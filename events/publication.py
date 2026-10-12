# ============================================================================
# events/publication.py — QUI PEUT CHANGER LE STATUT D'UN ÉVÉNEMENT, ET QUAND
#
# Avant ce fichier, l'organisateur pouvait s'imposer n'importe quel statut
# (« terminé », « annulé », « complet »...) et publier un événement sans billets
# ni date valide. Désormais, le SERVEUR décide — l'écran ne fait que prévenir.
#
# Ce que l'organisateur peut faire :
#     brouillon  → publié    seulement si l'événement est PRÊT (voir ci-dessous)
#     publié     → brouillon seulement s'il n'y a eu AUCUNE vente
#
# Ce que l'organisateur ne peut PAS faire :
#     « complet » : calculé automatiquement d'après le stock (voir availability.py)
#     « terminé » / « annulé » : jamais depuis cet écran, et définitifs
# ============================================================================

from django.utils import timezone


def erreurs_publication(evenement, debut, cloture=None):
    """
    Ce qui empêche de publier cet événement (liste vide = il est prêt).
    `debut` et `cloture` = les dates qui seront EN VIGUEUR après l'enregistrement
    (l'organisateur peut les corriger dans la même requête).
    """
    erreurs = []
    if not evenement.ticket_types.filter(is_active=True, quantity_total__gt=0).exists():
        erreurs.append("Ajoutez au moins une catégorie de billets active avec des places avant de publier.")
    if debut is None or debut <= timezone.now():
        erreurs.append("La date de début est déjà passée : modifiez-la avant de publier.")
    if cloture is not None and cloture <= timezone.now():
        erreurs.append("La date de clôture des ventes est déjà passée : les ventes seraient fermées dès la publication. Modifiez-la ou videz-la avant de publier.")
    return erreurs


def erreurs_changement_statut(evenement, nouveau, debut, cloture=None):
    """Les raisons de refuser le passage de evenement.status à `nouveau` (liste vide = autorisé)."""
    actuel = evenement.status

    if nouveau == actuel:
        return []  # un écran qui renvoie le statut tel quel ne change rien

    if actuel in ('finished', 'cancelled'):
        return ["Un événement terminé ou annulé ne peut plus changer de statut."]

    if actuel == 'draft' and nouveau == 'published':
        return erreurs_publication(evenement, debut, cloture)

    if actuel == 'published' and nouveau == 'draft':
        if evenement.ticket_types.filter(quantity_sold__gt=0).exists():
            return ["Des billets ont déjà été vendus : l'événement ne peut plus repasser en brouillon."]
        return []

    return ["Ce changement de statut n'est pas autorisé : « Complet », « Terminé » et « Annulé » sont gérés automatiquement."]