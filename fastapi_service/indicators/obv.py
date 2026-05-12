"""OBV — On-Balance Volume (Балансовый объём)."""
import pandas as pd
import pandas_ta as ta

from .base import BaseIndicator


class OBVIndicator(BaseIndicator):
    """
    OBV — кумулятивный объём: растёт когда цена растёт, падает когда падает.

    Config:
        offset (int): смещение (default: 0).
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает OBV и добавляет колонку OBV.

        Args:
            df (pd.DataFrame): таблица с колонками 'close' и 'volume'.

        Returns:
            pd.DataFrame: таблица с добавленной колонкой OBV.
        """
        offset = self.config.get('offset', 0)
        df['OBV'] = ta.obv(df['close'], df['volume'], offset=offset)
        self.column_names['main'] = 'OBV'
        return df

    def last(self, df: pd.DataFrame) -> float:
        """Возвращает последнее значение OBV."""
        return df[self.column_names.get('main', 'OBV')].iloc[-1]
