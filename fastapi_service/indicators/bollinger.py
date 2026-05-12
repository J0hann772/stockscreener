"""Bollinger Bands — Полосы Боллинджера."""
import pandas as pd
import pandas_ta as ta

from .base import BaseIndicator


class BollingerBandsIndicator(BaseIndicator):
    """
    Bollinger Bands показывает верхнюю, среднюю и нижнюю границы волатильности.

    Создаёт пять колонок: нижняя, средняя, верхняя полоса, ширина, процент.

    Config:
        length (int): период расчёта (default: 20).
        std (float): стандартных отклонений (default: 2).
        offset (int): смещение (default: 0).
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает Bollinger Bands и добавляет 5 колонок.

        Args:
            df (pd.DataFrame): таблица с колонкой 'close'.

        Returns:
            pd.DataFrame: таблица с добавленными колонками BB.
        """
        length = self.config.get('length', 20)
        std = self.config.get('std', 2)
        offset = self.config.get('offset', 0)

        bb = ta.bbands(df['close'], length=length, std=std, offset=offset)
        prefix = f'BB_{length}_{std}'

        df[f'{prefix}_LOWER'] = bb[f'BBL_{length}_{std}.0']
        df[f'{prefix}_MIDDLE'] = bb[f'BBM_{length}_{std}.0']
        df[f'{prefix}_UPPER'] = bb[f'BBU_{length}_{std}.0']
        df[f'{prefix}_WIDTH'] = bb[f'BBW_{length}_{std}.0']
        df[f'{prefix}_PERCENT'] = bb[f'BBP_{length}_{std}.0']

        self.column_names['lower'] = f'{prefix}_LOWER'
        self.column_names['middle'] = f'{prefix}_MIDDLE'
        self.column_names['upper'] = f'{prefix}_UPPER'
        self.column_names['width'] = f'{prefix}_WIDTH'
        self.column_names['percent'] = f'{prefix}_PERCENT'
        return df

    def last(self, df: pd.DataFrame) -> float:
        """Возвращает последнее значение средней полосы Боллинджера."""
        return df[self.column_names.get('middle', 'BB_20_2_MIDDLE')].iloc[-1]
