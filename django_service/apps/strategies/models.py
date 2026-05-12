"""
Модели для хранения торговых стратегий пользователей.

Содержит модель Strategy (стратегия) и StrategyCondition (условие стратегии).
Каждая стратегия принадлежит пользователю и может иметь несколько условий.
"""
from django.db import models
from django.contrib.auth.models import User


class Strategy(models.Model):
    """
    Торговая стратегия пользователя.

    Attributes:
        user (ForeignKey): пользователь-владелец стратегии.
        name (str): название стратегии.
        description (str): описание стратегии (необязательно).
        is_active (bool): активна ли стратегия.
        created_at (datetime): дата и время создания.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='strategies', verbose_name='Пользователь')
    name = models.CharField(max_length=100, verbose_name='Название стратегии')
    description = models.TextField(blank=True, verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Стратегия'
        verbose_name_plural = 'Стратегии'
        ordering = ['-created_at']

    def __str__(self):
        """Возвращает название стратегии и имя пользователя."""
        return f"{self.name} ({self.user.username})"

    def to_fastapi_config(self):
        """
        Формирует конфиг стратегии в формате, ожидаемом FastAPI.

        Returns:
            dict: словарь с required_conditions и optional_groups.
        """
        required = []
        groups = {}

        for cond in self.conditions.all():
            entry = {
                'name': cond.name,
                'indicator': cond.indicator,
                'params': cond.params or {},
                'operator': cond.operator,
                'value': cond.value,
                'compare_to_indicator': cond.compare_to_indicator or None,
                'compare_to_params': cond.compare_to_params or None,
            }
            if cond.is_required:
                required.append(entry)
            else:
                gid = cond.group_id or 0
                groups.setdefault(gid, []).append(entry)

        optional_groups = [
            {'group_id': gid, 'conditions': conds}
            for gid, conds in groups.items()
        ]

        return {
            'required_conditions': required,
            'optional_groups': optional_groups,
        }


class StrategyCondition(models.Model):
    """
    Условие торговой стратегии.

    Attributes:
        strategy (ForeignKey): стратегия.
        name (str): произвольное имя условия (необязательно).
        indicator (str): название индикатора ('rsi', 'ema', ...).
        params (dict): параметры индикатора в JSON.
        operator (str): оператор сравнения.
        value (float): пороговое значение (null при кросс-индикаторном сравнении).
        is_required (bool): True = MUST-условие (AND), False = входит в OR-группу.
        group_id (int): ID OR-группы (null если MUST).
        compare_to_indicator (str): имя второго индикатора для cross_up/cross_down.
        compare_to_params (dict): параметры второго индикатора.
    """
    OPERATOR_CHOICES = [
        ('>', 'Больше (>)'),
        ('<', 'Меньше (<)'),
        ('=', 'Равно (=)'),
        ('cross_up', 'Пересечение снизу вверх'),
        ('cross_down', 'Пересечение сверху вниз'),
    ]

    strategy = models.ForeignKey(
        Strategy, on_delete=models.CASCADE,
        related_name='conditions', verbose_name='Стратегия'
    )
    name = models.CharField(
        max_length=100, blank=True, verbose_name='Имя условия'
    )
    indicator = models.CharField(max_length=50, verbose_name='Индикатор')
    params = models.JSONField(default=dict, blank=True, verbose_name='Параметры индикатора')
    operator = models.CharField(max_length=20, choices=OPERATOR_CHOICES, verbose_name='Оператор')
    value = models.FloatField(verbose_name='Значение для сравнения', null=True, blank=True)

    # Группировка: MUST (AND) vs OR-группа
    is_required = models.BooleanField(
        default=True, verbose_name='Обязательное условие (MUST)'
    )
    group_id = models.IntegerField(
        null=True, blank=True, verbose_name='ID OR-группы'
    )

    # Кросс-индикаторное сравнение
    compare_to_indicator = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name='Сравнить с индикатором'
    )
    compare_to_params = models.JSONField(
        null=True, blank=True, verbose_name='Параметры второго индикатора'
    )

    class Meta:
        verbose_name = 'Условие стратегии'
        verbose_name_plural = 'Условия стратегии'
        ordering = ['group_id', 'id']

    def __str__(self):
        """Возвращает строку описания условия."""
        comp = f" vs {self.compare_to_indicator}" if self.compare_to_indicator else f" {self.value}"
        return f"{self.strategy.name} — {self.indicator} {self.operator}{comp}"
