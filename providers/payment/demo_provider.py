# Implémentation ACTIVE pour l'instant : simule un paiement réaliste
# sans jamais toucher de vrai argent.
#
# En mode démonstration, les achats doivent rester stables pour valider le
# flux utilisateur complet. Le cas d'échec reste accessible via une variable
# d'environnement explicite, afin d'éviter d'obtenir un faux "paiement refusé"
# au hasard pendant les tests fonctionnels.

import os
import random
import time

from .base import PaymentProvider, ResultatPaiement


class DemoPaymentProvider(PaymentProvider):

    def initier_paiement(self, montant: float, methode: str, reference: str) -> ResultatPaiement:
        # On simule un vrai délai réseau (un vrai appel à Wave/Orange Money
        # prendrait, lui aussi, un peu de temps à répondre).
        time.sleep(1.5)

        # Par défaut, le mode démo doit être stable pour le développement.
        # Pour tester le chemin d'erreur, activer explicitement:
        # DEMO_PAYMENT_RANDOM_FAILURE=1
        simulate_failure = os.getenv('DEMO_PAYMENT_RANDOM_FAILURE', '').lower() in {'1', 'true', 'yes'}

        succes = True
        if simulate_failure:
            succes = random.random() < 0.9

        return ResultatPaiement(success=succes, reference=reference, montant=montant)