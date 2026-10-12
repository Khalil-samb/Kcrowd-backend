# Deux familles de vues ici :
# - Publiques (catalogue) : tout le monde peut lire, personne ne peut écrire
# - Organisateur (gestion) : réservées à IsOrganizer, chacun ne voit/modifie
#   que SES PROPRES événements


from datetime import timedelta

import uuid
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView, Response

from accounts.permissions import IsAdmin, IsOrganizer


from django.db import transaction
from django.db.models import Case, DateTimeField, F, IntegerField, Value, When
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404

from accounts.permissions import IsOrganizer
from .availability import recalculer_statut_complet
from .lifecycle import terminer_les_evenements_passes
from .models import Event, TicketType
from .serializers import (
    EventCreateSerializer,
    EventDetailSerializer,
    EventListSerializer,
    TicketTypeSerializer,
)


# POURQUOI generics.ListAPIView PLUTÔT QUE APIView ICI ?

# Pour accounts/views.py, chaque vue avait une vraie logique métier
# particulière (vérifier un OTP, comparer un mot de passe...), donc APIView
# (où on écrit tout à la main) avait du sens. Ici, "lister des événements
# avec des filtres" est un besoin tellement standard que DRF fournit une
# classe toute faite : generics.ListAPIView s'occupe de la pagination, du
# format de réponse, etc. On ne fournit que le queryset et le serializer.

class EventListView(generics.ListAPIView):
    serializer_class = EventListSerializer
    permission_classes = [AllowAny]  # accessible sans connexion, c'est le catalogue public

    def get_queryset(self):
        terminer_les_evenements_passes()  # met à jour les statuts avant de lire
        # get_queryset() (plutôt qu'un simple queryset = ... fixe) permet
        # de construire la liste dynamiquement à partir des paramètres
        # envoyés dans l'URL (?ville=...&categorie=...).
        # Le catalogue montre TOUS les événements (brouillons et annulés exceptés) : les terminés restent visibles pour que
        # l'accueil ne soit jamais vide, mais l'écran les grise (voir « sales_state »). Ordre : d'abord les événements à venir
        # (le plus proche en premier), puis les terminés (le plus récent en premier).
        maintenant = timezone.now()
        queryset = Event.objects.filter(status__in=['published', 'sold_out', 'finished']).annotate(
            termine=Case(When(end_date__lte=maintenant, then=Value(1)), When(status='finished', then=Value(1)), default=Value(0), output_field=IntegerField()),
            cle_a_venir=Case(When(termine=0, then=F('start_date')), default=Value(None, output_field=DateTimeField()), output_field=DateTimeField()),
        ).order_by('termine', '-is_sponsored', 'cle_a_venir', '-start_date')

        ville = self.request.query_params.get('ville')
        if ville:
            queryset = queryset.filter(city_id=ville)

        categorie = self.request.query_params.get('categorie')
        if categorie:
            queryset = queryset.filter(category_id=categorie)

        mot_cle = self.request.query_params.get('q')
        if mot_cle:
            # icontains = "contient, sans tenir compte des majuscules/minuscules"
            # Le | (pipe) sur des objets Q permet un OU logique entre deux
            # conditions (titre OU lieu contient le mot-clé).
            from django.db.models import Q
            queryset = queryset.filter(Q(title__icontains=mot_cle) | Q(venue__icontains=mot_cle))

        periode = self.request.query_params.get('date')
        if periode:
            queryset = self._filtrer_par_periode(queryset, periode)

        return queryset

    def _filtrer_par_periode(self, queryset, periode):
        """Même logique que côté Angular (SearchResultsComponent), reproduite ici."""
        maintenant = timezone.now()
        debut_aujourdhui = maintenant.replace(hour=0, minute=0, second=0, microsecond=0)

        if periode == 'today':
            fin = debut_aujourdhui + timedelta(days=1)
            return queryset.filter(start_date__gte=debut_aujourdhui, start_date__lt=fin)

        if periode == 'week':
            fin = debut_aujourdhui + timedelta(days=7)
            return queryset.filter(start_date__gte=debut_aujourdhui, start_date__lte=fin)

        if periode == 'month':
            fin = debut_aujourdhui + timedelta(days=30)
            return queryset.filter(start_date__gte=debut_aujourdhui, start_date__lte=fin)

        return queryset


