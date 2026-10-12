# Implémentation ACTIVE pour l'instant : au lieu d'envoyer un vrai SMS,
# on affiche le code dans le terminal où tourne le serveur Django. Utile
# pour développer et tester sans dépendre d'un fournisseur SMS payant.

from .base import OtpSender

class ConsoleOtpSender(OtpSender):
    """
    Hérite de OtpSender, et fournit SA version de envoyer() — c'est ce
    qu'on appelle "implémenter l'interface". Le mot-clé Python ici est
    simplement l'héritage (class ConsoleOtpSender(OtpSender)), mais le
    fait que OtpSender soit une ABC garantit qu'on ne peut pas oublier
    d'écrire envoyer() ci-dessous.
    """

    def envoyer(self, telephone: str, code: str) -> None:
        print(f"[OTP] Code pour {telephone} : {code}")