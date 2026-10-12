# Les 4 points d'entrée de l'authentification :
# - OTP (demande + vérification) pour le grand public
# - Connexion classique email/mot de passe pour organisateur et admin
#
# Chaque vue hérite de APIView (la classe de base DRF pour une vue qui ne
# suit pas forcément le schéma CRUD classique d'un ViewSet).


from datetime import timedelta
import random

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework import generics
from .models import Organizer
from .permissions import IsAdmin, IsOrganizer
from admin_activity.services import journaliser
from django.db import transaction

from config.providers_config import otp_sender
from .models import Organizer, OtpCode, User
from .serializers import (
    AdminLoginSerializer,
    OrganizerLoginSerializer,
    OrganizerRegisterSerializer,
    OtpRequestSerializer,
    OtpVerifySerializer,
    UserSerializer,
)
from .serializers import OrganizerSerializer


def generer_tokens_pour(user: User) -> dict:
    """
    Fonction utilitaire partagée par les 3 vues de connexion ci-dessous :
    crée un couple de jetons JWT (access + refresh) pour un utilisateur.

    - access : jeton de courte durée, envoyé à chaque requête pour prouver
      l'identité (dans l'en-tête Authorization: Bearer <access>).
    - refresh : jeton de longue durée, utilisé uniquement pour obtenir un
      nouveau access sans redemander le mot de passe.
    """
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }
    

