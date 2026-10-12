import uuid

from django.db import transaction as db_transaction
from django.db.models.functions import Cast
from django.db.models import CharField
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from engagement.services import creer_notification
from access_control.models import AccessGate
from accounts.permissions import IsAdmin, IsOrganizer
from config.providers_config import payment_provider
from events.availability import recalculer_statut_complet
from events.sales_rules import raison_de_refuser_la_vente
from events.models import TicketType
from platform_settings.services import enregistrer_commission
from transactions.models import Transaction
from .models import Ticket
from .serializers import AchatBilletSerializer, ScanBilletSerializer, TicketSerializer



class AcheterBilletView(APIView):
    """
    POST /api/tickets/purchase/
    L'endpoint le plus sensible du projet : de l'argent (simulé pour
    l'instant) change de main, et des billets bien réels sont créés.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AchatBilletSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data

       
        # POURQUOI transaction.atomic() ?

        # Ce bloc regroupe PLUSIEURS écritures en base (mise à jour du
        # stock, création de la Transaction, création des Ticket) en une
        # seule unité "tout ou rien". Si une erreur survient à N'IMPORTE
        # QUELLE étape à l'intérieur du bloc, TOUTES les écritures déjà
        # faites sont annulées automatiquement (rollback) — impossible de
        # se retrouver avec un stock décrémenté mais aucun billet créé,
        # par exemple.
        with db_transaction.atomic():

            # --------------------------------------------------------------
            # POURQUOI select_for_update() ?
            # --------------------------------------------------------------
            # Imaginez deux acheteurs qui cliquent "Acheter" à la même
            # milliseconde sur le tout dernier billet disponible. Sans
            # précaution, les deux requêtes pourraient lire "1 place
            # restante" EN MÊME TEMPS, et toutes les deux réussir — on
            # aurait vendu 2 billets pour 1 place. select_for_update()
            # verrouille cette ligne en base tant que la transaction
            # n'est pas terminée : la deuxième requête doit ATTENDRE que
            # la première ait fini avant de lire la ligne à son tour, et
            # verra alors le stock déjà mis à jour.
            type_billet = TicketType.objects.select_for_update().get(id=donnees['ticket_type_id'])

            # La vente est-elle PERMISE ? (statut de l'événement, dates, catégorie active, limite d'achat)
            # Refusé AVANT tout paiement : aucune transaction, aucun billet, aucun stock touché.
            raison = raison_de_refuser_la_vente(type_billet, donnees['quantite'])
            if raison:
                return Response({'erreur': raison}, status=status.HTTP_400_BAD_REQUEST)

            if type_billet.quantity_sold + donnees['quantite'] > type_billet.quantity_total:
                return Response({'erreur': 'Plus assez de places disponibles.'}, status=status.HTTP_400_BAD_REQUEST)

            montant_total = type_billet.price * donnees['quantite']
            reference = f"TXN-{uuid.uuid4().hex[:10].upper()}"

           
            # LE PATRON STRATEGY EN ACTION
           
            # Cette ligne ne sait pas si elle parle à DemoPaymentProvider
            # ou à PayTechPaymentProvider — elle connaît seulement le
            # contrat PaymentProvider. C'est exactement ce qu'on a préparé
            # dans providers/ : demain, quand PayTech sera activé, cette
            # ligne ne changera pas d'un caractère.
            resultat = payment_provider.initier_paiement(
                montant_total, donnees['payment_method'], reference
            )

            transaction = Transaction.objects.create(
                user=request.user,
                event=type_billet.event,
                type='ticket_purchase',
                amount=montant_total,
                payment_method=donnees['payment_method'],
                status='success' if resultat.success else 'failed',
                reference=reference,
            )

            # Fige le taux de commission en vigueur à CET instant : cette vente garde
            # pour toujours le taux de son jour, même si l'admin le modifie plus tard
            # (voir platform_settings/models.py).
            enregistrer_commission(transaction)

            if not resultat.success:
                # Le rollback de transaction.atomic() annule aussi la
                # création de la Transaction ci-dessus ? Non — on la
                # VEUT en base même en cas d'échec (garder une trace des
                # tentatives ratées). C'est pour ça qu'on ne lève pas
                # d'exception ici : on retourne juste une réponse d'échec,
                # sans annuler ce qui a déjà été écrit.
                return Response({'erreur': 'Le paiement a échoué.'}, status=status.HTTP_402_PAYMENT_REQUIRED)

            billets_crees = []
            for _ in range(donnees['quantite']):
                billet = Ticket.objects.create(
                    ticket_type=type_billet,
                    event=type_billet.event,
                    user=request.user,
                    transaction=transaction,
                    qr_code=f"QR-{uuid.uuid4().hex}",
                    price=type_billet.price,
                )
                billets_crees.append(billet)

            type_billet.quantity_sold += donnees['quantite']
            type_billet.save()
            recalculer_statut_complet(type_billet.event)
            
            # Notifie l'acheteur
            creer_notification(
                user=request.user,
                type_notif='payment_confirmation',
                titre='Paiement confirmé',
                message=f"Votre achat de {donnees['quantite']} billet(s) pour {type_billet.event.title} est confirmé.",
            )
            
            # Notifie l'organisateur — c'est lui qui a besoin de savoir qu'une vente
            # vient d'avoir lieu. Seulement s'il a gardé les alertes de vente activées
            # dans son profil (Paramètres → Notifications).
            if type_billet.event.organizer.receoit_alertes_vente:
                creer_notification(
                    user=type_billet.event.organizer.user,
                    type_notif='new_sale',
                    titre='Nouvelle vente',
                    message=f"{donnees['quantite']} billet(s) vendu(s) pour {type_billet.event.title} — {montant_total:,.0f} FCFA.",
                )



        return Response(
            {
                'billets': TicketSerializer(billets_crees, many=True).data,
                'reference': reference,
            },
            status=status.HTTP_201_CREATED,
        )


class MesBilletsView(generics.ListAPIView):
    """GET /api/users/me/tickets/ — tous les billets de la personne connectée."""
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Ticket.objects.filter(user=self.request.user).order_by('-purchase_date')


class ScannerBilletView(APIView):
    """
    POST /api/tickets/scan/
    Corps attendu : { "qr_code": "QR-..." } (scan caméra)
                 OU { "reference": "A1B2C3D4" } (saisie manuelle de secours,
                     les 8 derniers caractères de l'id du billet)
    """
    permission_classes = [IsOrganizer]

    def post(self, request):
        serializer = ScanBilletSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data

        billet = None

        if donnees.get('qr_code'):
            # Cas normal : la caméra a lu un QR Code, on cherche une
            # correspondance EXACTE sur ce texte.
            billet = Ticket.objects.filter(qr_code=donnees['qr_code']).first()

        elif donnees.get('reference'):
            # Cas de secours : recherche par les derniers caractères de
            # l'id. Comme l'id est un UUID (pas du texte par défaut en
            # base), Cast(...) le convertit temporairement en texte pour
            # pouvoir utiliser __iendswith (comparaison "se termine par",
            # insensible à la casse).
            # Le code de secours = exactement 8 caractères (les 8 derniers de l'identifiant du billet),
            # cherché UNIQUEMENT parmi les billets des événements de cet organisateur.
            reference = str(donnees['reference']).strip().replace('-', '')
            if len(reference) == 8:
                billet = (
                    Ticket.objects.annotate(id_texte=Cast('id', CharField()))
                    .filter(id_texte__iendswith=reference, event__organizer=request.user.organizer)
                    .first()
                )

        if not billet:
            return Response({'statut': 'invalide', 'message': 'Billet introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        if billet.event.organizer != request.user.organizer:
            return Response({'erreur': "Ce billet n'appartient pas à un de vos événements."}, status=status.HTTP_403_FORBIDDEN)

        if billet.status == 'used':
            return Response({'statut': 'doublon', 'message': 'Ce billet a déjà été scanné.'}, status=status.HTTP_200_OK)

        if billet.status == 'cancelled':
            return Response({'statut': 'invalide', 'message': 'Ce billet a été annulé.'}, status=status.HTTP_200_OK)

        billet.status = 'used'
        billet.scanned_at = timezone.now()
        gate_id = donnees.get('gate_id')
        if gate_id:
            billet.gate = AccessGate.objects.filter(id=gate_id).first()
        billet.save()

        return Response({'statut': 'valide', 'message': 'Entrée autorisée.', 'billet': TicketSerializer(billet).data})

class SignalerLitigeView(APIView):
    """POST /api/tickets/<id>/dispute/ — marque un billet comme litigieux."""
    permission_classes = [IsOrganizer]

    def post(self, request, pk):
        try:
            billet = Ticket.objects.get(id=pk)
        except Ticket.DoesNotExist:
            return Response({'erreur': 'Billet introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        if billet.event.organizer != request.user.organizer:
            return Response({'erreur': "Ce billet n'appartient pas à un de vos événements."}, status=status.HTTP_403_FORBIDDEN)

        billet.dispute_status = 'flagged'
        billet.save()

        return Response({'message': 'Billet signalé en litige.', 'billet': TicketSerializer(billet).data})
    
    
 
class OrganizerEventTicketsView(generics.ListAPIView):
    """GET /api/tickets/organizers/me/events/<event_id>/tickets/"""
    serializer_class = TicketSerializer
    permission_classes = [IsOrganizer]
 
    def get_queryset(self):
        return Ticket.objects.filter(
            event_id=self.kwargs['event_id'],
            event__organizer=self.request.user.organizer,
        )


class TicketDetailView(generics.RetrieveAPIView):
    """
    GET /api/tickets/<id>/
    L'acheteur consulte SON PROPRE billet (page de confirmation d'achat).
    """
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]
 
    def get_queryset(self):
        return Ticket.objects.filter(user=self.request.user)

class AdminAllTicketsView(generics.ListAPIView):
    """GET /api/tickets/admin/all/ — tous les billets de la plateforme."""
    serializer_class = TicketSerializer
    permission_classes = [IsAdmin]
    # select_related évite une requête SQL supplémentaire par billet
    # (TicketSerializer lit user et ticket_type pour buyer_name/ticket_type_name).
    queryset = Ticket.objects.select_related('user', 'ticket_type').all()