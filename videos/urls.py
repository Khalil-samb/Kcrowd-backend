from django.urls import path

from .views import (AimerView, CompterVueView, FilVideosView, MaVideoView, MesVideosView,
                    ModerationVideoView, VideoStreamView)

urlpatterns = [
    path('', FilVideosView.as_view(), name='video-fil'),
    path('mine/', MesVideosView.as_view(), name='video-mes'),
    path('mine/<uuid:pk>/', MaVideoView.as_view(), name='video-ma'),
    path('admin/<uuid:pk>/', ModerationVideoView.as_view(), name='video-moderation'),
    path('<uuid:pk>/stream/', VideoStreamView.as_view(), name='video-stream'),
    path('<uuid:pk>/view/', CompterVueView.as_view(), name='video-vue'),
    path('<uuid:pk>/like/', AimerView.as_view(), name='video-like'),
]
