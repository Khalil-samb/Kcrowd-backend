# Même logique que pour l'OTP : un contrat (PaymentProvider) que toute
# implémentation de paiement doit respecter.

from abc import ABC, abstractmethod
from dataclasses import dataclass

# @dataclass est un raccourci Python pour créer une classe qui ne sert qu'à
# TRANSPORTER des données, sans logique compliquée. Sans ce raccourci, il
# faudrait écrire à la main un constructeur __init__ qui affecte chaque
# champ un par un. Avec @dataclass, Python le génère automatiquement à
# partir de la simple liste de champs ci-dessous.
#
# On l'utilise ici parce que le résultat d'un paiement a toujours la même
# forme (a-t-il réussi ? avec quelle référence ? pour quel montant ?),
# peu importe quel fournisseur (démo ou PayTech) a produit ce résultat.

@dataclass
class ResultatPaiement:
    success: bool
    reference: str
    montant: float


class PaymentProvider(ABC):

    @abstractmethod
    def initier_paiement(self, montant: float, methode: str, reference: str) -> ResultatPaiement:
        """
        Tente un paiement et retourne toujours un ResultatPaiement,
        que ça réussisse ou échoue (l'échec n'est pas une exception ici,
        c'est un résultat normal à gérer : success=False).
        """
        ...