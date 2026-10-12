# ============================================================================
# transactions/views.py — FICHIER COMPLET
# ============================================================================

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdmin, IsOrganizer
from .models import Transaction
from .serializers import TransactionSerializer


class OrganizerAllTransactionsView(generics.ListAPIView):
    """GET /api/transactions/organizers/me/ — toutes MES transactions, tousévénements confondus."""
    serializer_class = TransactionSerializer
    permission_classes = [IsOrganizer]

    def get_queryset(self):
        return Transaction.objects.select_related('commission_snapshot').filter(event__organizer=self.request.user.organizer)


class OrganizerEventTransactionsView(generics.ListAPIView):
    """GET /api/transactions/organizers/me/events/<event_id>/ — transactions d'UN événement précis."""
    serializer_class = TransactionSerializer
    permission_classes = [IsOrganizer]

    def get_queryset(self):
        return Transaction.objects.select_related('commission_snapshot').filter(
            event_id=self.kwargs['event_id'],
            event__organizer=self.request.user.organizer,
        )


class AdminAllTransactionsView(generics.ListAPIView):
    """GET /api/transactions/admin/all/ — TOUTES les transactions de la plateforme."""
    serializer_class = TransactionSerializer
    permission_classes = [IsAdmin]
    queryset = Transaction.objects.select_related('commission_snapshot').all()


class TransactionDetailView(generics.RetrieveAPIView):
    """
    GET /api/transactions/<id>/
    Pour l'acheteur : consulter SA PROPRE transaction (page de confirmation
    d'achat). Filtré par user=request.user — jamais accessible pour la
    transaction de quelqu'un d'autre.
    """
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.select_related('commission_snapshot').filter(user=self.request.user)