"""RSI — Relative Strength Index (Индекс относительной силы)."""
import pandas as pd
import pandas_ta as ta

from .base import BaseIndicator


class RSIIndicator(BaseIndicator):
    """
    RSI показывает перекупленность (>70) или перепроданность (<30) актива.

    Config:
        length (int): период расчёта (default: 14).
        scalar (float): множитель (default: 100).
        drift (int): период изменения (default: 1).
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает RSI и добавляет колонку RSI_{length}.

        Args:
            df (pd.DataFrame): таблица с колонкой 'close'.

        Returns:
            pd.DataFrame: таблица с добавленной колонкой RSI.
        """
        length = self.config.get('length', 14)
        scalar = self.config.get('scalar', 100)
        drift = self.config.get('drift', 1)
        col_name = f'RSI_{length}'
        df[col_name] = ta.rsi(df['close'], length=length, scalar=scalar, drift=drift)
        self.column_names['main'] = col_name
        return df

    def last(self, df: pd.DataFrame) -> float:
        """Возвращает последнее значение RSI."""
        return df[self.column_names.get('main', 'RSI_14')].iloc[-1]
