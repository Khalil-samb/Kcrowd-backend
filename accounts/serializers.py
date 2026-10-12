# Un "serializer" DRF a deux rôles :
# 1. En entrée : valider les données reçues (types corrects, champs
#    obligatoires présents) avant de les utiliser.
# 2. En sortie : convertir un objet Python/modèle Django en JSON pour
#    la réponse HTTP.
#
# Deux types différents utilisés ici :
# - Serializer (simple) : pour des données qui ne correspondent à aucun
#   modèle complet (ex. juste "email + mot de passe" pour se connecter).
# - ModelSerializer : sait automatiquement lire les champs d'un modèle
#   Django et les convertir en JSON, sans tout réécrire à la main.

from rest_framework import serializers
from .models import Organizer, User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'phone', 'first_name', 'last_name', 'email', 'role', 'status', 'city_id', 'avatar_url']
        

class OtpRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    

class OtpVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6)
 
    # allow_blank=True : accepte explicitement une chaîne vide ("").
    # required=False accepte que le champ soit absent. Ce sont 2 règles
    # différentes en DRF — il fallait les deux, pas l'une ou l'autre.
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
 

    
class OrganizerRegisterSerializer(serializers.Serializer):
    """
    Les champs du formulaire "Devenir organisateur" déjà construit côté
    Angular. La personne est déjà un utilisateur identifié (téléphone+OTP)
    à ce stade — cet endpoint transforme son compte existant, il n'en
    crée pas un nouveau depuis rien.
    """
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8)
    organization_name = serializers.CharField(max_length=200)
    registration_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    category_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(choices=['wave', 'orange_money'])
    mobile_money_account_number = serializers.CharField(max_length=30)
    mobile_money_account_holder = serializers.CharField(max_length=100)
    receoit_alertes_vente = serializers.BooleanField(default=True)
    
    
class OrganizerLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    
# Pourquoi : le téléphone et l'email d'un organisateur vivent sur son compte
# User, pas sur la fiche Organizer. La liste admin des utilisateurs ne
# contient QUE les comptes de rôle "user" : l'écran ne pouvait donc jamais
# retrouver le téléphone d'un organisateur. On l'ajoute directement à la
# réponse. (Avec fields = '__all__', les champs déclarés ici sont inclus.)
# ============================================================================
 
class OrganizerSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source='user.phone', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
 
    class Meta:
        model = Organizer
        fields = '__all__'

