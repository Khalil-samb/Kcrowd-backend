from django.urls import reverse
from rest_framework import serializers

from .models import EventVideo, VideoLike


class VideoPubliqueSerializer(serializers.ModelSerializer):
    """Ce que voit le public dans le fil « Vidéos »."""
    video_url = serializers.SerializerMethodField()
    event = serializers.SerializerMethodField()
    organizer = serializers.SerializerMethodField()
    liked_by_me = serializers.SerializerMethodField()
    is_sponsored = serializers.SerializerMethodField()

    class Meta:
        model = EventVideo
        fields = ['id', 'title', 'video_url', 'event', 'organizer', 'views_count', 'likes_count',
                  'liked_by_me', 'is_sponsored', 'created_at']

    def get_video_url(self, video):
        return self.context['request'].build_absolute_uri(reverse('video-stream', args=[video.id]))

    def get_event(self, video):
        e = video.event
        return {'id': str(e.id), 'title': e.title, 'cover_image_url': e.cover_image_url,
                'start_date': e.start_date, 'venue': e.venue}

    def get_organizer(self, video):
        o = video.organizer
        return {'id': str(o.id), 'name': o.organization_name, 'logo_url': o.logo_url}

    def get_is_sponsored(self, video):
        return bool(video.event.is_sponsored)

    def get_liked_by_me(self, video):
        ids = self.context.get('ids_likes')
        return video.id in ids if ids is not None else False


class VideoOrganisateurSerializer(VideoPubliqueSerializer):
    """Ce que voit l'organisateur dans « Mes vidéos » (mêmes champs + la taille du fichier)."""
    class Meta(VideoPubliqueSerializer.Meta):
        fields = VideoPubliqueSerializer.Meta.fields + ['size_bytes']
