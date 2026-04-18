"""
URL-маршруты для приложения strategies.

Маршруты:
    - /              — список стратегий пользователя
    - /new/          — создание новой стратегии
    - /delete/<pk>/  — удаление стратегии по ID
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.strategy_list, name='strategy_list'),
    path('new/', views.strategy_create, name='strategy_create'),
    path('delete/<int:pk>/', views.strategy_delete, name='strategy_delete'),
]