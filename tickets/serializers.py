# ============================================================================
# tickets/serializers.py — FICHIER COMPLET, remplace tout le contenu actuel
# ============================================================================

from rest_framework import serializers

from .models import Ticket


class TicketSerializer(serializers.ModelSerializer):
    buyer_name = serializers.SerializerMethodField()
    buyer_phone = serializers.SerializerMethodField()
    ticket_type_name = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            'id', 'ticket_type', 'event', 'user', 'transaction', 'qr_code',
            'status', 'price', 'purchase_date', 'scanned_at', 'gate',
            'scanned_by_agent', 'dispute_status', 'buyer_name', 'buyer_phone',
            'ticket_type_name',
        ]

    def get_buyer_name(self, ticket):
        return f"{ticket.user.first_name} {ticket.user.last_name or ''}".strip()

    def get_buyer_phone(self, ticket):
        return ticket.user.phone

    def get_ticket_type_name(self, ticket):
        return ticket.ticket_type.name


class AchatBilletSerializer(serializers.Serializer):
    ticket_type_id = serializers.UUIDField()
    payment_method = serializers.ChoiceField(choices=['wave', 'orange_money', 'free_money', 'card'])
    quantite = serializers.IntegerField(min_value=1, default=1)


class ScanBilletSerializer(serializers.Serializer):
    qr_code = serializers.CharField(required=False, allow_blank=True)
    reference = serializers.CharField(required=False, allow_blank=True)
    gate_id = serializers.UUIDField(required=False)

    def validate(self, donnees):
        if not donnees.get('qr_code') and not donnees.get('reference'):
            raise serializers.ValidationError("Fournissez soit qr_code, soit reference.")
        return donnees