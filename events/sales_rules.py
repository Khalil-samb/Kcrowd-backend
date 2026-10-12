# ============================================================================
# events/sales_rules.py — UN BILLET PEUT-IL ÊTRE VENDU MAINTENANT ?
#
# Avant ce fichier, l'achat ne vérifiait que le stock : un événement en brouillon,
# annulé, terminé, aux ventes closes ou pas encore ouvertes se vendait quand même,
# et la limite d'achat réglée par l'organisateur n'était lue nulle part.
# Ce sont les réglages de l'étape « Conditions de vente » : ils doivent être RESPECTÉS
# par le serveur, pas seulement affichés.
# ============================================================================

from django.utils import timezone


def raison_de_refuser_la_vente(type_billet, quantite, maintenant=None):
    """
    Pourquoi cette vente doit être refusée (un message pour l'acheteur), ou None si elle est permise.
    Le stock n'est PAS vérifié ici : l'achat le fait déjà, sous verrou.
    """
    maintenant = maintenant or timezone.now()
    evenement = type_billet.event

    # « complet » n'est pas une raison de refus ici : c'est le stock qui tranche, avec son propre message
    if evenement.status not in ('published', 'sold_out'):
        return {
            'draft': "Cet événement n'est pas encore en vente.",
            'cancelled': "Cet événement a été annulé.",
            'finished': "Cet événement est terminé.",
        }.get(evenement.status, "Cet événement n'est pas en vente.")

    if evenement.end_date <= maintenant:
        return "Cet événement est terminé."

    if not type_billet.is_active:
        return "Cette catégorie de billets n'est plus en vente."

    if evenement.sales_open_at and maintenant < evenement.sales_open_at:
        ouverture = timezone.localtime(evenement.sales_open_at).strftime('%d/%m/%Y à %H:%M')
        return f"La billetterie ouvre le {ouverture}."

    if evenement.sales_close_at and maintenant >= evenement.sales_close_at:
        return "La billetterie est fermée."

    limite = evenement.max_tickets_per_purchase
    if limite and quantite > limite:
        return f"Vous ne pouvez pas acheter plus de {limite} billet{'s' if limite > 1 else ''} par commande."

    return None


def etat_des_ventes(evenement, maintenant=None):
    """
    L'état des ventes d'un événement, pour l'AFFICHAGE (catalogue, fiche) : l'écran grise ce qui n'est plus achetable
    au lieu de le cacher.  Valeurs :
        'open'         billets en vente
        'sold_out'     complet
        'not_open'     la billetterie n'a pas encore ouvert
        'closed'       la billetterie est clôturée (événement pas encore fini)
        'ended'        l'événement est terminé (statut « terminé » OU date de fin dépassée)
        'unavailable'  brouillon ou annulé
    L'achat, lui, reste protégé par raison_de_refuser_la_vente() : cet état n'est qu'une information.
    """
    maintenant = maintenant or timezone.now()
    if evenement.status in ('draft', 'cancelled'):
        return 'unavailable'
    if evenement.status == 'finished' or evenement.end_date <= maintenant:
        return 'ended'
    if evenement.status == 'sold_out':
        return 'sold_out'
    if evenement.sales_open_at and maintenant < evenement.sales_open_at:
        return 'not_open'
    if evenement.sales_close_at and maintenant >= evenement.sales_close_at:
        return 'closed'
    return 'open'