 
from django.urls import path
 
from .views import (
    AdminAllTransactionsView,
    OrganizerAllTransactionsView,
    OrganizerEventTransactionsView,
    TransactionDetailView,
)
 
urlpatterns = [
    path('organizers/me/', OrganizerAllTransactionsView.as_view(), name='organizer-all-transactions'),
    path('organizers/me/events/<uuid:event_id>/', OrganizerEventTransactionsView.as_view(), name='organizer-event-transactions'),
    path('admin/all/', AdminAllTransactionsView.as_view(), name='admin-all-transactions'),
    path('<uuid:pk>/', TransactionDetailView.as_view(), name='transaction-detail'),
]
 
