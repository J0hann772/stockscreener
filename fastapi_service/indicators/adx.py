"""ADX — Average Directional Index (Индекс направленного движения)."""
import pandas as pd
import pandas_ta as ta

from .base import BaseIndicator


class ADXIndicator(BaseIndicator):
    """
    ADX показывает силу тренда (не направление).

    Значения выше 25 — сильный тренд. Создаёт три колонки: ADX, DMP (+DI), DMN (-DI).

    Config:
        length (int): период ADX (default: 14).
        offset (int): смещение (default: 0).
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает ADX и добавляет колонки ADX, DMP и DMN.

        Args:
            df (pd.DataFrame): таблица с колонками 'high', 'low', 'close'.

        Returns:
            pd.DataFrame: таблица с добавленными колонками ADX.
        """
        length = self.config.get('length', 14)
        offset = self.config.get('offset', 0)

        adx = ta.adx(df['high'], df['low'], df['close'], length=length, offset=offset)
        prefix = f'ADX_{length}'

        df[prefix] = adx[f'ADX_{length}']
        df[f'{prefix}_DMP'] = adx[f'DMP_{length}']
        df[f'{prefix}_DMN'] = adx[f'DMN_{length}']

        self.column_names['main'] = prefix
        self.column_names['dmp'] = f'{prefix}_DMP'
        self.column_names['dmn'] = f'{prefix}_DMN'
        return df

    def last(self, df: pd.DataFrame) -> float:
        """Возвращает последнее значение ADX."""
        return df[self.column_names.get('main', 'ADX_14')].iloc[-1]
