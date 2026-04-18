"""
Настройки админ-панели для тикеров.
"""
from django.contrib import admin
from .models import Ticker


@admin.register(Ticker)
class TickerAdmin(admin.ModelAdmin):
    """
    Админ-панель для тикеров.

    Показывает символ, пользователя и дату добавления.
    Поиск по символу и имени пользователя.
    """
    list_display = ('symbol', 'user', 'added_at')
    search_fields = ('symbol', 'user__username')
    list_filter = ('added_at',)
