"""MACD — Moving Average Convergence Divergence."""
import pandas as pd
import pandas_ta as ta

from .base import BaseIndicator


class MACDIndicator(BaseIndicator):
    """
    MACD показывает разницу между быстрой и медленной EMA.

    Создаёт три колонки: MACD линия, сигнальная линия, гистограмма.

    Config:
        fast (int): быстрый период (default: 12).
        slow (int): медленный период (default: 26).
        signal (int): период сигнальной линии (default: 9).
        offset (int): смещение (default: 0).
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает MACD и добавляет три колонки в DataFrame.

        Args:
            df (pd.DataFrame): таблица с колонкой 'close'.

        Returns:
            pd.DataFrame: таблица с добавленными колонками MACD.
        """
        fast = self.config.get('fast', 12)
        slow = self.config.get('slow', 26)
        signal = self.config.get('signal', 9)
        offset = self.config.get('offset', 0)

        macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal, offset=offset)
        prefix = f'MACD_{fast}_{slow}_{signal}'

        df[prefix] = macd[f'MACD_{fast}_{slow}_{signal}']
        df[f'{prefix}_SIGNAL'] = macd[f'MACDs_{fast}_{slow}_{signal}']
        df[f'{prefix}_HIST'] = macd[f'MACDh_{fast}_{slow}_{signal}']

        self.column_names['main'] = prefix
        self.column_names['signal'] = f'{prefix}_SIGNAL'
        self.column_names['histogram'] = f'{prefix}_HIST'
        return df

    def last(self, df: pd.DataFrame) -> float:
        """Возвращает последнее значение MACD линии."""
        return df[self.column_names.get('main', 'MACD_12_26_9')].iloc[-1]
