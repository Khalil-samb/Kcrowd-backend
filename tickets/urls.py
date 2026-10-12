
from django.urls import path

from .views import AcheterBilletView, AdminAllTicketsView, MesBilletsView, OrganizerEventTicketsView, ScannerBilletView, SignalerLitigeView, TicketDetailView

urlpatterns = [
    path('purchase/', AcheterBilletView.as_view(), name='ticket-purchase'),
    path('me/', MesBilletsView.as_view(), name='my-tickets'),
    path('scan/', ScannerBilletView.as_view(), name='ticket-scan'),
    path('<uuid:pk>/dispute/', SignalerLitigeView.as_view(), name='ticket-dispute'),
    path('organizers/me/events/<uuid:event_id>/tickets/', OrganizerEventTicketsView.as_view(), name='organizer-event-tickets'),
    path('<uuid:pk>/', TicketDetailView.as_view(), name='ticket-detail'),
    path('admin/all/', AdminAllTicketsView.as_view(), name='admin-all-tickets'),
]