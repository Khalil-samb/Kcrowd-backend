# Cycle de vie automatique des événements.
# Un événement « publié » (ou « complet ») dont la date de fin est passée devient « terminé ».
# Aucune tâche planifiée n'est indispensable : la fonction est appelée à chaque lecture des listes et
# fiches d'événements, donc l'état affiché est toujours juste. La commande
# `python manage.py terminer_evenements` permet en plus de l'appeler depuis un cron.
#
# En passant à « terminé », un événement perd aussi ses vidéos (fichiers compris) et sa sponsorisation :
# voir videos/services.py.
from django.utils import timezone

from .models import Event

STATUTS_QUI_PEUVENT_TERMINER = ['published', 'sold_out']


def terminer_les_evenements_passes(maintenant=None):
    maintenant = maintenant or timezone.now()
    ids = list(Event.objects.filter(status__in=STATUTS_QUI_PEUVENT_TERMINER, end_date__lte=maintenant).values_list('id', flat=True))
    nb = 0
    if ids:
        nb = Event.objects.filter(id__in=ids).update(status='finished')

    # Événements déjà terminés mais encore marqués « sponsorisés » (cas d'avant cette version) : on nettoie aussi.
    anciens = list(Event.objects.filter(status='finished', is_sponsored=True).values_list('id', flat=True))
    a_nettoyer = ids + anciens
    if a_nettoyer:
        from videos.services import nettoyer_apres_evenements_termines
        nettoyer_apres_evenements_termines(a_nettoyer)
    return nb
