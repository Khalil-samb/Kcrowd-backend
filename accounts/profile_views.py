# ============================================================================
# accounts/profile_views.py
#
# Le profil de L'ORGANISATEUR CONNECTÉ :
#   GET   /api/auth/organizer/profile/          → lire son profil complet
#   PATCH /api/auth/organizer/profile/          → modifier tout ou partie
#   POST  /api/auth/organizer/change-password/  → changer son mot de passe
#
# RÈGLES DE SÉCURITÉ, à pouvoir expliquer à l'oral :
#
# 1. AUCUN identifiant dans l'URL : on modifie TOUJOURS request.user.organizer.
#    Impossible de modifier le profil de quelqu'un d'autre en changeant un id.
#
# 2. Seuls les champs listés dans le serializer sont pris en compte. Un client
#    qui enverrait "role": "admin", "status": "active" ou "phone": "..." est
#    simplement ignoré (protection contre la « mass assignment »).
#
# 3. Le compte de REVERSEMENT (là où l'argent est versé) et l'EMAIL (identifiant
#    de connexion) sont les deux cibles d'un voleur de session : modifier l'un
#    de ces deux champs exige le mot de passe ACTUEL. Un jeton volé ne suffit
#    donc pas pour détourner les reversements.
#
# 4. Les endpoints qui vérifient un mot de passe sont limités à 10 requêtes par
#    minute : impossible d'essayer des milliers de mots de passe à la suite.
# ============================================================================

import logging
import re

from django.db import transaction
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from engagement.services import creer_notification

from .models import Organizer, User
from .permissions import IsOrganizer

logger = logging.getLogger(__name__)


class TentativesSensiblesThrottle(UserRateThrottle):
    """10 requêtes par minute et par utilisateur sur les endpoints du profil."""
    scope = 'organizer_profile'
    rate = '10/min'


# ----------------------------------------------------------------------------
# Numéro de compte mobile money : format sénégalais (9 chiffres, commence par 7)
# ----------------------------------------------------------------------------
_NUMERO_VALIDE = re.compile(r'^7\d{8}$')


def normaliser_numero(brut):
    """'+221 77 123 45 67' → '771234567' (espaces, points, tirets et indicatif retirés)."""
    s = re.sub(r'[\s.\-()]', '', brut or '')
    for prefixe in ('+221', '00221', '221'):
        if s.startswith(prefixe) and len(s) > 9:
            return s[len(prefixe):]
    return s


# ----------------------------------------------------------------------------
# Robustesse du mot de passe : mêmes critères que le formulaire d'inscription
# (longueur, majuscule, minuscule, chiffre, caractère spécial)
# ----------------------------------------------------------------------------
def criteres_manquants(mot_de_passe):
    criteres = {
        "au moins 8 caractères": len(mot_de_passe) >= 8,
        "une majuscule": re.search(r'[A-Z]', mot_de_passe) is not None,
        "une minuscule": re.search(r'[a-z]', mot_de_passe) is not None,
        "un chiffre": re.search(r'\d', mot_de_passe) is not None,
        "un caractère spécial": re.search(r'[^A-Za-z0-9]', mot_de_passe) is not None,
    }
    return [nom for nom, ok in criteres.items() if not ok]


def mot_de_passe_assez_robuste(mot_de_passe):
    """La longueur de 8 est obligatoire ; en plus, au moins 4 critères sur 5 au total."""
    manquants = criteres_manquants(mot_de_passe)
    return len(mot_de_passe) >= 8 and len(manquants) <= 1, manquants


# ----------------------------------------------------------------------------
# Lecture : le profil, à plat (organisation + responsable)
# ----------------------------------------------------------------------------
def serialiser_profil(organizer):
    user = organizer.user
    return {
        'id': str(organizer.id),
        'organization_name': organizer.organization_name,
        'registration_number': organizer.registration_number or '',
        'category_id': organizer.category_id or '',
        'description': organizer.description or '',
        'logo_url': organizer.logo_url or '',
        'payment_method': organizer.payment_method,
        'mobile_money_account_number': organizer.mobile_money_account_number,
        'mobile_money_account_holder': organizer.mobile_money_account_holder,
        'receives_sale_alerts': organizer.receoit_alertes_vente,
        'status': organizer.status,
        'created_at': organizer.created_at,
        # le responsable du compte
        'first_name': user.first_name,
        'last_name': user.last_name or '',
        'email': user.email or '',
        'phone': user.phone,            # lecture seule : sert à s'identifier (OTP)
        'city_id': user.city_id or '',
    }


