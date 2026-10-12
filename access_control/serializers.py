import random

from rest_framework import serializers

from .models import AccessGate, ScannerAgent


class AccessGateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessGate
        fields = ['id', 'event', 'name', 'label', 'allowed_ticket_type_ids', 'estimated_throughput_per_hour', 'status']
        read_only_fields = ['event']  # injecté depuis l'URL dans la vue, jamais depuis le client


class ScannerAgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScannerAgent
        fields = ['id', 'event', 'gate', 'name', 'phone', 'role', 'pin_code', 'created_at']
        # pin_code en lecture seule : on ne veut jamais qu'un client choisisse
        # lui-même son code, on le génère nous-mêmes à la création (voir create()).
        read_only_fields = ['event', 'pin_code', 'created_at']

    def create(self, validated_data):
        # create() est appelée automatiquement par serializer.save().
        # En la redéfinissant ici, on peut ajouter une valeur (pin_code)
        # qui n'a jamais été envoyée par le client, avant l'enregistrement réel.
        validated_data['pin_code'] = f"{random.randint(0, 9999):04d}"
        return super().create(validated_data)