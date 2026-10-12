import uuid

from django.db import models

from accounts.models import User
from events.models import Event, TicketType


class Ticket(models.Model):
    STATUS_CHOICES = [
        ('valid', 'Valide'),
        ('used', 'Utilisé'),
        ('cancelled', 'Annulé'),
    ]
    DISPUTE_CHOICES = [
        ('none', 'Aucun'),
        ('flagged', 'Signalé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ticket_type = models.ForeignKey(TicketType, on_delete=models.PROTECT, related_name='tickets')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tickets')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')

    # on_delete=PROTECT : même raisonnement que pour ticket_type — une
    # transaction déjà liée à un vrai billet payé ne doit jamais pouvoir
    # être supprimée silencieusement.
    transaction = models.ForeignKey('transactions.Transaction', on_delete=models.PROTECT, related_name='tickets')
        
    qr_code = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='valid')
    price = models.FloatField()
    purchase_date = models.DateTimeField(auto_now_add=True)
    scanned_at = models.DateTimeField(blank=True, null=True)
    
    # Si une porte ou un agent est supprimé après l'événement, on ne veut
    # ni supprimer le billet (CASCADE — on perdrait l'historique de vente),
    # ni bloquer la suppression (PROTECT — trop contraignant pour une
    # donnée aussi secondaire que "qui a scanné"). SET_NULL est le bon
    # compromis : le billet reste intact, seul le lien vers la porte/l'agent
    # disparaît (le champ redevient vide). C'est pour ça que blank=True,
    # null=True est obligatoire ici — sans ça, Django refuserait de
    # vider le champ.
    gate = models.ForeignKey(
        'access_control.AccessGate', on_delete=models.SET_NULL, blank=True, null=True, related_name='tickets'
    )
    scanned_by_agent = models.ForeignKey(
        'access_control.ScannerAgent', on_delete=models.SET_NULL, blank=True, null=True, related_name='tickets_scanned'
    )

    dispute_status = models.CharField(max_length=20, choices=DISPUTE_CHOICES, default='none')

    def __str__(self):
        return f"Billet {self.id} — {self.status}"