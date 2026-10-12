# Le cœur du catalogue : un événement, ses catégories de billets, et son
# programme détaillé.

import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models

from accounts.models import Organizer

class Event(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('published', 'Publié'),
        ('sold_out', 'Complet'),
        ('finished', 'Terminé'),
        ('cancelled', 'Annulé'),
    ]
    FEES_CHOICES = [
        ('organizer', 'Organisateur'),
        ('buyer', 'Acheteur'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizer = models.ForeignKey(Organizer, on_delete=models.CASCADE, related_name='events')
    
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    category_id = models.CharField(max_length=50)
    experience_format = models.CharField(max_length=100, blank=True, null=True)
    city_id = models.CharField(max_length=50)

    venue = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True)

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    doors_open_time = models.DateTimeField(blank=True, null=True)

    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    cover_image_url = models.URLField()
    banner_image_url = models.URLField(blank=True, null=True)
    
    # QU'EST-CE QU'UN ArrayField ?
    # ------------------------------------------------------------------
    # PostgreSQL sait stocker directement une LISTE de valeurs dans une
    # seule colonne (ce que ne savent pas faire MySQL ou SQLite nativement).
    # Sans ça, il faudrait créer une table séparée juste pour stocker une
    # simple liste de noms d'artistes ou d'URLs — ArrayField évite cette
    # complexité pour des listes simples qu'on n'a pas besoin d'interroger
    # individuellement (on ne cherche jamais "tous les événements où tel
    # artiste précis apparaît", donc pas besoin d'une vraie table).
    gallery_urls = ArrayField(models.URLField(), default=list, blank=True)
    teaser_video_url = models.URLField(blank=True, null=True)
    lineup = ArrayField(models.CharField(max_length=150), default=list, blank=True)
    
    max_capacity = models.PositiveIntegerField()
    max_tickets_per_purchase = models.PositiveIntegerField(blank=True, null=True)
    sales_open_at = models.DateTimeField(blank=True, null=True)
    sales_close_at = models.DateTimeField(blank=True, null=True)
    fees_born_by = models.CharField(max_length=20, choices=FEES_CHOICES, default='organizer')
    accepted_payment_methods = ArrayField(models.CharField(max_length=20), default=list, blank=True)

    # Réglages enregistrés mais pas encore fonctionnels sans backend temps
    # réel / application Flutter des agents (voir mémoire, partie organisateur).
    offline_mode_enabled = models.BooleanField(default=False)
    anti_passback_enabled = models.BooleanField(default=False)
    allow_temporary_exits = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_sponsored = models.BooleanField(default=False)
    average_rating = models.FloatField(default=0)
    review_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    

class TicketType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_types')

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    perks = ArrayField(models.CharField(max_length=150), default=list, blank=True)

    price = models.FloatField()
    quantity_total = models.PositiveIntegerField()
    quantity_sold = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} — {self.event.title}"
    


class EventScheduleItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='schedule_items')

    time = models.CharField(max_length=20)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField()

    class Meta:
        # Garantit que Django (et PostgreSQL) trie toujours les entrées du
        # programme dans le bon ordre par défaut, sans avoir à le préciser
        # à chaque requête.
        ordering = ['order']