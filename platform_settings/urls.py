from django.urls import path

from .views import ReglagesPublicsView, ReglagesView

urlpatterns = [
    path('', ReglagesView.as_view(), name='platform-settings'),
    path('public/', ReglagesPublicsView.as_view(), name='platform-settings-public'),
]