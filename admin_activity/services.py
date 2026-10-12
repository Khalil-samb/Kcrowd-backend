# Même logique que engagement/services.py : une fonction unique, appelée
# depuis n'importe quelle autre app, pour ne jamais avoir 2 façons
# différentes de créer une entrée de journal.

from .models import AdminActivityLog


def journaliser(type_activite: str, message: str, user=None, organizer=None, event=None) -> AdminActivityLog:
    return AdminActivityLog.objects.create(
        type=type_activite,
        message=message,
        related_user=user,
        related_organizer=organizer,
        related_event=event,
    )