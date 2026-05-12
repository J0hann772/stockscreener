"""SMA — Simple Moving Average (Простое скользящее среднее)."""
import pandas as pd
import pandas_ta as ta

from .base import BaseIndicator


class SMAIndicator(BaseIndicator):
    """
    SMA — среднее значение цены за указанный период.

    Config:
        length (int): период SMA (default: 20).
        offset (int): смещение (default: 0).
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает SMA и добавляет колонку SMA_{length}.

        Args:
            df (pd.DataFrame): таблица с колонкой 'close'.

        Returns:
            pd.DataFrame: таблица с добавленной колонкой SMA.
        """
        length = self.config.get('length', 20)
        offset = self.config.get('offset', 0)
        col_name = f'SMA_{length}'
        df[col_name] = ta.sma(df['close'], length=length, offset=offset)
        self.column_names['main'] = col_name
        return df

    def last(self, df: pd.DataFrame) -> float:
        """Возвращает последнее значение SMA."""
        return df[self.column_names.get('main', 'SMA_20')].iloc[-1]
