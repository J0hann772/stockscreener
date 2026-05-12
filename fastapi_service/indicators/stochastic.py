"""Stochastic — Стохастический осциллятор."""
import pandas as pd
import pandas_ta as ta

from .base import BaseIndicator


class StochasticIndicator(BaseIndicator):
    """
    Stochastic показывает положение цены относительно диапазона High-Low.

    Создаёт две колонки: %K (быстрая) и %D (медленная).

    Config:
        k (int): период %K (default: 14).
        d (int): период %D (default: 3).
        smooth_k (int): сглаживание %K (default: 3).
        offset (int): смещение (default: 0).
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает Stochastic и добавляет колонки %K и %D.

        Args:
            df (pd.DataFrame): таблица с колонками 'high', 'low', 'close'.

        Returns:
            pd.DataFrame: таблица с добавленными колонками STOCH_K и STOCH_D.
        """
        k = self.config.get('k', 14)
        d = self.config.get('d', 3)
        smooth_k = self.config.get('smooth_k', 3)
        offset = self.config.get('offset', 0)

        stoch = ta.stoch(df['high'], df['low'], df['close'], k=k, d=d, smooth_k=smooth_k, offset=offset)
        prefix = f'STOCH_{k}_{d}_{smooth_k}'

        df[f'{prefix}_K'] = stoch[f'STOCHk_{k}_{d}_{smooth_k}']
        df[f'{prefix}_D'] = stoch[f'STOCHd_{k}_{d}_{smooth_k}']

        self.column_names['k'] = f'{prefix}_K'
        self.column_names['d'] = f'{prefix}_D'
        return df

    def last(self, df: pd.DataFrame) -> float:
        """Возвращает последнее значение %K."""
        return df[self.column_names.get('k', 'STOCH_14_3_3_K')].iloc[-1]
