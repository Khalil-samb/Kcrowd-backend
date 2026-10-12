

from .base import PaymentProvider, ResultatPaiement


class PayTechPaymentProvider(PaymentProvider):

    def initier_paiement(self, montant: float, methode: str, reference: str) -> ResultatPaiement:
        # TODO, une fois le compte PayTech activé :
        # 1. Appeler l'API PayTech pour initier la transaction
        # 2. PayTech redirige l'acheteur vers sa page de paiement
        # 3. PayTech notifie ensuite votre serveur par webhook (IPN) du
        #    résultat réel — il faudra donc aussi un endpoint dédié qui
        #    reçoit ce webhook et vérifie sa signature avant de faire
        #    confiance au contenu (sécurité : n'importe qui pourrait sinon
        #    appeler ce endpoint en prétendant qu'un paiement a réussi).
        raise NotImplementedError("PayTech n'est pas encore activé sur ce compte.")