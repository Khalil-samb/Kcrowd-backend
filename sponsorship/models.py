# Une campagne de publicité vidéo sponsorisée, achetée directement par
# l'organisateur pour mettre en avant un de ses événements.
import uuid
from django.db import models


class SponsoredAd(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expirée'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizer = models.ForeignKey('accounts.Organizer', on_delete=models.CASCADE, related_name='sponsored_ads')
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='sponsored_ads')


    # ne jamais perdre la trace d'un paiement déjà effectué.
    transaction = models.ForeignKey('transactions.Transaction', on_delete=models.PROTECT, related_name='sponsored_ads')

    video_url = models.URLField(blank=True, null=True)
    package_name = models.CharField(max_length=100)
    price = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.package_name} — {self.event.title}"