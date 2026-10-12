from django.urls import path

from .views import ActivityLogListView, AdminDashboardView

urlpatterns = [
    path('dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('log/', ActivityLogListView.as_view(), name='admin-activity-log'),
]