from django.urls import path
from . import views

urlpatterns = [
    path('meetings/', views.meeting_list_create),
    path('meetings/<int:pk>/', views.meeting_detail),
    path('meetings/<int:pk>/transcript/', views.get_transcript),
    path('meetings/<int:pk>/chat/', views.chat),
]