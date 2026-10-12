from django.urls import path

from .views import AcheterCampagneView, CampagneActiveView

urlpatterns = [
    path('events/<uuid:event_id>/active/', CampagneActiveView.as_view(), name='campagne-active'),
    path('events/<uuid:event_id>/purchase/', AcheterCampagneView.as_view(), name='campagne-purchase'),
]