# ----------------------------------------------------------------------------
# Écriture : tous les champs sont facultatifs (modification partielle)
# ----------------------------------------------------------------------------
class ProfilOrganisateurUpdateSerializer(serializers.Serializer):
    # Organisation
    organization_name = serializers.CharField(max_length=200)
    registration_number = serializers.CharField(max_length=100, allow_blank=True, allow_null=True)
    category_id = serializers.CharField(max_length=50, allow_blank=True, allow_null=True)
    description = serializers.CharField(max_length=1000, allow_blank=True, allow_null=True)
    logo_url = serializers.URLField(max_length=200, allow_blank=True, allow_null=True)
    # Responsable
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, allow_blank=True, allow_null=True)
    city_id = serializers.CharField(max_length=50, allow_blank=True, allow_null=True)
    email = serializers.EmailField(max_length=254)
    # Compte de reversement (sensible)
    payment_method = serializers.ChoiceField(choices=['wave', 'orange_money'])
    mobile_money_account_number = serializers.CharField(max_length=30)
    mobile_money_account_holder = serializers.CharField(max_length=100)
    # Préférences
    receives_sale_alerts = serializers.BooleanField()
    # Confirmation (jamais enregistrée, jamais renvoyée)
    current_password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, trim_whitespace=False, max_length=128,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Chaque champ est facultatif : on ne modifie que ce qui est envoyé
        for nom, champ in self.fields.items():
            champ.required = False
        self.changements_sensibles = []

    @property
    def organizer(self):
        return self.context['organizer']

    def validate_mobile_money_account_number(self, valeur):
        actuel = (self.organizer.mobile_money_account_number or '').strip()
        # Numéro inchangé : on ne le re-valide pas (un ancien format enregistré
        # à l'inscription ne doit pas empêcher de modifier autre chose).
        if valeur.strip() == actuel:
            return actuel
        normalise = normaliser_numero(valeur)
        if not _NUMERO_VALIDE.match(normalise):
            raise serializers.ValidationError(
                "Numéro invalide : 9 chiffres commençant par 7 (ex. 77 123 45 67)."
            )
        return normalise

    def validate_email(self, valeur):
        valeur = valeur.strip()
        user = self.organizer.user
        if (user.email or '').lower() == valeur.lower():
            return user.email
        if User.objects.filter(email__iexact=valeur).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("Cette adresse email est déjà utilisée.")
        return valeur

    def validate(self, attrs):
        organizer = self.organizer
        user = organizer.user
        sensibles = []

        if 'email' in attrs and attrs['email'] != user.email:
            sensibles.append("l'adresse email")

        champs_reversement = {
            'payment_method': organizer.payment_method,
            'mobile_money_account_number': organizer.mobile_money_account_number,
            'mobile_money_account_holder': organizer.mobile_money_account_holder,
        }
        nettoye = lambda v: (v or '').strip()  # un espace en trop n'est pas une modification
        if any(nom in attrs and nettoye(attrs[nom]) != nettoye(actuel) for nom, actuel in champs_reversement.items()):
            sensibles.append("le compte de reversement")

        mot_de_passe = attrs.pop('current_password', '')
        if sensibles:
            if not user.has_usable_password():
                raise serializers.ValidationError({
                    'current_password': "Ce compte n'a pas de mot de passe : définissez-en un avant de modifier ces informations."
                })
            if not mot_de_passe:
                raise serializers.ValidationError({
                    'current_password': f"Votre mot de passe actuel est requis pour modifier {' et '.join(sensibles)}."
                })
            if not user.check_password(mot_de_passe):
                raise serializers.ValidationError({'current_password': "Mot de passe incorrect."})

        self.changements_sensibles = sensibles
        return attrs


