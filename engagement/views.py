from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Favorite, Notification
from .serializers import FavoriteSerializer, NotificationSerializer


class FavoriteListView(generics.ListAPIView):
    """GET /api/engagement/favorites/ — mes favoris."""
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)


class FavoriteToggleView(APIView):
    """
    POST   /api/engagement/favorites/<event_id>/  → ajoute aux favoris
    DELETE /api/engagement/favorites/<event_id>/  → retire des favoris
    Une seule vue pour les deux actions : logique, ce sont les deux faces
    d'un même bouton "cœur" côté frontend.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        # get_or_create : si le favori existe déjà, ne crée pas de doublon
        # (grâce aussi à unique_together sur le modèle, en double sécurité).
        favori, cree = Favorite.objects.get_or_create(user=request.user, event_id=event_id)
        return Response(FavoriteSerializer(favori).data, status=status.HTTP_201_CREATED if cree else status.HTTP_200_OK)

    def delete(self, request, event_id):
        Favorite.objects.filter(user=request.user, event_id=event_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationListView(generics.ListAPIView):
    """GET /api/engagement/notifications/ — mes notifications."""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class NotificationMarkReadView(APIView):
    """PATCH /api/engagement/notifications/<id>/read/"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        notification = Notification.objects.filter(id=pk, user=request.user).first()
        if not notification:
            return Response({'erreur': 'Notification introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        notification.is_read = True
        notification.save()
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    """PATCH /api/engagement/notifications/read-all/"""
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'message': 'Toutes les notifications ont été marquées comme lues.'})
    
    

# Pourquoi elle est beaucoup plus légère que NotificationListView :
# .count() demande à la base de données de compter des lignes — une
# opération très rapide, optimisée nativement par PostgreSQL. Elle ne
# renvoie JAMAIS le contenu des notifications, juste un nombre. C'est
# CETTE vue-là qu'Angular appellera toutes les 15-20 secondes, pas la
# liste complète.
 
class NotificationCountView(APIView):
    """GET /api/engagement/notifications/count/ — juste le nombre de non lues."""
    permission_classes = [IsAuthenticated]
 
    def get(self, request):
        nombre = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'non_lues': nombre})

