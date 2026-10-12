from django.utils import timezone
from rest_framework import serializers

from .date_validation import erreurs_dates_evenement
from .models import Event, EventScheduleItem, TicketType
from .publication import erreurs_changement_statut
from .sales_rules import etat_des_ventes


class TicketTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketType
        fields = ['id', 'name', 'description', 'perks', 'price', 'quantity_total', 'quantity_sold', 'is_active']
        # quantity_sold en lecture seule : ça ne doit JAMAIS être modifiable
        # directement depuis l'extérieur, seulement incrémenté par la
        # logique d'achat de billets.
        read_only_fields = ['quantity_sold']


class EventScheduleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventScheduleItem
        fields = ['id', 'time', 'title', 'description', 'image_url', 'order']


# QU'EST-CE QU'UN SerializerMethodField ?
# ------------------------------------------------------------------
# C'est un champ qui n'existe PAS dans la table de la base de données
# — il est calculé à la volée à chaque fois qu'on sérialise l'objet.
# Ici, "prix_min" n'est pas une colonne d'Event, mais quelque chose
# qu'on calcule en regardant ses TicketType liés. Le nom de la méthode
# doit être get_<nom_du_champ> (donc get_prix_min ci-dessous).

class EventListSerializer(serializers.ModelSerializer):
    """
    Utilisé pour la LISTE des événements (le catalogue) : volontairement
    léger, on n'a pas besoin du programme détaillé ni de la description
    complète juste pour afficher une carte événement.
    """
    prix_min = serializers.SerializerMethodField()
    # L'écran grise les événements qui ne sont plus achetables (terminés, clôturés...) au lieu de les cacher
    sales_state = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'category_id', 'city_id', 'venue',
            'start_date', 'end_date', 'cover_image_url', 'status', 'is_sponsored', 'prix_min', 'sales_state',
        ]

    def get_sales_state(self, event):
        return etat_des_ventes(event)

    def get_prix_min(self, event):
        # .aggregate(Min(...)) calcule le minimum directement en base de
        # données (efficace), plutôt que de charger tous les TicketType
        # en Python pour les comparer un par un.
        from django.db.models import Min
        resultat = event.ticket_types.filter(is_active=True).aggregate(Min('price'))
        return resultat['price__min']


class EventDetailSerializer(serializers.ModelSerializer):
    """
    Utilisé pour la fiche événement complète : contient tout, y compris
    les catégories de billets et le programme détaillé.
    """

    # SERIALIZER IMBRIQUÉ (nested serializer)
    # En mettant un autre serializer comme type de champ (au lieu d'un
    # simple CharField ou IntegerField), on inclut directement la liste
    # complète des objets liés dans la réponse JSON — le frontend reçoit
    # tout en un seul appel, pas besoin d'un deuxième appel séparé pour
    # récupérer les catégories de billets.
    #
    # many=True car un événement a PLUSIEURS TicketType.
    # read_only=True car on ne crée pas de TicketType via CET endpoint
    # (il y a un endpoint dédié dans tickets/ pour ça).
    ticket_types = TicketTypeSerializer(many=True, read_only=True)
    schedule_items = EventScheduleItemSerializer(many=True, read_only=True)
    sales_state = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = '__all__'

    def get_sales_state(self, event):
        return etat_des_ventes(event)


class EventCreateSerializer(serializers.ModelSerializer):
    """
    Utilisé quand un organisateur crée ou modifie son événement. Séparé
    du serializer de détail parce qu'ici on ATTEND des champs en entrée
    (écriture), alors que EventDetailSerializer sert à la LECTURE.
    """

    class Meta:
        model = Event
        exclude = ['organizer', 'created_at', 'average_rating', 'review_count']
        # organizer est exclu : on le déduira nous-mêmes de request.user
        # dans la vue (jamais faire confiance à un organizer_id envoyé
        # par le client, qui pourrait tricher en mettant l'id de
        # quelqu'un d'autre).

    def validate(self, attrs):
        # self.instance vaut None à la création, et l'événement existant en
        # modification. En modification partielle (PATCH), une date absente
        # de attrs est reprise de l'événement existant.
        instance = self.instance
        debut = attrs.get('start_date', getattr(instance, 'start_date', None))
        fin = attrs.get('end_date', getattr(instance, 'end_date', None))

        erreurs = erreurs_dates_evenement(
            debut=debut,
            fin=fin,
            debut_initial=getattr(instance, 'start_date', None),
            creation=instance is None,
        )
        if erreurs:
            raise serializers.ValidationError(erreurs)

        # Le statut est décidé par le SERVEUR (voir publication.py) : à la création, un
        # événement est toujours un brouillon (ses billets n'existent pas encore) ; ensuite,
        # seuls brouillon → publié (s'il est prêt) et publié → brouillon (sans vente) sont permis.
        # Clôture des ventes : une date NOUVELLE ou MODIFIÉE doit être à venir, et ne pas dépasser la fin de
        # l'événement. (Une clôture laissée telle quelle n'est pas revérifiée : un événement dont les ventes sont
        # légitimement closes doit pouvoir être modifié sans que cette date bloque tout.)
        cloture = attrs.get('sales_close_at', getattr(instance, 'sales_close_at', None))
        if cloture is not None and cloture != getattr(instance, 'sales_close_at', None):
            if cloture <= timezone.now():
                raise serializers.ValidationError({'sales_close_at': ["Cette date de clôture est déjà passée : les ventes seraient fermées dès maintenant. Choisissez une date à venir, ou laissez le champ vide."]})
            if fin is not None and cloture > fin:
                raise serializers.ValidationError({'sales_close_at': ["La clôture des ventes ne peut pas dépasser la fin de l'événement."]})

        statut = attrs.get('status')
        if instance is None:
            if statut not in (None, 'draft'):
                raise serializers.ValidationError({'status': ["Un événement se crée en brouillon : ajoutez ses billets, puis publiez-le."]})
        elif statut is not None:
            erreurs_statut = erreurs_changement_statut(instance, statut, debut, cloture)
            if erreurs_statut:
                raise serializers.ValidationError({'status': erreurs_statut})
        return attrs