class OtpRequestView(APIView):
    """
    POST /api/auth/otp/request/
    Corps attendu : { "phone": "+221771234567" }

    Génère un code à 4 chiffres, le sauvegarde avec 5 minutes de validité,
    et le transmet via otp_sender (actuellement : affiché dans la console).
    """

    def post(self, request):
        serializer = OtpRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        telephone = serializer.validated_data['phone']

        # :04d = toujours 4 chiffres, avec des zéros devant si besoin
        # (ex. 42 devient "0042", jamais un code à 2 chiffres par erreur).
        code = f"{random.randint(0, 9999):04d}"

        OtpCode.objects.create(
            phone=telephone,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        #  Ligne clé : on ne connaît jamais ConsoleOtpSender directement
        # ici, seulement le contrat otp_sender. C'est le patron Strategy
        # appliqué concrètement.
        otp_sender.envoyer(telephone, code)

        return Response({'message': 'Code envoyé.'}, status=status.HTTP_200_OK)
    
    

class OtpVerifyView(APIView):
    """
    POST /api/auth/otp/verify/
    Corps attendu : { "phone": "...", "code": "...", "first_name": "..." }

    Vérifie le code, crée le compte s'il n'existe pas encore (première
    connexion), et renvoie un jeton JWT pour que le frontend reste connecté.
    """

    def post(self, request):
        serializer = OtpVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data

        # On cherche le code le plus RÉCENT pour ce numéro (si plusieurs
        # codes ont été demandés d'affilée) et on vérifie qu'il n'a pas expiré.
        otp = (
            OtpCode.objects.filter(
                phone=donnees['phone'],
                code=donnees['code'],
                expires_at__gte=timezone.now(),
            )
            .order_by('-created_at')
            .first()
        )

        if not otp:
            return Response({'erreur': 'Code invalide ou expiré.'}, status=status.HTTP_400_BAD_REQUEST)

        # get_or_create : récupère l'utilisateur s'il existe déjà (il se
        # reconnecte), ou le crée avec les infos fournies (première fois).
        user, _cree = User.objects.get_or_create(
            phone=donnees['phone'],
            defaults={
                'first_name': donnees.get('first_name', ''),
                'last_name': donnees.get('last_name', ''),
            },
        )
        user.phone_verified = True
        user.save()

        return Response(
            {**generer_tokens_pour(user), 'user': UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )


class OrganizerRegisterView(APIView):
    """
    POST /api/auth/organizer/register/
    Réservé aux utilisateurs déjà identifiés (JWT valide obtenu via l'OTP) —
    d'où permission_classes = [IsAuthenticated] : contrairement aux vues
    précédentes, celle-ci exige un jeton dans l'en-tête de la requête.
 
    Transforme le compte User actuel en organisateur : ajoute l'email et
    le mot de passe, bascule le rôle, et crée la fiche Organizer associée.
    """
    permission_classes = [IsAuthenticated]
 
    def post(self, request):
        serializer = OrganizerRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data
 
        user = request.user
 
        if user.role != 'user':
            return Response(
                {'erreur': 'Ce compte a déjà un rôle différent.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
 
        if User.objects.filter(email=donnees['email']).exclude(id=user.id).exists():
            return Response({'erreur': 'Cet email est déjà utilisé.'}, status=status.HTTP_400_BAD_REQUEST)
 
        
        # POURQUOI transaction.atomic() ICI, précisément ?
        
        # Ce bloc modifie 3 choses en base : le User, l'Organizer, ET le
        # journal d'activité. Sans ce bloc, si la dernière étape
        # (journaliser) échoue pour n'importe quelle raison, les 2
        # premières restent quand même enregistrées — exactement ce qui
        # vous est arrivé (compte transformé en organisateur, mais la
        # requête globale a quand même renvoyé une erreur 500). Avec
        # atomic(), soit LES 3 réussissent ensemble, soit AUCUNE des 3
        # n'est gardée.
        with transaction.atomic():
            user.email = donnees['email']
            user.set_password(donnees['password'])
            user.role = 'organizer'
            user.save()
 
            organizer = Organizer.objects.create(
                user=user,
                organization_name=donnees['organization_name'],
                registration_number=donnees.get('registration_number', ''),
                category_id=donnees.get('category_id', ''),
                payment_method=donnees['payment_method'],
                mobile_money_account_number=donnees['mobile_money_account_number'],
                mobile_money_account_holder=donnees['mobile_money_account_holder'],
                receoit_alertes_vente=donnees.get('receoit_alertes_vente', True),
            )
 
            journaliser(
                type_activite='new_organizer',
                message=f"{organizer.organization_name} a rejoint la plateforme",
                organizer=organizer,
            )
 
        return Response(
            {
                **generer_tokens_pour(user),
                'user': UserSerializer(user).data,
                'organizer_id': str(organizer.id),
            },
            status=status.HTTP_201_CREATED,
        )

        
class OrganizerLoginView(APIView):
    """
    POST /api/auth/organizer/login/
    Connexion classique email + mot de passe, réservée aux comptes
    role='organizer'.
    """

    def post(self, request):
        serializer = OrganizerLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data

        try:
            user = User.objects.get(email=donnees['email'], role='organizer')
        except User.DoesNotExist:
            #  Message volontairement identique que l'email existe ou non :
            # ne jamais révéler si un email est enregistré, ça faciliterait
            # une attaque par énumération des comptes existants.
            return Response({'erreur': 'Email ou mot de passe incorrect.'}, status=status.HTTP_401_UNAUTHORIZED)

        # check_password() compare le mot de passe fourni au hachage stocké,
        # sans jamais avoir besoin de "déchiffrer" quoi que ce soit (le
        # hachage n'est pas réversible, c'est précisément le but).
        if not user.check_password(donnees['password']):
            return Response({'erreur': 'Email ou mot de passe incorrect.'}, status=status.HTTP_401_UNAUTHORIZED)

        if user.status == 'suspended':
            return Response({'erreur': 'Ce compte a été suspendu.'}, status=status.HTTP_403_FORBIDDEN)

        return Response(
            {**generer_tokens_pour(user), 'user': UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )
        
        
class AdminLoginView(APIView):
    """POST /api/auth/admin/login/ — même principe, réservé à role='admin'."""

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data

        try:
            user = User.objects.get(email=donnees['email'], role='admin')
        except User.DoesNotExist:
            return Response({'erreur': 'Email ou mot de passe incorrect.'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(donnees['password']):
            return Response({'erreur': 'Email ou mot de passe incorrect.'}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(
            {**generer_tokens_pour(user), 'user': UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )
        
        
class AdminUserListView(generics.ListAPIView):
    """GET /api/auth/admin/users/ — tous les comptes grand public."""
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    queryset = User.objects.filter(role='user')
    
    
class AdminUserStatusView(APIView):
    """PATCH /api/auth/admin/users/<id>/status/ — suspend ou réactive."""
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        utilisateur = User.objects.filter(id=pk, role='user').first()
        if not utilisateur:
            return Response({'erreur': 'Utilisateur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        nouveau_statut = 'suspended' if utilisateur.status == 'active' else 'active'
        utilisateur.status = nouveau_statut
        utilisateur.save()

        journaliser(
            type_activite='account_suspended' if nouveau_statut == 'suspended' else 'account_reactivated',
            message=f"Le compte utilisateur de {utilisateur.first_name} a été {'suspendu' if nouveau_statut == 'suspended' else 'réactivé'}.",
            user=utilisateur,
        )

        return Response(UserSerializer(utilisateur).data)

class AdminOrganizerListView(generics.ListAPIView):
    """GET /api/auth/admin/organizers/"""
    serializer_class = OrganizerSerializer
    permission_classes = [IsAdmin]
    # select_related : évite une requête SQL supplémentaire par organisateur
    # (le serializer lit user.phone et user.email).
    queryset = Organizer.objects.select_related('user').all()

    

class AdminOrganizerStatusView(APIView):
    """PATCH /api/auth/admin/organizers/<id>/status/"""
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        organizer = Organizer.objects.filter(id=pk).first()
        if not organizer:
            return Response({'erreur': 'Organisateur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        nouveau_statut = 'suspended' if organizer.status == 'active' else 'active'
        organizer.status = nouveau_statut
        organizer.save()

        journaliser(
            type_activite='account_suspended' if nouveau_statut == 'suspended' else 'account_reactivated',
            message=f"Le compte organisateur {organizer.organization_name} a été {'suspendu' if nouveau_statut == 'suspended' else 'réactivé'}.",
            organizer=organizer,
        )

        return Response({'id': str(organizer.id), 'status': organizer.status})
    
    
class OrganizerMeView(APIView):
    """GET /api/auth/organizer/me/ — le profil de L'ORGANISATEUR CONNECTÉ, lui-même."""
    permission_classes = [IsOrganizer]
 
    def get(self, request):
        return Response(OrganizerSerializer(request.user.organizer).data)


# mise à jour simple du
#    profil — uniquement prénom/nom pour l'instant, jamais le téléphone,
#    qui reste l'identifiant de connexion) :


class UpdateMeView(APIView):
    """PATCH /api/auth/me/"""
    permission_classes = [IsAuthenticated]
 
    def patch(self, request):
        utilisateur = request.user
        utilisateur.first_name = request.data.get('first_name', utilisateur.first_name)
        utilisateur.last_name = request.data.get('last_name', utilisateur.last_name)
        utilisateur.save()
        return Response(UserSerializer(utilisateur).data)


class WhoAmIView(APIView):
    """
    GET /api/auth/whoami/
    Fonctionne pour N'IMPORTE QUEL rôle connecté (utilisateur, organisateur,
    administrateur) — contrairement aux autres vues "me" qui sont propres à
    un seul rôle. Sert à identifier qui parle, pour le chatbot notamment.
    """
    permission_classes = [IsAuthenticated]
 
    def get(self, request):
        u = request.user
        return Response({
            'id': str(u.id),
            'role': u.role,
            'firstName': u.first_name,
            'lastName': u.last_name,
        })
