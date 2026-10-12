# Squelette pour PLUS TARD : à remplir une fois Flutter en place et les
# jetons FCM (Firebase Cloud Messaging) des appareils enregistrés.

from .base import NotificationSender


class FirebaseNotificationSender(NotificationSender):
    def envoyer(self, user_id: str, titre: str, message: str) -> None:
        # TODO : récupérer le jeton FCM de l'appareil de cet utilisateur
        # (à stocker sur User ou dans une table dédiée le moment venu),
        # puis appeler l'API Firebase Cloud Messaging avec ce jeton.
        raise NotImplementedError("Firebase n'est pas encore branché.")