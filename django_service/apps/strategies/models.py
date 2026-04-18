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


class StrategyCondition(models.Model):
    """
    Условие торговой стратегии.

    Описывает одно правило: какой индикатор сравнивается
    с каким значением и каким оператором (больше, меньше, пересечение и т.д.).

    Attributes:
        strategy (ForeignKey): стратегия, к которой относится условие.
        indicator (str): название индикатора (например, 'rsi', 'ema').
        params (dict): параметры индикатора в формате JSON.
        operator (str): оператор сравнения (>, <, =, cross_up, cross_down).
        value (float): значение для сравнения (необязательно).
    """
    OPERATOR_CHOICES = [
        ('>', 'Больше (>)'),
        ('<', 'Меньше (<)'),
        ('=', 'Равно (=)'),
        ('cross_up', 'Пересечение снизу вверх'),
        ('cross_down', 'Пересечение сверху вниз'),
    ]

    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name='conditions', verbose_name='Стратегия')
    indicator = models.CharField(max_length=50, verbose_name='Индикатор')
    params = models.JSONField(default=dict, blank=True, verbose_name='Параметры индикатора')
    operator = models.CharField(max_length=20, choices=OPERATOR_CHOICES, verbose_name='Оператор')
    value = models.FloatField(verbose_name='Значение для сравнения', null=True, blank=True)

    class Meta:
        verbose_name = 'Условие стратегии'
        verbose_name_plural = 'Условия стратегии'

    def __str__(self):
        """Возвращает строку вида: 'Название стратегии - индикатор оператор значение'."""
        return f"{self.strategy.name} - {self.indicator} {self.operator} {self.value}"
