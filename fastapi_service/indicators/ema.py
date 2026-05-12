"""EMA — Exponential Moving Average (Экспоненциальное скользящее среднее)."""
import pandas as pd
import pandas_ta as ta

from .base import BaseIndicator


class EMAIndicator(BaseIndicator):
    """
    EMA придаёт больший вес последним ценам, чем SMA.

    Config:
        length (int): период EMA (default: 20).
        offset (int): смещение (default: 0).
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает EMA и добавляет колонку EMA_{length}.

        Args:
            df (pd.DataFrame): таблица с колонкой 'close'.

        Returns:
            pd.DataFrame: таблица с добавленной колонкой EMA.
        """
        length = self.config.get('length', 20)
        offset = self.config.get('offset', 0)
        col_name = f'EMA_{length}'
        df[col_name] = ta.ema(df['close'], length=length, offset=offset)
        self.column_names['main'] = col_name
        return df

    def last(self, df: pd.DataFrame) -> float:
        """Возвращает последнее значение EMA."""
        return df[self.column_names.get('main', 'EMA_20')].iloc[-1]
