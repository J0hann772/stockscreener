"""
Форма для добавления тикера.
"""
from django import forms
from .models import Ticker


class TickerForm(forms.ModelForm):
    """
    Форма для добавления нового тикера.

    Содержит одно поле — symbol (символ тикера).
    При сохранении тикер автоматически переводится в верхний регистр.
    """

    class Meta:
        model = Ticker
        fields = ['symbol']

    def clean_symbol(self):
        """
        Приводит символ тикера к верхнему регистру.

        Returns:
            str: символ тикера в верхнем регистре (например, 'aapl' → 'AAPL').
        """
        return self.cleaned_data['symbol'].upper()
