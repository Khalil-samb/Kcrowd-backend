from rest_framework import serializers

from .models import SponsoredAd


class SponsoredAdSerializer(serializers.ModelSerializer):
    class Meta:
        model = SponsoredAd
        fields = '__all__'


class AcheterCampagneSerializer(serializers.Serializer):
    # Une seule offre fixe, définie côté serveur : jamais de montant envoyé par le client.
    formule = serializers.ChoiceField(choices=['boost'], default='boost')
