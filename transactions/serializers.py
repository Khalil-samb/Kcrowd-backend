from rest_framework import serializers

from platform_settings.services import commission_de, taux_applique
 
from .models import Transaction
 
 
class TransactionSerializer(serializers.ModelSerializer):
    # Le taux (en %) appliqué à CETTE vente, figé le jour de l'achat, et ce qu'elle
    # rapporte à Kcrowd. Le frontend ne recalcule plus rien : il additionne.
    commission_rate = serializers.SerializerMethodField()
    commission_amount = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = '__all__'

    def get_commission_rate(self, obj):
        if obj.type != 'ticket_purchase':
            return None  # une publicité sponsorisée n'a pas de taux : 100 % revient à la plateforme
        return float(taux_applique(obj))

    def get_commission_amount(self, obj):
        return round(commission_de(obj), 2)