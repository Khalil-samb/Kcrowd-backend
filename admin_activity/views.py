from django.db.models import Sum
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Organizer, User
from accounts.permissions import IsAdmin
from events.models import Event
from platform_settings.services import somme_commission_ventes
from transactions.models import Transaction
from .models import AdminActivityLog
from .serializers import AdminActivityLogSerializer


class ActivityLogListView(generics.ListAPIView):
    """GET /api/admin-activity/log/ — le journal complet, réservé à l'admin."""
    serializer_class = AdminActivityLogSerializer
    permission_classes = [IsAdmin]
    queryset = AdminActivityLog.objects.all()


class AdminDashboardView(APIView):
    """GET /api/admin-activity/dashboard/ — les indicateurs de supervision globale."""
    permission_classes = [IsAdmin]

    def get(self, request):
        nb_utilisateurs = User.objects.filter(role='user').count()
        nb_organisateurs = Organizer.objects.count()
        nb_evenements_en_cours = Event.objects.filter(status='published').count()

        # Commission sur les ventes de billets : chaque vente au taux figé le jour de
        # l'achat (plus de « 5% » en dur) ; 100% sur les publicités sponsorisées.
        commission_ventes = somme_commission_ventes(Transaction.objects.all())
        pubs = (
            Transaction.objects.filter(type='sponsored_ad', status='success')
            .aggregate(total=Sum('amount'))['total']
            or 0
        )
        commission_totale = round(commission_ventes + pubs)

        return Response({
            'nombre_utilisateurs': nb_utilisateurs,
            'nombre_organisateurs': nb_organisateurs,
            'evenements_en_cours': nb_evenements_en_cours,
            'commission_totale': commission_totale,
        })