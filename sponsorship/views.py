import uuid

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsOrganizer
from config.providers_config import payment_provider
from events.lifecycle import terminer_les_evenements_passes
from events.models import Event
from transactions.models import Transaction
from .models import SponsoredAd
from .serializers import AcheterCampagneSerializer, SponsoredAdSerializer

# Une seule offre, décidée côté serveur — jamais négociable depuis le client.
# Valable JUSQU'À LA FIN DE L'ÉVÉNEMENT : l'événement passe en tête du catalogue (badge « Sponsorisé ») et
# ses vidéos passent en premier dans le fil « Vidéos ».
FORMULES = {
    'boost': {'nom': 'Boost : en tête du catalogue et du fil vidéos', 'prix': 15000},
}


class CampagneActiveView(generics.RetrieveAPIView):
    """
    GET /api/sponsorship/events/<event_id>/active/
    Renvoie la campagne en cours de l'événement, ou 404 s'il n'y en a pas (cas normal, pas une erreur).
    """
    serializer_class = SponsoredAdSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        terminer_les_evenements_passes()
        pub = SponsoredAd.objects.filter(
            event_id=self.kwargs['event_id'], status='active', end_date__gt=timezone.now()
        ).first()
        if not pub:
            raise Http404
        return pub


class AcheterCampagneView(APIView):
    """
    POST /api/sponsorship/events/<event_id>/purchase/
    Corps : {} (ou { "formule": "boost" }). Réservé à l'organisateur propriétaire de l'événement.
    """
    permission_classes = [IsOrganizer]

    def post(self, request, event_id):
        serializer = AcheterCampagneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        formule = FORMULES[serializer.validated_data['formule']]

        terminer_les_evenements_passes()
        event = get_object_or_404(Event, id=event_id, organizer=request.user.organizer)
        organizer = request.user.organizer
        maintenant = timezone.now()

        # Refusé AVANT tout paiement : on ne fait jamais payer pour rien.
        if event.status not in ('published', 'sold_out') or event.end_date <= maintenant:
            return Response({'erreur': "Seul un événement publié et pas encore terminé peut être sponsorisé."},
                            status=status.HTTP_400_BAD_REQUEST)
        if SponsoredAd.objects.filter(event=event, status='active', end_date__gt=maintenant).exists():
            return Response({'erreur': "Cet événement est déjà sponsorisé."}, status=status.HTTP_400_BAD_REQUEST)

        reference = f"AD-{uuid.uuid4().hex[:10].upper()}"
        resultat = payment_provider.initier_paiement(formule['prix'], organizer.payment_method, reference)

        transaction = Transaction.objects.create(
            user=request.user,
            event=event,
            type='sponsored_ad',
            amount=formule['prix'],
            payment_method=organizer.payment_method,
            status='success' if resultat.success else 'failed',
            reference=reference,
        )

        if not resultat.success:
            return Response({'erreur': 'Le paiement a échoué.'}, status=status.HTTP_402_PAYMENT_REQUIRED)

        pub = SponsoredAd.objects.create(
            organizer=organizer,
            event=event,
            transaction=transaction,
            package_name=formule['nom'],
            price=formule['prix'],
            status='active',
            start_date=maintenant,
            end_date=event.end_date,      # jusqu'à la fin de l'événement
        )

        event.is_sponsored = True
        event.save(update_fields=['is_sponsored'])

        return Response(SponsoredAdSerializer(pub).data, status=status.HTTP_201_CREATED)