class EventDetailView(generics.RetrieveAPIView):
    """GET /api/events/<id>/ — la fiche complète, avec billets et programme imbriqués."""
    queryset = Event.objects.all()
    serializer_class = EventDetailSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        terminer_les_evenements_passes()  # statut à jour avant lecture
        return super().get_object()

class EventTicketTypesView(generics.ListAPIView):
    """GET /api/events/<id>/ticket-types/ — utile si le frontend veut les
    recharger séparément sans re-télécharger toute la fiche événement."""
    serializer_class = TicketTypeSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # self.kwargs['event_id'] : la partie <event_id> de l'URL,
        # capturée automatiquement par Django (voir urls.py).
        return TicketType.objects.filter(event_id=self.kwargs['event_id'])


# Coté Organisateur

class OrganizerEventListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/organizers/me/events/  → liste SES événements
    POST /api/organizers/me/events/  → en crée un nouveau
    ListCreateAPIView combine les deux comportements en une seule classe.
    """
    permission_classes = [IsOrganizer]

    def get_serializer_class(self):
        # Un serializer différent pour la lecture (léger) et l'écriture
        # (tous les champs) — même vue, deux comportements selon la méthode.
        if self.request.method == 'POST':
            return EventCreateSerializer
        return EventDetailSerializer

    def get_queryset(self):
        terminer_les_evenements_passes()  # met à jour les statuts avant de lire
        # Ligne de sécurité essentielle : un organisateur ne voit QUE
        # ses propres événements, jamais ceux des autres, même s'il
        # connaissait leur identifiant.
        return Event.objects.filter(organizer=self.request.user.organizer)

    def perform_create(self, serializer):
        # perform_create() est appelée juste avant l'enregistrement en
        # base. On y injecte l'organisateur nous-mêmes, à partir de
        # l'utilisateur connecté — jamais depuis une donnée envoyée par
        # le client (qui pourrait tricher en indiquant un autre organizer_id).
        serializer.save(organizer=self.request.user.organizer)


class OrganizerEventDetailView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/organizers/me/events/<id>/
    Un organisateur ne peut consulter/modifier QUE ses propres événements.
    """
    serializer_class = EventCreateSerializer
    permission_classes = [IsOrganizer]

    def get_queryset(self):
        terminer_les_evenements_passes()  # met à jour les statuts avant de lire
        # Même principe que ci-dessus : si l'événement demandé n'appartient
        # pas à cet organisateur, get_queryset() ne le trouvera simplement
        # pas, et DRF renverra automatiquement une erreur 404 — sans qu'on
        # ait besoin d'écrire une vérification "si ce n'est pas à lui, refuse".
        return Event.objects.filter(organizer=self.request.user.organizer)

    def perform_update(self, serializer):
        # Enregistrer l'événement remet son statut « complet / en vente » en
        # accord avec le stock réel — ce qui corrige aussi un événement resté
        # bloqué en « Complet » alors qu'il reste des places.
        evenement = serializer.save()
        recalculer_statut_complet(evenement)


class OrganizerTicketTypeListCreateView(generics.ListCreateAPIView):
    """
    GET/POST /api/events/organizers/me/events/<event_id>/ticket-types/
    Même principe de sécurité que pour les portes d'accès : double
    filtre (événement + propriétaire), jamais l'un sans l'autre.
    """
    serializer_class = TicketTypeSerializer
    permission_classes = [IsOrganizer]

    def get_queryset(self):
        return TicketType.objects.filter(
            event_id=self.kwargs['event_id'],
            event__organizer=self.request.user.organizer,
        )

    def perform_create(self, serializer):
        event = get_object_or_404(Event, id=self.kwargs['event_id'], organizer=self.request.user.organizer)
        serializer.save(event=event)
        # Ajouter une catégorie avec des places rouvre un événement « Complet »
        recalculer_statut_complet(event)


class OrganizerTicketTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /api/events/organizers/me/events/<event_id>/ticket-types/<id>/

    Règles métier, garanties ICI (le frontend les affiche aussi, mais ne
    fait que prévenir : seul le serveur peut vraiment les faire respecter) :
    - la quantité totale ne peut jamais descendre sous le nombre déjà vendu ;
    - une catégorie qui a déjà des ventes ne peut pas être supprimée
      (les acheteurs perdraient la trace de leur billet).
    Le prix, lui, reste modifiable : il ne change que les achats futurs.
    """
    serializer_class = TicketTypeSerializer
    permission_classes = [IsOrganizer]

    def get_queryset(self):
        return TicketType.objects.filter(
            event_id=self.kwargs['event_id'],
            event__organizer=self.request.user.organizer,
        )

    def perform_update(self, serializer):
        # ⚠️ select_for_update(), comme dans l'achat de billets : sans ce
        # verrou, un achat qui arrive pile pendant la modification pourrait
        # être écrasé (instance.save() réécrit TOUTES les colonnes, y compris
        # quantity_sold lu un instant plus tôt) — des ventes disparaîtraient.
        with transaction.atomic():
            verrouille = TicketType.objects.select_for_update().get(pk=serializer.instance.pk)
            nouvelle_quantite = serializer.validated_data.get('quantity_total', verrouille.quantity_total)
            if nouvelle_quantite < verrouille.quantity_sold:
                raise ValidationError({
                    'quantity_total': f"La quantité totale ne peut pas être inférieure aux {verrouille.quantity_sold} billets déjà vendus."
                })
            serializer.instance = verrouille
            serializer.save()
            recalculer_statut_complet(verrouille.event)

    def perform_destroy(self, instance):
        with transaction.atomic():
            verrouille = TicketType.objects.select_for_update().get(pk=instance.pk)
            if verrouille.quantity_sold > 0:
                raise ValidationError({
                    'erreur': f"Impossible de supprimer « {verrouille.name} » : {verrouille.quantity_sold} billet(s) déjà vendu(s)."
                })
            evenement = verrouille.event
            verrouille.delete()
            recalculer_statut_complet(evenement)


class UploadImageView(APIView):
    """
    POST /api/events/upload-image/
    Corps attendu : un formulaire multipart avec un champ "image".
    Réservé aux organisateurs (affiches/bannières d'événement).
    """
    permission_classes = [IsOrganizer]
    parser_classes = [MultiPartParser, FormParser]

    FORMATS_AUTORISES = ['image/jpeg', 'image/png', 'image/webp']
    TAILLE_MAX = 5 * 1024 * 1024  # 5 Mo

    def post(self, request):
        fichier = request.FILES.get('image')

        if not fichier:
            return Response({'erreur': 'Aucun fichier envoyé.'}, status=status.HTTP_400_BAD_REQUEST)

        if fichier.content_type not in self.FORMATS_AUTORISES:
            return Response({'erreur': 'Format non supporté (JPEG, PNG ou WebP uniquement).'}, status=status.HTTP_400_BAD_REQUEST)

        if fichier.size > self.TAILLE_MAX:
            return Response({'erreur': 'Image trop volumineuse (5 Mo maximum).'}, status=status.HTTP_400_BAD_REQUEST)

        nom_fichier = f"{uuid.uuid4().hex}_{fichier.name}"
        chemin = default_storage.save(f'event-images/{nom_fichier}', ContentFile(fichier.read()))

        url = request.build_absolute_uri(default_storage.url(chemin))

        return Response({'url': url}, status=status.HTTP_201_CREATED)


class AdminAllEventsView(generics.ListAPIView):
    """
    GET /api/events/admin/all/
    Tous les événements, tous statuts confondus (brouillons compris), avec
    TOUS les champs — contrairement au catalogue public qui est allégé et
    ne montre que les événements publiés.
    """
    serializer_class = EventDetailSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        terminer_les_evenements_passes()
        return Event.objects.all()
