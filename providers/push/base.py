# Même principe que providers/otp/ et providers/payment/ : un contrat,
# plusieurs implémentations possibles.

from abc import ABC, abstractmethod


class NotificationSender(ABC):

    @abstractmethod
    def envoyer(self, user_id: str, titre: str, message: str) -> None:
        """Envoie une notification push à l'utilisateur donné."""
        ...