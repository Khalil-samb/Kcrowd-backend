import uuid

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsOrganizer, IsAdmin
from config.providers_config import payment_provider
from .models import Payout
from .serializers import PayoutSerializer
from .services import calculer_solde_disponible


class SoldeDisponibleView(APIView):
    """GET /api/payouts/solde/ — le solde actuellement disponible pour l'organisateur connecté."""
    permission_classes = [IsOrganizer]

    def get(self, request):
        solde = calculer_solde_disponible(request.user.organizer)
        return Response({'solde_disponible': solde})


class PayoutListView(generics.ListAPIView):
    """GET /api/payouts/ — historique des demandes de virement."""
    serializer_class = PayoutSerializer
    permission_classes = [IsOrganizer]

    def get_queryset(self):
        return Payout.objects.filter(organizer=self.request.user.organizer)


class DemanderPayoutView(APIView):
    """
    POST /api/payouts/demander/
    Demande le virement de la TOTALITÉ du solde disponible — pas un
    montant choisi par le client, toujours recalculé côté serveur.
    """
    permission_classes = [IsOrganizer]

    def post(self, request):
        organizer = request.user.organizer
        solde = calculer_solde_disponible(organizer)

        if solde <= 0:
            return Response({'erreur': 'Aucun solde disponible à reverser.'}, status=status.HTTP_400_BAD_REQUEST)

        reference = f"{organizer.payment_method.upper()}-PAYOUT-{uuid.uuid4().hex[:8].upper()}"

        # Même patron Strategy, cette fois pour de l'argent qui SORT de
        # Kcrowd plutôt que d'y entrer — la même interface sert dans
        # les deux sens.
        resultat = payment_provider.initier_paiement(solde, organizer.payment_method, reference)

        payout = Payout.objects.create(
            organizer=organizer,
            amount=solde,
            status='completed' if resultat.success else 'failed',
            payment_method=organizer.payment_method,
            destination_account=organizer.mobile_money_account_number,
            reference=reference,
            processed_at=timezone.now() if resultat.success else None,
        )

        if not resultat.success:
            return Response({'erreur': 'Le virement a échoué.', 'payout': PayoutSerializer(payout).data}, status=status.HTTP_402_PAYMENT_REQUIRED)

        return Response(PayoutSerializer(payout).data, status=status.HTTP_201_CREATED)
    
    


class AdminAllPayoutsView(generics.ListAPIView):
    """GET /api/payouts/admin/all/ — tous les reversements de la plateforme."""
    serializer_class = PayoutSerializer
    permission_classes = [IsAdmin]
    queryset = Payout.objects.all()
