from rest_framework import serializers

from .models import TAUX_MAX, CommissionRateChange, PlatformSettings


def _nom(user):
    if user is None:
        return None
    return f"{user.first_name} {user.last_name or ''}".strip()


def serialiser_reglages(reglages, nb_historique=8):
    historique = CommissionRateChange.objects.select_related('changed_by')[:nb_historique]
    return {
        'commission_rate': float(reglages.commission_rate),
        'updated_at': reglages.updated_at,
        'updated_by_name': _nom(reglages.updated_by),
        'history': [
            {
                'old_rate': float(c.old_rate),
                'new_rate': float(c.new_rate),
                'changed_by_name': _nom(c.changed_by),
                'changed_at': c.changed_at,
            }
            for c in historique
        ],
    }


class ModifierReglagesSerializer(serializers.Serializer):
    commission_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, max_value=TAUX_MAX,
        error_messages={
            'invalid': 'Saisissez un nombre (ex. 5 ou 7,5).',
            'min_value': 'Le taux ne peut pas être négatif.',
            # « %% » : DRF formate ces messages avec l'opérateur %, un « % » seul ferait planter (erreur 500)
            'max_value': f'Le taux ne peut pas dépasser {TAUX_MAX} %%.',
            'max_decimal_places': "Deux décimales au maximum (ex. 7,25).",
            'max_digits': 'Valeur trop grande.',
            'max_whole_digits': 'Valeur trop grande.',
        },
    )
    # Jamais enregistré, jamais renvoyé : sert uniquement à confirmer l'identité.
    current_password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, trim_whitespace=False, max_length=128,
    )