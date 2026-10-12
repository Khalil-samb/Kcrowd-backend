# ============================================================================
# platform_settings/models.py
#
# Le seul réglage de la plateforme qui agit réellement sur l'argent : le taux
# de commission que Kcrowd prélève sur chaque billet vendu.
#
# POURQUOI TROIS TABLES ?
#
# 1. PlatformSettings       : le taux EN VIGUEUR aujourd'hui (une seule ligne).
# 2. CommissionRateChange   : l'historique « qui a changé le taux, quand, de
#                             combien à combien » — indispensable dès qu'un
#                             réglage touche à l'argent.
# 3. TransactionCommission  : le taux APPLIQUÉ À CETTE VENTE, figé au moment de
#                             l'achat.
#
# C'est la 3e qui compte : sans elle, passer le taux de 5 % à 7 % recalculerait
# TOUTES les anciennes ventes à 7 %, y compris celles d'événements déjà reversés
# aux organisateurs. Faux comptablement. Avec elle, une vente garde pour
# toujours le taux qui était en vigueur le jour où elle a eu lieu.
# ============================================================================

from decimal import Decimal

from django.conf import settings
from django.db import models

# Le taux appliqué avant que la commission devienne configurable : les ventes
# plus anciennes que ce module n'ont pas de taux figé et gardent donc ces 5 %.
TAUX_HISTORIQUE = Decimal('5.00')

# Garde-fou : une faute de frappe (« 50 » au lieu de « 5 ») ne doit pas pouvoir
# prélever la moitié des recettes de tous les organisateurs.
TAUX_MAX = Decimal('30.00')


class PlatformSettings(models.Model):
    """Réglages globaux : UNE SEULE ligne dans toute la table (toujours pk=1)."""
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=TAUX_HISTORIQUE)  # en %
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        verbose_name = 'Paramètres de la plateforme'
        verbose_name_plural = 'Paramètres de la plateforme'

    def save(self, *args, **kwargs):
        self.pk = 1  # impossible de créer une deuxième ligne de réglages
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Les réglages de la plateforme ne peuvent pas être supprimés.")

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Commission : {self.commission_rate} %"


class CommissionRateChange(models.Model):
    """Une ligne par changement du taux : le journal d'audit du réglage."""
    old_rate = models.DecimalField(max_digits=5, decimal_places=2)
    new_rate = models.DecimalField(max_digits=5, decimal_places=2)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+',
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at', '-id']

    def __str__(self):
        return f"{self.old_rate} % → {self.new_rate} % ({self.changed_at:%d/%m/%Y})"


class TransactionCommission(models.Model):
    """Le taux de commission appliqué à UNE vente de billet, figé au moment de l'achat."""
    transaction = models.OneToOneField(
        'transactions.Transaction', on_delete=models.CASCADE, primary_key=True, related_name='commission_snapshot',
    )
    rate = models.DecimalField(max_digits=5, decimal_places=2)  # en %
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_id} : {self.rate} %"