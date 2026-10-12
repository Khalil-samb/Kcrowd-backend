# ============================================================================
# platform_settings/services.py
#
# TOUS les calculs de commission du projet passent par ce fichier. Avant, la
# formule « montant × 0,05 » était recopiée à 7 endroits (2 côté Django, 5 côté
# Angular) : changer le taux aurait demandé de les retrouver tous.
# ============================================================================

from decimal import Decimal

from django.db.models import F, FloatField, Sum, Value
from django.db.models.expressions import ExpressionWrapper
from django.db.models.functions import Cast, Coalesce

from .models import TAUX_HISTORIQUE, PlatformSettings, TransactionCommission


def get_commission_rate() -> Decimal:
    """Le taux en vigueur MAINTENANT (en %)."""
    return PlatformSettings.load().commission_rate


def enregistrer_commission(transaction) -> None:
    """
    À appeler juste après la création d'une Transaction d'achat de billet :
    fige le taux en vigueur à cet instant. Les publicités sponsorisées n'ont pas
    de taux (100 % du montant revient à la plateforme), elles sont ignorées.
    """
    if transaction.type != 'ticket_purchase':
        return
    TransactionCommission.objects.get_or_create(
        transaction=transaction, defaults={'rate': get_commission_rate()},
    )


def taux_applique(transaction) -> Decimal:
    """Le taux (en %) appliqué à cette vente ; 5 % pour les ventes antérieures à ce module."""
    figee = getattr(transaction, 'commission_snapshot', None)  # None si aucune ligne
    return figee.rate if figee is not None else TAUX_HISTORIQUE


def commission_de(transaction) -> float:
    """Ce que cette transaction rapporte à Kcrowd."""
    if transaction.type == 'sponsored_ad':
        return float(transaction.amount)  # 100 % du montant
    if transaction.type == 'ticket_purchase':
        return float(transaction.amount) * float(taux_applique(transaction)) / 100.0
    return 0.0


# ---------------------------------------------------------------------------
# Versions « base de données » : une seule requête SQL, pour de gros volumes.
# Les ventes sans taux figé (anciennes) retombent sur TAUX_HISTORIQUE.
# ---------------------------------------------------------------------------

def _taux_sql():
    return Coalesce(
        Cast('commission_snapshot__rate', FloatField()),
        Value(float(TAUX_HISTORIQUE)),
        output_field=FloatField(),
    )


def somme_commission_ventes(transactions) -> float:
    """Σ commission des ventes de billets réussies du queryset donné."""
    total = (
        transactions.filter(type='ticket_purchase', status='success')
        .aggregate(total=Sum(ExpressionWrapper(F('amount') * _taux_sql() / Value(100.0), output_field=FloatField())))['total']
    )
    return float(total or 0.0)


def somme_ventes_nettes(transactions) -> float:
    """Σ de ce qui revient aux organisateurs (montant moins commission) sur les ventes réussies."""
    total = (
        transactions.filter(type='ticket_purchase', status='success')
        .aggregate(total=Sum(ExpressionWrapper(F('amount') * (Value(100.0) - _taux_sql()) / Value(100.0), output_field=FloatField())))['total']
    )
    return float(total or 0.0)