from django.urls import path

from .views import AgentDetailView, AgentListCreateView, GateDetailView, GateListCreateView

urlpatterns = [
    path('events/<uuid:event_id>/gates/', GateListCreateView.as_view(), name='gate-list-create'),
    path('events/<uuid:event_id>/gates/<uuid:pk>/', GateDetailView.as_view(), name='gate-detail'),
    path('events/<uuid:event_id>/agents/', AgentListCreateView.as_view(), name='agent-list-create'),
    path('events/<uuid:event_id>/agents/<uuid:pk>/', AgentDetailView.as_view(), name='agent-detail'),
]