from django.shortcuts import get_object_or_404
from rest_framework import generics

from accounts.permissions import IsOrganizer
from events.models import Event
from .models import AccessGate, ScannerAgent
from .serializers import AccessGateSerializer, ScannerAgentSerializer


class GateListCreateView(generics.ListCreateAPIView):
    """
    GET/POST /api/access-control/events/<event_id>/gates/
    Réservé à l'organisateur propriétaire de l'événement concerné.
    """
    serializer_class = AccessGateSerializer
    permission_classes = [IsOrganizer]

    def get_queryset(self):
        # Double filtre : par l'événement demandé ET par le fait que cet
        # événement appartient bien à l'organisateur connecté. Si les
        # deux ne correspondent pas, la liste est simplement vide — pas
        # d'erreur explicite qui confirmerait à un curieux que
        # l'événement existe.
        return AccessGate.objects.filter(
            event_id=self.kwargs['event_id'],
            event__organizer=self.request.user.organizer,
        )

    def perform_create(self, serializer):
        # get_object_or_404 : récupère l'événement, ou renvoie proprement
        # une erreur 404 s'il n'existe pas OU s'il n'appartient pas à cet
        # organisateur (le filtre organizer=... est inclus dans la recherche).
        event = get_object_or_404(Event, id=self.kwargs['event_id'], organizer=self.request.user.organizer)
        serializer.save(event=event)


class GateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /api/access-control/events/<event_id>/gates/<id>/

    Même double filtre que pour la liste : la porte doit appartenir à CET
    événement ET cet événement doit appartenir à l'organisateur connecté.
    Sinon la porte est introuvable (404) — jamais une erreur qui confirmerait
    à un curieux qu'elle existe chez quelqu'un d'autre.

    Attention : supprimer une porte supprime aussi ses agents (CASCADE dans
    le modèle ScannerAgent) — le frontend les retire d'abord s'il veut les
    garder ailleurs.
    """
    serializer_class = AccessGateSerializer
    permission_classes = [IsOrganizer]

    def get_queryset(self):
        return AccessGate.objects.filter(
            event_id=self.kwargs['event_id'],
            event__organizer=self.request.user.organizer,
        )


class AgentListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/access-control/events/<event_id>/agents/"""
    serializer_class = ScannerAgentSerializer
    permission_classes = [IsOrganizer]

    def get_queryset(self):
        return ScannerAgent.objects.filter(
            event_id=self.kwargs['event_id'],
            event__organizer=self.request.user.organizer,
        )

    def perform_create(self, serializer):
        event = get_object_or_404(Event, id=self.kwargs['event_id'], organizer=self.request.user.organizer)
        serializer.save(event=event)


class AgentDetailView(generics.DestroyAPIView):
    """
    DELETE /api/access-control/events/<event_id>/agents/<id>/

    Seule la suppression est exposée : retirer un agent est le seul besoin
    actuel. Même double filtre de sécurité que les autres vues.
    """
    serializer_class = ScannerAgentSerializer
    permission_classes = [IsOrganizer]

    def get_queryset(self):
        return ScannerAgent.objects.filter(
            event_id=self.kwargs['event_id'],
            event__organizer=self.request.user.organizer,
        )