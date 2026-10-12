# Une Transaction garde une trace de CHAQUE mouvement d'argent entrant :
# l'achat d'un billet, ou l'achat d'une publicité sponsorisée. Séparée de
# Ticket parce qu'une transaction peut couvrir PLUSIEURS billets d'un coup
# (achat groupé), et parce que le type "sponsored_ad" n'a rien à voir
# avec un billet.

import uuid

from django.db import models

from accounts.models import User
from events.models import Event


class Transaction(models.Model):
    TYPE_CHOICES = [
        ('ticket_purchase', 'Achat de billet'),
        ('sponsored_ad', 'Publicité sponsorisée'),
    ]
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('success', 'Réussie'),
        ('failed', 'Échouée'),
        ('refunded', 'Remboursée'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='transactions')

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.FloatField()
    payment_method = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # unique=True : deux transactions ne peuvent jamais partager la même
    # référence — utile pour retrouver une transaction précise sans
    # ambiguïté (par exemple si PayTech vous notifie plus tard via cette
    # référence dans son webhook).
    reference = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reference} — {self.amount} FCFA ({self.status})"
