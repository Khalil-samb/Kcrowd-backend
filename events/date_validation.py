"""
Règles de dates d'un événement, côté serveur : la VRAIE protection.
Le formulaire Angular donne un message clair, mais n'importe qui peut
contourner Angular et envoyer la requête à la main : seul Django peut
garantir qu'un événement n'est jamais créé dans le passé.

Fonction pure (pas d'accès à la base) : facile à tester.
"""
from django.utils import timezone


def _a_la_minute(dt):
    return dt.replace(second=0, microsecond=0)


def erreurs_dates_evenement(debut, fin, debut_initial=None, creation=True, maintenant=None):
    """
    Renvoie un dict {champ: message}, vide si tout est valide.

    - À la création : le début doit être dans le futur.
    - En modification : le début n'est vérifié que s'il CHANGE. Sinon, un
      organisateur ne pourrait plus corriger une faute dans la description
      d'un événement déjà commencé.
    - Dans tous les cas : la fin doit être strictement après le début.
    """
    erreurs = {}
    maintenant = maintenant or timezone.now()

    if debut is not None:
        debut_change = (
            creation
            or debut_initial is None
            or _a_la_minute(debut) != _a_la_minute(debut_initial)
        )
        if debut_change and debut <= maintenant:
            erreurs['start_date'] = "La date et l'heure de début doivent être dans le futur."

    if debut is not None and fin is not None and fin <= debut:
        erreurs['end_date'] = "La date de fin doit être postérieure à la date de début."

    return erreurs