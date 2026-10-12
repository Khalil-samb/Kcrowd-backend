import uuid

from django.db import models


class AdminActivityLog(models.Model):
    TYPE_CHOICES = [
        ('new_event', 'Nouvel événement'),
        ('new_organizer', 'Nouvel organisateur'),
        ('account_suspended', 'Compte suspendu'),
        ('account_reactivated', 'Compte réactivé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    message = models.TextField()

    # SET_NULL partout ici : un journal d'activité doit garder son texte
    # même si la personne ou l'événement concerné a depuis été supprimé
    # — c'est un historique, il ne doit jamais disparaître avec son sujet.
    related_user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, blank=True, null=True)
    related_organizer = models.ForeignKey('accounts.Organizer', on_delete=models.SET_NULL, blank=True, null=True)
    related_event = models.ForeignKey('events.Event', on_delete=models.SET_NULL, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.type} — {self.created_at:%d/%m/%Y %H:%M}"