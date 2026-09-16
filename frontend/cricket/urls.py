"""
URL configuration for the cricket app.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('players/', views.players_list, name='players'),
    path('players/<int:player_id>/', views.player_detail, name='player_detail'),
    path('teams/', views.teams_page, name='teams'),
    path('teams/vs/', views.team_vs_team, name='team_vs_team'),
    path('venues/', views.venues_page, name='venues'),
    path('head-to-head/', views.head_to_head, name='head_to_head'),
    path('playing-xi/', views.playing_xi, name='playing_xi'),
    path('prediction/', views.prediction, name='prediction'),
]
