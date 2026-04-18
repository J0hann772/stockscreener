"""
Модель тикера (акции), добавленного пользователем в свой список.
"""
from django.db import models
from django.contrib.auth.models import User


class Ticker(models.Model):
    """
    Тикер акции, привязанный к пользователю.

    Один пользователь не может добавить один и тот же тикер дважды
    (ограничение unique_together).

    Attributes:
        user (ForeignKey): пользователь-владелец.
        symbol (str): символ тикера (например, AAPL, TSLA).
        added_at (datetime): дата и время добавления.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickers', verbose_name='Пользователь')
    symbol = models.CharField(max_length=15, db_index=True, verbose_name='Тикер')
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    class Meta:
        verbose_name = 'Тикер'
        verbose_name_plural = 'Тикеры'
        unique_together = ('user', 'symbol')
        ordering = ['-added_at']

    def __str__(self):
        """Возвращает символ тикера и имя пользователя."""
        return f"{self.symbol} ({self.user.username})"
