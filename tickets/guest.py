from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from .models import Ticket
from .serializers import AchatBilletSerializer, TicketSerializer
from .views import AcheterBilletView


class AchatInviteSerializer(AchatBilletSerializer):
    phone = serializers.CharField(max_length=20)
    first_name = serializers.CharField(max_length=100)


class AcheterBilletInviteView(AcheterBilletView):
    """Achat sans compte : utilisateur NON verifie lie au telephone,
    puis reutilisation de toute la logique de AcheterBilletView."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        s = AchatInviteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        phone = s.validated_data['phone'].strip()
        prenom = s.validated_data['first_name'].strip()

        user = User.objects.filter(phone=phone).first()
        if user is None:
            user = User.objects.create_user(phone=phone, first_name=prenom)
        elif user.phone_verified or str(getattr(user, 'status', '')).lower() == 'suspended':
            return Response(
                {'erreur': "Ce numéro a déjà un compte Kcrowd. Identifiez-vous pour acheter.",
                 'compteExistant': True},
                status=status.HTTP_409_CONFLICT,
            )

        request.user = user
        return super().post(request)


class TicketInviteView(APIView):
    """Lecture publique d'un billet achete sans compte,
    valable tant que le numero n'a jamais ete verifie."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, pk):
        ticket = (Ticket.objects.select_related('user', 'ticket_type', 'event')
                  .filter(pk=pk).first())
        if ticket is None or ticket.user.phone_verified:
            return Response({'detail': 'Billet introuvable.'}, status=404)
        return Response(TicketSerializer(ticket).data)
