from django.urls import path

from .views import AdminAllPayoutsView, DemanderPayoutView, PayoutListView, SoldeDisponibleView

urlpatterns = [
    path('solde/', SoldeDisponibleView.as_view(), name='payout-solde'),
    path('', PayoutListView.as_view(), name='payout-list'),
    path('demander/', DemanderPayoutView.as_view(), name='payout-demander'),
    path('admin/all/', AdminAllPayoutsView.as_view(), name='payout-admin-all'),
]