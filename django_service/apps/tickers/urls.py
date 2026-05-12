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
    path('bulk/', views.add_bulk_tickers, name='add_bulk_tickers'),
    path('stocks/', views.stocks_search, name='stocks_search'),
    path('stocks/<str:symbol>/', views.stock_detail, name='stock_detail'),
]