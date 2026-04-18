"""
Настройки админ-панели для стратегий.

Регистрирует модели Strategy и StrategyCondition в Django Admin
с поиском, фильтрацией и inline-редактированием условий.
"""
from django.contrib import admin
from .models import Strategy, StrategyCondition


class StrategyConditionInline(admin.TabularInline):
    """Inline для редактирования условий прямо на странице стратегии."""
    model = StrategyCondition
    extra = 1


@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    """
    Админ-панель для стратегий.

    Показывает название, пользователя, статус и дату создания.
    Условия стратегии редактируются inline.
    """
    list_display = ('name', 'user', 'is_active', 'created_at')
    search_fields = ('name', 'user__username')
    list_filter = ('is_active', 'created_at')
    inlines = [StrategyConditionInline]


@admin.register(StrategyCondition)
class StrategyConditionAdmin(admin.ModelAdmin):
    """
    Админ-панель для условий стратегий.

    Показывает стратегию, индикатор, оператор и значение.
    """
    list_display = ('strategy', 'indicator', 'operator', 'value')
    search_fields = ('strategy__name', 'indicator')
    list_filter = ('indicator', 'operator')
