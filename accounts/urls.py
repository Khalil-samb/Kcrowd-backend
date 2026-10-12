from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import AdminLoginView, OrganizerLoginView, OrganizerMeView, OrganizerRegisterView, OtpRequestView, OtpVerifyView, AdminOrganizerListView, AdminOrganizerStatusView, AdminUserListView, AdminUserStatusView, UpdateMeView, WhoAmIView
from .profile_views import OrganizerChangePasswordView, OrganizerProfileView

urlpatterns = [
    path('otp/request/', OtpRequestView.as_view(), name='otp-request'),
    path('otp/verify/', OtpVerifyView.as_view(), name='otp-verify'),
    path('organizer/register/', OrganizerRegisterView.as_view(), name='organizer-register'),
    path('organizer/login/', OrganizerLoginView.as_view(), name='organizer-login'),
    path('admin/login/', AdminLoginView.as_view(), name='admin-login'),
    
    
    path('admin/users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('admin/users/<uuid:pk>/status/', AdminUserStatusView.as_view(), name='admin-user-status'),
    path('admin/organizers/', AdminOrganizerListView.as_view(), name='admin-organizer-list'),
    path('admin/organizers/<uuid:pk>/status/', AdminOrganizerStatusView.as_view(), name='admin-organizer-status'),
    
    
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('organizer/me/', OrganizerMeView.as_view(), name='organizer-me'),
        
    path('me/', UpdateMeView.as_view(), name='update-me'),
    
    path('organizer/profile/', OrganizerProfileView.as_view(), name='organizer-profile'),
    path('organizer/change-password/', OrganizerChangePasswordView.as_view(), name='organizer-change-password'),
    
    
    path('whoami/', WhoAmIView.as_view(), name='whoami'),
    
]