# Une fonction utilitaire, pensée pour être appelée depuis N'IMPORTE
# QUELLE autre app (tickets après un achat, events après une création...).
# Elle fait toujours les 2 mêmes choses ensemble : garder une trace en
# base ET déclencher l'envoi push — pour ne jamais oublier l'un des deux.

from config.providers_config import notification_sender
from .models import Notification


def creer_notification(user, type_notif: str, titre: str, message: str) -> Notification:
    notification = Notification.objects.create(user=user, type=type_notif, title=titre, message=message)

    # Ligne clé, même principe que pour l'OTP et le paiement : on ne sait
    # pas ici si notification_sender est la version console ou Firebase.
    notification_sender.envoyer(str(user.id), titre, message)

    return notification