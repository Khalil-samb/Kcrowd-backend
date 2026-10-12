# LE SEUL FICHIER À MODIFIER quand vous voudrez brancher un vrai
# fournisseur SMS ou PayTech. Tout le reste du projet importe otp_sender
# et payment_provider DEPUIS ICI, jamais directement une classe précise.
#
# C'est le point central du patron Strategy : changer une seule ligne
# ici change le comportement de TOUTE l'application, sans toucher aux
# vues, aux modèles, ni à rien d'autre.


from providers.otp.console_sender import ConsoleOtpSender
from providers.payment.demo_provider import DemoPaymentProvider
from providers.push.console_sender import ConsoleNotificationSender

# ── Actif pour l'instant ──
otp_sender = ConsoleOtpSender()
payment_provider = DemoPaymentProvider()

# ── Le jour où vous basculez en réel, on remplace  les 2 lignes ci-dessus par : ──
#
# from providers.otp.sms_sender import SmsOtpSender
# from providers.payment.paytech_provider import PayTechPaymentProvider
#
# otp_sender = SmsOtpSender()
# payment_provider = PayTechPaymentProvider()

notification_sender = ConsoleNotificationSender()
# ── Plus tard, une fois Firebase en place ──
# from providers.push.firebase_sender import FirebaseNotificationSender
# notification_sender = FirebaseNotificationSender()