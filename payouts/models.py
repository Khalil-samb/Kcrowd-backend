import uuid

from django.db import models


class Payout(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('completed', 'Terminé'),
        ('failed', 'Échoué'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizer = models.ForeignKey('accounts.Organizer', on_delete=models.CASCADE, related_name='payouts')
    amount = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20)
    destination_account = models.CharField(max_length=30)
    reference = models.CharField(max_length=100, unique=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.reference} — {self.amount} FCFA ({self.status})"
