# Squelette pour PLUS TARD : le jour où vous branchez un vrai fournisseur
# SMS (Twilio, ou une passerelle sénégalaise), c'est ICI et SEULEMENT ici
# que le vrai code d'envoi sera écrit. Aucun autre fichier du projet n'a
# besoin de changer, puisque tout le reste ne connaît que le contrat
# OtpSender, pas cette classe précise.

from .base import OtpSender


class SmsOtpSender(OtpSender):
    def envoyer(self, telephone: str, code: str) -> None:
        # TODO : appel réel à l'API du fournisseur SMS choisi.
        # Exemple de structure attendue (à adapter selon le fournisseur) :
        #
        # response = requests.post(
        #     "https://api.fournisseur-sms.sn/send",
        #     json={"to": telephone, "message": f"Votre code Kcrowd : {code}"},
        #     headers={"Authorization": f"Bearer {API_KEY}"},
        # )
        # response.raise_for_status()
        raise NotImplementedError("Le fournisseur SMS réel n'est pas encore branché.")