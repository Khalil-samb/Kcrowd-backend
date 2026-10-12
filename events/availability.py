"""
Statut « complet » d'un événement : UNE seule règle, à UN seul endroit.

Le catalogue public n'a pas accès aux quantités de billets (il ne reçoit que
l'état de l'événement) : c'est le champ `status` qui fait apparaître le badge
« Épuisé ». Ce statut doit donc toujours refléter le stock réel :

- tout est vendu            -> 'sold_out'  (badge « Épuisé »)
- il reste des places       -> 'published' (vente ouverte)

Cette règle est appelée à la fois quand un client ACHÈTE un billet et quand
l'organisateur MODIFIE son stock : les deux sens sont ainsi toujours cohérents.

Seuls 'published' et 'sold_out' sont concernés : un brouillon, un événement
terminé ou annulé ne doit JAMAIS être rouvert par un simple changement de stock.
"""
from django.db import transaction

from .models import Event, TicketType


def recalculer_statut_complet(event):
    """
    Aligne event.status sur le stock des catégories de billets ACTIVES.
    Renvoie le statut final.

     POURQUOI ON VERROUILLE L'ÉVÉNEMENT ET NON LES CATÉGORIES :
    cette fonction est appelée PENDANT un achat, qui détient déjà le verrou
    d'UNE catégorie. Si elle verrouillait aussi les autres catégories, deux
    achats simultanés sur deux catégories d'un même événement s'attendraient
    mutuellement (chacun tient une catégorie et réclame celle de l'autre) :
    PostgreSQL annule alors l'un des deux — le client voit une erreur en plein
    paiement. (Reproduit en test : ça arrive à chaque tentative.)

    À la place, on verrouille la ligne de l'événement. Tous les recalculs d'un
    même événement passent ainsi l'un après l'autre : le DERNIER lit le stock
    de tous les achats déjà validés, donc le statut final est toujours juste.
    (Mesuré : SANS ce verrou, deux achats simultanés qui vendent chacun la
    dernière place de leur catégorie laissent l'événement « en vente » alors que
    tout est vendu — à chaque essai.)

    no_key=True (FOR NO KEY UPDATE) est le verrou le plus léger qui suffit ici :
    on ne modifie jamais la clé de l'événement, seulement son statut.
    """
    with transaction.atomic():
        evenement = Event.objects.select_for_update(no_key=True).only('id', 'status').get(pk=event.pk)
        statut_actuel = evenement.status

        if statut_actuel not in ('published', 'sold_out'):
            return statut_actuel

        stocks = list(
            TicketType.objects.filter(event_id=event.pk, is_active=True)
            .values_list('quantity_sold', 'quantity_total')
        )
        if not stocks:
            return statut_actuel  # aucune catégorie active : on ne décide rien

        epuise = all(vendus >= total for vendus, total in stocks)
        nouveau = 'sold_out' if epuise else 'published'

        if nouveau != statut_actuel:
            # update() ciblé : ne réécrit QUE le statut. Un save() complet
            # réécrirait toutes les colonnes depuis une copie possiblement périmée.
            Event.objects.filter(pk=event.pk).update(status=nouveau)
        event.status = nouveau
        return nouveau