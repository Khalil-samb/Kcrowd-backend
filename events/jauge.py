from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from .models import TicketType


def verifier_jauge(event, nouvelle_quantite, ancienne_quantite=0, exclure_pk=None):
    """Le total des quantites des categories ne peut jamais depasser la jauge
    de l'evenement. Une diminution n'augmente jamais le total : elle passe toujours."""
    if nouvelle_quantite <= ancienne_quantite:
        return
    autres = (
        TicketType.objects.filter(event=event)
        .exclude(pk=exclure_pk)
        .aggregate(total=Sum('quantity_total'))['total']
        or 0
    )
    reste = max(event.max_capacity - autres, 0)
    if nouvelle_quantite > reste:
        raise ValidationError({
            'quantity_total': (
                f"La jauge de l'événement est de {event.max_capacity} places : "
                f"il n'en reste que {reste} pour cette catégorie."
            )
        })
