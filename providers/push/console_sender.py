from .base import NotificationSender


class ConsoleNotificationSender(NotificationSender):
    def envoyer(self, user_id: str, titre: str, message: str) -> None:
        print(f"[PUSH] Pour l'utilisateur {user_id} — {titre} : {message}")