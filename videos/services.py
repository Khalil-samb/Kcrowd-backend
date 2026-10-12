from django.db.models import F

from .models import EventVideo


def nettoyer_apres_evenements_termines(ids_evenements):
    """Appelé quand des événements viennent de passer à « terminé » :
    - leurs vidéos sont supprimées (lignes ET fichiers) ;
    - leur sponsorisation prend fin (plus de badge « à la une », annonces expirées)."""
    if not ids_evenements:
        return 0
    from events.models import Event
    from sponsorship.models import SponsoredAd

    nb = 0
    for video in EventVideo.objects.filter(event_id__in=ids_evenements):
        video.delete()          # un par un : le signal supprime aussi le fichier du disque
        nb += 1
    SponsoredAd.objects.filter(event_id__in=ids_evenements, status='active').update(status='expired')
    Event.objects.filter(id__in=ids_evenements, is_sponsored=True).update(is_sponsored=False)
    return nb
