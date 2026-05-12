"""
Модель для хранения истории запусков анализа.
"""
from django.db import models
from django.contrib.auth.models import User

from apps.strategies.models import Strategy


class AnalysisRun(models.Model):
    """
    Запись одного запуска анализа пользователем.

    Attributes:
        user (ForeignKey): пользователь, запустивший анализ.
        strategy (ForeignKey): стратегия, по которой выполнялся анализ.
        strategy_name (str): имя стратегии на момент запуска (snapshot).
        created_at (datetime): дата и время запуска.
        tickers_analyzed (int): сколько тикеров было обработано.
        tickers_matched (int): сколько тикеров прошли стратегию.
        matched_tickers (list): JSON список прошедших тикеров.
        details (list): JSON-детали по каждому тикеру.
        error (str): сообщение об ошибке (если был сбой).
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='analysis_runs', verbose_name='Пользователь'
    )
    strategy = models.ForeignKey(
        Strategy, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='runs', verbose_name='Стратегия'
    )
    strategy_name = models.CharField(
        max_length=100, verbose_name='Название стратегии'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Дата запуска'
    )
    tickers_analyzed = models.IntegerField(default=0, verbose_name='Тикеров проверено')
    tickers_matched = models.IntegerField(default=0, verbose_name='Тикеров прошло')
    matched_tickers = models.JSONField(default=list, verbose_name='Прошедшие тикеры')
    details = models.JSONField(default=list, verbose_name='Подробности')
    error = models.TextField(blank=True, verbose_name='Ошибка')

    class Meta:
        verbose_name = 'Запуск анализа'
        verbose_name_plural = 'История анализов'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.strategy_name} ({self.created_at:%d.%m.%Y %H:%M})"
