import uuid

from django.db import models


class Favorite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='favorites')
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # unique_together empêche la même personne de mettre 2 fois le
        # même événement en favori — Django refusera silencieusement le
        # doublon au niveau de la base, pas seulement dans notre code Python.
        unique_together = ('user', 'event')


class Notification(models.Model):
    TYPE_CHOICES = [
        ('event_reminder', 'Rappel événement'),
        ('payment_confirmation', 'Confirmation de paiement'),
        ('new_event', 'Nouvel événement'),
        ('new_sale', 'Nouvelle vente'),
        ('system', 'Système'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']