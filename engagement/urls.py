from django.urls import path

from .views import (
    FavoriteListView,
    FavoriteToggleView,
    NotificationCountView,
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
)

urlpatterns = [
    path('favorites/', FavoriteListView.as_view(), name='favorite-list'),
    path('favorites/<uuid:event_id>/', FavoriteToggleView.as_view(), name='favorite-toggle'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/read-all/', NotificationMarkAllReadView.as_view(), name='notification-read-all'),
    path('notifications/<uuid:pk>/read/', NotificationMarkReadView.as_view(), name='notification-read'),
    path('notifications/count/', NotificationCountView.as_view(), name='notification-count'),
]