# ============================================================================
# platform_settings/views.py
#
#   GET   /api/settings/          → les réglages + l'historique   (admin)
#   PATCH /api/settings/          → modifier le taux de commission (admin)
#   GET   /api/settings/public/   → le taux en vigueur             (tout le monde)
#
# SÉCURITÉ, à pouvoir expliquer à l'oral :
#
# 1. Modifier le taux exige le MOT DE PASSE ACTUEL de l'admin : un jeton de
#    session volé ne suffit pas à changer ce que gagne la plateforme (ni à faire
#    perdre de l'argent aux organisateurs).
# 2. Chaque changement est inscrit dans l'historique (qui, quand, ancien et nouveau
#    taux). Ce journal n'est modifiable par aucune route.
# 3. Garde-fou : le taux est compris entre 0 et 30 %.
# 4. Le nouveau taux ne s'applique QU'AUX VENTES FUTURES : les anciennes gardent
#    le taux figé le jour de l'achat (voir models.py).
# 5. 10 essais par minute : impossible de deviner un mot de passe par force brute.
# ============================================================================

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from accounts.permissions import IsAdmin

from .models import CommissionRateChange, PlatformSettings
from .serializers import ModifierReglagesSerializer, serialiser_reglages


class LimiteAdmin(UserRateThrottle):
    scope = 'platform_settings'
    rate = '10/min'


class LimitePublique(AnonRateThrottle):
    scope = 'platform_settings_public'
    rate = '120/min'


class ReglagesView(APIView):
    permission_classes = [IsAdmin]
    throttle_classes = [LimiteAdmin]

    def get(self, request):
        return Response(serialiser_reglages(PlatformSettings.load()))

    def patch(self, request):
        serializer = ModifierReglagesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nouveau_taux = serializer.validated_data['commission_rate']
        mot_de_passe = serializer.validated_data.get('current_password', '')

        PlatformSettings.load()  # garantit que la ligne existe avant de la verrouiller

        with transaction.atomic():
            # Verrou : deux admins qui enregistrent en même temps passent l'un après l'autre
            reglages = PlatformSettings.objects.select_for_update().get(pk=1)

            if nouveau_taux == reglages.commission_rate:
                return Response(serialiser_reglages(reglages))  # rien à changer, rien à confirmer

            if not mot_de_passe:
                return Response(
                    {'current_password': ["Votre mot de passe actuel est requis pour modifier le taux de commission."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not request.user.check_password(mot_de_passe):
                return Response({'current_password': ['Mot de passe incorrect.']}, status=status.HTTP_400_BAD_REQUEST)

            CommissionRateChange.objects.create(
                old_rate=reglages.commission_rate, new_rate=nouveau_taux, changed_by=request.user,
            )
            reglages.commission_rate = nouveau_taux
            reglages.updated_by = request.user
            reglages.save()

        return Response(serialiser_reglages(reglages))


class ReglagesPublicsView(APIView):
    """
    Le taux est une information publique : la page d'inscription des organisateurs
    l'annonce déjà (« commission de 5 % »). On n'expose RIEN d'autre ici.
    """
    authentication_classes = []  # un jeton expiré dans le navigateur ne doit pas provoquer de 401 ici
    permission_classes = [AllowAny]
    throttle_classes = [LimitePublique]

    def get(self, request):
        return Response({'commission_rate': float(PlatformSettings.load().commission_rate)})