"""ATR — Average True Range (Средний истинный диапазон)."""
import pandas as pd
import pandas_ta as ta

from .base import BaseIndicator


class ATRIndicator(BaseIndicator):
    """
    ATR показывает волатильность актива — средний размер свечи за период.

    Config:
        length (int): период ATR (default: 14).
        offset (int): смещение (default: 0).
        mamode (str): режим сглаживания (default: 'rma').
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает ATR и добавляет колонку ATR_{length}.

        Args:
            df (pd.DataFrame): таблица с колонками 'high', 'low', 'close'.

        Returns:
            pd.DataFrame: таблица с добавленной колонкой ATR.
        """
        length = self.config.get('length', 14)
        offset = self.config.get('offset', 0)
        mamode = self.config.get('mamode', 'rma')
        col_name = f'ATR_{length}'
        df[col_name] = ta.atr(
            df['high'], df['low'], df['close'],
            length=length, offset=offset, mamode=mamode
        )
        self.column_names['main'] = col_name
        return df

    def last(self, df: pd.DataFrame) -> float:
        """Возвращает последнее значение ATR."""
        return df[self.column_names.get('main', 'ATR_14')].iloc[-1]