class OrganizerProfileView(APIView):
    permission_classes = [IsOrganizer]
    throttle_classes = [TentativesSensiblesThrottle]

    # Champs de la fiche Organizer et de la fiche User, et leur nom en base
    CHAMPS_ORGANIZER = {
        'organization_name': 'organization_name',
        'registration_number': 'registration_number',
        'category_id': 'category_id',
        'description': 'description',
        'logo_url': 'logo_url',
        'payment_method': 'payment_method',
        'mobile_money_account_number': 'mobile_money_account_number',
        'mobile_money_account_holder': 'mobile_money_account_holder',
        'receives_sale_alerts': 'receoit_alertes_vente',
    }
    CHAMPS_USER = ('first_name', 'last_name', 'city_id', 'email')
    # Ces champs facultatifs vidés par l'utilisateur sont enregistrés comme « rien » (NULL)
    CHAMPS_FACULTATIFS = {'registration_number', 'category_id', 'description', 'logo_url', 'last_name', 'city_id'}

    def _organizer(self, request):
        try:
            return Organizer.objects.select_related('user').get(user=request.user)
        except Organizer.DoesNotExist:
            return None

    def get(self, request):
        organizer = self._organizer(request)
        if organizer is None:
            return Response({'erreur': 'Profil organisateur introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serialiser_profil(organizer))

    def patch(self, request):
        organizer = self._organizer(request)
        if organizer is None:
            return Response({'erreur': 'Profil organisateur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProfilOrganisateurUpdateSerializer(data=request.data, context={'organizer': organizer})
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data

        with transaction.atomic():
            # Verrou : deux enregistrements simultanés (deux onglets) passent l'un après l'autre
            organizer = Organizer.objects.select_for_update().select_related('user').get(pk=organizer.pk)
            user = organizer.user

            modifies_organizer, modifies_user = [], []
            for nom_api, nom_base in self.CHAMPS_ORGANIZER.items():
                if nom_api in donnees:
                    valeur = donnees[nom_api]
                    if nom_api in self.CHAMPS_FACULTATIFS and valeur == '':
                        valeur = None
                    setattr(organizer, nom_base, valeur)
                    modifies_organizer.append(nom_base)
            for nom in self.CHAMPS_USER:
                if nom in donnees:
                    valeur = donnees[nom]
                    if nom in self.CHAMPS_FACULTATIFS and valeur == '':
                        valeur = None
                    setattr(user, nom, valeur)
                    modifies_user.append(nom)

            # update_fields : on n'écrit QUE ce qui a été envoyé (jamais le rôle, le statut...)
            if modifies_organizer:
                organizer.save(update_fields=modifies_organizer)
            if modifies_user:
                user.save(update_fields=modifies_user)

        # Une alerte à la personne elle-même : si ce n'était pas elle, elle le voit
        if serializer.changements_sensibles:
            try:
                creer_notification(
                    user=user,
                    type_notif='account',
                    titre='Informations sensibles modifiées',
                    message=f"Vous avez modifié {' et '.join(serializer.changements_sensibles)}. "
                            f"Si ce n'est pas vous, changez votre mot de passe immédiatement.",
                )
            except Exception:  # une notification ratée ne doit jamais annuler la modification
                logger.exception("Notification de modification du profil non envoyée")

        return Response(serialiser_profil(organizer))


# ----------------------------------------------------------------------------
# Changement de mot de passe
# ----------------------------------------------------------------------------
class ChangerMotDePasseSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    def validate_new_password(self, valeur):
        assez_robuste, manquants = mot_de_passe_assez_robuste(valeur)
        if not assez_robuste:
            raise serializers.ValidationError(
                "Mot de passe trop faible : il manque " + ", ".join(manquants) + "."
            )
        return valeur


class OrganizerChangePasswordView(APIView):
    permission_classes = [IsOrganizer]
    throttle_classes = [TentativesSensiblesThrottle]

    def post(self, request):
        serializer = ChangerMotDePasseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data
        user = request.user

        if not user.check_password(donnees['current_password']):
            return Response({'current_password': 'Mot de passe actuel incorrect.'}, status=status.HTTP_400_BAD_REQUEST)

        if donnees['current_password'] == donnees['new_password']:
            return Response(
                {'new_password': "Le nouveau mot de passe doit être différent de l'ancien."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(donnees['new_password'])  # haché : jamais stocké en clair
        user.save(update_fields=['password'])

        try:
            creer_notification(
                user=user,
                type_notif='account',
                titre='Mot de passe modifié',
                message="Votre mot de passe vient d'être modifié. Si ce n'est pas vous, contactez le support immédiatement.",
            )
        except Exception:
            logger.exception("Notification de changement de mot de passe non envoyée")

        return Response({'message': 'Mot de passe modifié.'})