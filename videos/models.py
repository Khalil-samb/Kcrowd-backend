# Les vidéos que les organisateurs rattachent à leurs événements (fil « Vidéos » du site).
#
# Règles de vie, décidées côté serveur :
#   - une vidéo appartient à UN événement publié de SON organisateur ;
#   - quand l'événement se termine, ses vidéos (fichiers compris) sont supprimées (voir services.py) ;
#   - les vues et les « j'aime » sont comptés ici, jamais par le navigateur.
import uuid

from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver


def chemin_de_la_video(instance, nom_fichier):
    # Nom aléatoire : jamais le nom d'origine (accents, espaces, collisions, noms devinables).
    extension = nom_fichier.rsplit('.', 1)[-1].lower() if '.' in nom_fichier else 'mp4'
    return f'videos/{uuid.uuid4().hex}.{extension}'


class EventVideo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='videos')
    organizer = models.ForeignKey('accounts.Organizer', on_delete=models.CASCADE, related_name='videos')

    title = models.CharField(max_length=120, blank=True, default='')
    file = models.FileField(upload_to=chemin_de_la_video)
    content_type = models.CharField(max_length=30, default='video/mp4')
    size_bytes = models.BigIntegerField(default=0)

    views_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title or f'Vidéo de {self.event.title}'


class VideoLike(models.Model):
    video = models.ForeignKey(EventVideo, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='video_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Un seul « j'aime » par personne et par vidéo, garanti par la base elle-même.
        constraints = [models.UniqueConstraint(fields=['video', 'user'], name='un_like_par_personne_et_par_video')]


@receiver(post_delete, sender=EventVideo)
def supprimer_le_fichier_de_la_video(sender, instance, **kwargs):
    # Supprimer la ligne en base ne supprime pas le fichier sur le disque : on le fait ici,
    # pour que « la vidéo est supprimée » soit vrai (et que le disque ne se remplisse pas).
    if instance.file:
        instance.file.delete(save=False)
