# Ce fichier définit le CONTRAT que doit respecter tout "envoyeur d'OTP",
# peu importe comment il l'envoie réellement (console, SMS, WhatsApp...).

from abc import ABC, abstractmethod

# @abstractmethod force toute classe qui hérite de OtpSender à écrire
# obligatoirement sa propre version de la méthode envoyer(). Si on oublie,
# Python refuse de démarrer le programme — c'est une sécurité à l'exécution,
# pas juste une convention qu'on pourrait ignorer par erreur.

class OtpSender(ABC):

    @abstractmethod
    def envoyer(self, telephone: str, code: str) -> None:
        """
        Envoie le code OTP au numéro donné.
        Ne retourne rien : soit ça réussit silencieusement, soit ça lève
        une exception (erreur) que l'appelant devra gérer.
        """
        ...
        
        
        
#LE DOSSIER PROVIDE 
# pourquoi cette architecture ?" sur ce dossier providers/, 
# la réponse tient en une phrase : le code métier ne dépend jamais d'un fournisseur précis, 
# seulement d'un contrat — ce qui rend le système extensible sans modification du code existant 
# (principe ouvert/fermé, si vous voulez citer un vrai principe SOLID).