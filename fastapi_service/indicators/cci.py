"""CCI — Commodity Channel Index (Индекс товарного канала)."""
import pandas as pd
import pandas_ta as ta

from .base import BaseIndicator


class CCIIndicator(BaseIndicator):
    """
    CCI измеряет отклонение цены от среднего.

    Значения выше +100 — перекупленность, ниже -100 — перепроданность.

    Config:
        length (int): период CCI (default: 20).
        constant (float): константа (default: 0.015).
        offset (int): смещение (default: 0).
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает CCI и добавляет колонку CCI_{length}.

        Args:
            df (pd.DataFrame): таблица с колонками 'high', 'low', 'close'.

        Returns:
            pd.DataFrame: таблица с добавленной колонкой CCI.
        """
        length = self.config.get('length', 20)
        constant = self.config.get('constant', 0.015)
        offset = self.config.get('offset', 0)
        col_name = f'CCI_{length}'
        df[col_name] = ta.cci(
            df['high'], df['low'], df['close'],
            length=length, constant=constant, offset=offset
        )
        self.column_names['main'] = col_name
        return df

    def last(self, df: pd.DataFrame) -> float:
        """Возвращает последнее значение CCI."""
        return df[self.column_names.get('main', 'CCI_20')].iloc[-1]
