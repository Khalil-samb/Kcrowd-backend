from django.urls import path

from .views import (
    AdminAllEventsView,
    EventDetailView,
    EventListView,
    EventTicketTypesView,
    OrganizerEventDetailView,
    OrganizerEventListCreateView,
    OrganizerTicketTypeDetailView,
    OrganizerTicketTypeListCreateView,
    UploadImageView,
)

urlpatterns = [
    # ── Catalogue public ──
    path('', EventListView.as_view(), name='event-list'),
    path('<uuid:pk>/', EventDetailView.as_view(), name='event-detail'),
    path('<uuid:event_id>/ticket-types/', EventTicketTypesView.as_view(), name='event-ticket-types'),

    # ── Gestion organisateur ──
    path('organizers/me/events/', OrganizerEventListCreateView.as_view(), name='organizer-event-list-create'),
    path('organizers/me/events/<uuid:pk>/', OrganizerEventDetailView.as_view(), name='organizer-event-detail'),
    path('organizers/me/events/<uuid:event_id>/ticket-types/', OrganizerTicketTypeListCreateView.as_view(), name='organizer-ticket-type-list-create'),
    path('organizers/me/events/<uuid:event_id>/ticket-types/<uuid:pk>/', OrganizerTicketTypeDetailView.as_view(), name='organizer-ticket-type-detail'),
    path('upload-image/', UploadImageView.as_view(), name='upload-image'),
    path('admin/all/', AdminAllEventsView.as_view(), name='admin-all-events'),

]