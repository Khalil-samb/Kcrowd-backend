# Les portes d'accès physiques d'un événement, et les agents affectés à
# chacune pour scanner les billets le jour J.

import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models


class AccessGate(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='access_gates')
    
    name = models.CharField(max_length=50)
    label = models.CharField(max_length=150)
    allowed_ticket_type_ids = ArrayField(models.UUIDField(), default=list, blank=True)
    estimated_throughput_per_hour = models.PositiveIntegerField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return f"{self.name} — {self.label}"
    
    

class ScannerAgent(models.Model):
    ROLE_CHOICES = [
        ('operator', 'Opérateur Scanner'),
        ('supervisor', 'Superviseur Portique'),
        ('disputes_manager', 'Gestionnaire Litiges'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='scanner_agents')
    gate = models.ForeignKey(AccessGate, on_delete=models.CASCADE, related_name='agents')

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='operator')

    # Code à 4 chiffres, transmis par WhatsApp à l'agent pour qu'il
    # s'authentifie sur l'application Flutter dédiée (application séparée,
    # pas ce backend Django directement).
    pin_code = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"