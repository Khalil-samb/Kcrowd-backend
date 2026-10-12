
# Cette app gère TOUT ce qui concerne "qui fait la demande" :
# - Les utilisateurs (grand public, organisateurs, administrateurs confondus)
# - Les organisateurs (informations supplémentaires liées à un utilisateur)
# - Les codes OTP temporaires (pour la connexion par téléphone)

import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models


# En Django, le "Manager" est l'objet qui sait comment CRÉER des lignes dans
# la table (via .objects.create_user(...) par exemple). Le Manager par défaut
# de Django suppose un couple username+password classique. Comme notre
# identifiant est le téléphone (et que le mot de passe est optionnel, réservé
# aux organisateurs/admins), on doit fournir notre propre logique de création.

class UserManager(models.Manager):
    def create_user(self, phone, **extra_fields):
        """Crée un utilisateur simple (grand public), identifié par son téléphone."""
        user = self.model(phone=phone, **extra_fields)
        user.save()
        return user

# AbstractBaseUser nous donne le strict socle nécessaire (mot de passe haché,
# gestion de session) SANS nous imposer la structure de champs de Django.

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('user', 'Utilisateur'),
        ('organizer', 'Organisateur'),
        ('admin', 'Administrateur'),
    ]
    STATUS_CHOICES = [
        ('active', 'Actif'),
        ('suspended', 'Suspendu'),
    ]
    # Par défaut, Django utilise un simple entier auto-incrémenté (1, 2, 3...)
    # comme identifiant. On préfère un UUID (identifiant unique universel,
    # une longue chaîne aléatoire) pour deux raisons :
    # 1. Sécurité : on ne peut pas deviner "l'id suivant" en changeant un chiffre
    #    dans une URL (contrairement à /users/1, /users/2...).
    # 2. Cohérence avec le frontend, qui utilise déjà des identifiants texte.
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    phone = models.CharField(max_length=20, unique=True)
    phone_verified = models.BooleanField(default=False)
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)

    # Optionnels car un utilisateur grand public (role='user') n'a besoin
    # que du téléphone. L'email + mot de passe ne servent qu'aux comptes
    # organisateur/admin.
    email = models.EmailField(unique=True, blank=True, null=True)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    city_id = models.CharField(max_length=50, blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    
    # Champs exigés par Django pour que l'authentification standard fonctionne
    # correctement (utilisés en interne par Django, pas par notre logique métier).
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
 
    objects = UserManager()

    # C'est ICI qu'on dit à Django : "l'identifiant de connexion, c'est le
    # téléphone, pas un username". C'est ce qui rend possible d'avoir un
    # système d'auth cohérent même si nos deux méthodes de connexion
    # (OTP téléphone / email+mot de passe) sont gérées à la main plus tard.
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['first_name']

    def __str__(self):
        return f"{self.first_name} ({self.phone})"
    
    
    
    
    
class Organizer(models.Model):
    PAYMENT_CHOICES = [
        ('wave', 'Wave'),
        ('orange_money', 'Orange Money'),
    ]
    STATUS_CHOICES = [
        ('active', 'Actif'),
        ('suspended', 'Suspendu'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # OneToOneField = "un Organizer correspond à exactement un User, et
    # inversement". related_name='organizer' permet, depuis un objet user,
    # d'écrire user.organizer pour retrouver ses infos d'organisateur.
    # on_delete=CASCADE : si le User est supprimé, son Organizer l'est aussi
    # automatiquement (pas de fiche organisateur "orpheline" en base).
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='organizer')
 
    organization_name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=100, blank=True, null=True)
    category_id = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    logo_url = models.URLField(blank=True, null=True)
 
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    mobile_money_account_number = models.CharField(max_length=30)
    mobile_money_account_holder = models.CharField(max_length=100)
    receoit_alertes_vente = models.BooleanField(default=True)
 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return self.organization_name


# Un code OTP est temporaire et jetable (il expire, on peut en redemander un
# nouveau). Le stocker sur User compliquerait le modèle pour quelque chose
# qui n'a de sens que pendant quelques minutes. Un modèle séparé permet aussi
# de garder un historique (utile pour du debug ou de la détection de fraude :
# "cette personne a demandé 10 codes en 1 minute").
class OtpCode(models.Model):
    phone = models.CharField(max_length=20)
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return f"OTP {self.code} pour {self.phone}"
