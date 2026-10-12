# Le calcul du solde disponible, isolé dans sa propre fonction : il est
# utilisé à 2 endroits (afficher le solde, ET vérifier qu'il y a bien de
# quoi payer avant d'accepter une demande) — pas question de dupliquer
# cette formule à deux endroits différents, au risque qu'elle diverge un jour.


from django.db.models import Sum

from platform_settings.services import somme_ventes_nettes
from transactions.models import Transaction
from .models import Payout


def calculer_solde_disponible(organizer) -> int:
    # Ce qui revient à l'organisateur : chaque vente moins la commission figée le jour
    # de l'achat. Plus de « 0,95 » écrit en dur : si l'admin change le taux, seules les
    # ventes FUTURES sont concernées, jamais celles déjà reversées.
    net_du = somme_ventes_nettes(Transaction.objects.filter(event__organizer=organizer))

    deja_verse = (
        Payout.objects.filter(organizer=organizer, status__in=['completed','pending'])
        .aggregate(total=Sum('amount'))['total']
        or 0
    )

    return max(0, round(net_du - deja_verse))