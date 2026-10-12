from rest_framework import serializers

from .models import Favorite, Notification


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ['id', 'event', 'created_at']
        read_only_fields = ['created_at']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'type', 'title', 'message', 'is_read', 'created_at']