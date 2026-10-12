import os
import uuid

from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from accounts.permissions import IsAdmin, IsOrganizer
from events.lifecycle import terminer_les_evenements_passes
from events.models import Event
from .models import EventVideo, VideoLike
from .rules import erreur_de_fichier, raison_de_refuser_la_video, type_mime_du_fichier
from .serializers import VideoOrganisateurSerializer, VideoPubliqueSerializer
from .streaming import reponse_avec_range

LIMITE_FIL = 100


def _ids_aimes(request, videos):
    """Les vidéos de la liste que la personne connectée a déjà aimées (un seul appel à la base)."""
    user = request.user
    if not (user and user.is_authenticated):
        return set()
    return set(VideoLike.objects.filter(user=user, video__in=videos).values_list('video_id', flat=True))


class FilVideosView(APIView):
    """
    GET /api/videos/  — le fil public. Optionnel : ?event=<id> (vidéos d'un seul événement).
    Seules les vidéos d'événements EN COURS DE VENTE s'affichent. Ordre : événements sponsorisés
    d'abord, puis les plus récentes.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        terminer_les_evenements_passes()
        maintenant = timezone.now()
        qs = (EventVideo.objects
              .select_related('event', 'organizer')
              .filter(event__status__in=['published', 'sold_out'], event__end_date__gt=maintenant))
        if request.query_params.get('event'):
            qs = qs.filter(event_id=request.query_params['event'])
        videos = list(qs.order_by('-event__is_sponsored', '-created_at')[:LIMITE_FIL])
        serializer = VideoPubliqueSerializer(videos, many=True, context={'request': request, 'ids_likes': _ids_aimes(request, videos)})
        return Response(serializer.data)


class VideoStreamView(APIView):
    """GET /api/videos/<id>/stream/ — le fichier vidéo, lisible par morceaux (voir streaming.py)."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, pk):
        video = get_object_or_404(EventVideo, pk=pk)
        if not video.file or not os.path.exists(video.file.path):
            return Response({'erreur': 'Fichier introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return reponse_avec_range(request, video.file.path, video.content_type)


class LimiteVues(AnonRateThrottle):
    rate = '120/min'


class CompterVueView(APIView):
    """POST /api/videos/<id>/view/ — appelée par le lecteur après quelques secondes de lecture."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LimiteVues]

    def post(self, request, pk):
        if not EventVideo.objects.filter(pk=pk).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        EventVideo.objects.filter(pk=pk).update(views_count=F('views_count') + 1)
        return Response({'views_count': EventVideo.objects.get(pk=pk).views_count})


class AimerView(APIView):
    """POST /api/videos/<id>/like/ — j'aime ; DELETE — je n'aime plus. Il faut être identifié."""
    permission_classes = [IsAuthenticated]

    def _reponse(self, video, aime):
        video.refresh_from_db(fields=['likes_count'])
        return Response({'liked': aime, 'likes_count': video.likes_count})

    def post(self, request, pk):
        video = get_object_or_404(EventVideo, pk=pk)
        with transaction.atomic():
            _, cree = VideoLike.objects.get_or_create(video=video, user=request.user)
            if cree:
                EventVideo.objects.filter(pk=pk).update(likes_count=F('likes_count') + 1)
        return self._reponse(video, True)

    def delete(self, request, pk):
        video = get_object_or_404(EventVideo, pk=pk)
        with transaction.atomic():
            supprimes, _ = VideoLike.objects.filter(video=video, user=request.user).delete()
            if supprimes:
                EventVideo.objects.filter(pk=pk).update(likes_count=F('likes_count') - 1)
        return self._reponse(video, False)


class MesVideosView(APIView):
    """
    GET  /api/videos/mine/?event=<id> — les vidéos de l'organisateur connecté.
    POST /api/videos/mine/            — ajoute une vidéo (multipart : event, title, file).
    """
    permission_classes = [IsOrganizer]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        terminer_les_evenements_passes()
        qs = EventVideo.objects.select_related('event', 'organizer').filter(organizer=request.user.organizer)
        if request.query_params.get('event'):
            qs = qs.filter(event_id=request.query_params['event'])
        videos = list(qs)
        return Response(VideoOrganisateurSerializer(videos, many=True, context={'request': request, 'ids_likes': set()}).data)

    def post(self, request):
        terminer_les_evenements_passes()
        id_evenement = request.data.get('event')
        if not id_evenement:
            return Response({'erreur': "Choisissez l'événement de cette vidéo."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            evenement = Event.objects.get(pk=uuid.UUID(str(id_evenement)), organizer=request.user.organizer)
        except (ValueError, Event.DoesNotExist):
            return Response({'erreur': 'Événement introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        raison = raison_de_refuser_la_video(evenement, evenement.videos.count())
        if raison:
            return Response({'erreur': raison}, status=status.HTTP_400_BAD_REQUEST)

        fichier = request.FILES.get('file')
        erreur = erreur_de_fichier(fichier)
        if erreur:
            return Response({'erreur': erreur}, status=status.HTTP_400_BAD_REQUEST)

        video = EventVideo.objects.create(
            event=evenement,
            organizer=request.user.organizer,
            title=(request.data.get('title') or '').strip()[:120],
            file=fichier,
            content_type=type_mime_du_fichier(fichier.name),
            size_bytes=fichier.size,
        )
        return Response(VideoOrganisateurSerializer(video, context={'request': request, 'ids_likes': set()}).data,
                        status=status.HTTP_201_CREATED)


class MaVideoView(APIView):
    """DELETE /api/videos/mine/<id>/ — l'organisateur supprime SA vidéo."""
    permission_classes = [IsOrganizer]

    def delete(self, request, pk):
        video = get_object_or_404(EventVideo, pk=pk, organizer=request.user.organizer)
        video.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ModerationVideoView(APIView):
    """DELETE /api/videos/admin/<id>/ — l'administrateur retire n'importe quelle vidéo."""
    permission_classes = [IsAdmin]

    def delete(self, request, pk):
        get_object_or_404(EventVideo, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
