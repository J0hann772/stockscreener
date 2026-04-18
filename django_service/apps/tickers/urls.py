"""
URL-маршруты для приложения tickers.

Маршруты:
    - /             — список тикеров + добавление нового
    - /delete/<pk>/ — удаление тикера по ID
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.ticker_list, name='ticker_list'),
    path('delete/<int:pk>/', views.delete_ticker, name='delete_ticker'),
]