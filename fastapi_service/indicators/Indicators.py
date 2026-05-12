"""
Модуль технических индикаторов.

Содержит классы для расчёта RSI, EMA, SMA, MACD, Bollinger Bands,
ATR, Stochastic, OBV, CCI, ADX. Все индикаторы имеют единый интерфейс
через базовый класс BaseIndicator и создаются через IndicatorFactory.
"""
from abc import ABC, abstractmethod
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional, Union


class BaseIndicator(ABC):
    """Абстрактный базовый класс для всех индикаторов"""
    """
    Абстрактный базовый класс для всех индикаторов.

    Определяет общий интерфейс: calculate() для расчёта
    и last() для получения последнего значения.

    Attributes:
        config (dict): параметры индикатора (период, смещение и т.д.).
        column_names (dict): имена колонок, добавленных в DataFrame.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Инициализирует индикатор с конфигурацией.

        Args:
            config (dict, optional): параметры индикатора. По умолчанию пустой dict.
        """
        self.config = config or {}
        self.column_names = {}  # Для хранения имен созданных колонок

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает индикатор и добавляет его в DataFrame
        Рассчитывает индикатор и добавляет его в DataFrame.

        Args:
            df: DataFrame с ценами/объемами
            df (pd.DataFrame): таблица с ценами (close, high, low, volume).

        Returns:
            pd.DataFrame: таблица с добавленными колонками индикатора.
        """
        pass

    @abstractmethod
    def last(self, df: pd.DataFrame) -> float:
        """
        Возвращает последнее значение индикатора

        Args:
            df: DataFrame с рассчитанным индикатором

        Returns:
            Последнее значение индикатора
        """
        pass


class RSIIndicator(BaseIndicator):
    """
    Индекс относительной силы (Relative Strength Index).

    Показывает перекупленность (>70) или перепроданность (<30) актива.
    Индекс относительной силы (Relative Strength Index)

    Config:
        length: период расчета RSI (default: 14)
        scalar: множитель (default: 100)
        drift: период изменения (default: 1)
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает RSI и добавляет колонку RSI_{length} в DataFrame.

        Args:
            df (pd.DataFrame): таблица с колонкой 'close'.

        Returns:
            pd.DataFrame: таблица с добавленной колонкой RSI.
        """
        length = self.config.get('length', 14)
        scalar = self.config.get('scalar', 100)
        drift = self.config.get('drift', 1)

        rsi = ta.rsi(
            df['close'],
            length=length,
            scalar=scalar,
            drift=drift
        )

        col_name = f'RSI_{length}'
        df[col_name] = rsi
        self.column_names['main'] = col_name

        return df

    def last(self, df: pd.DataFrame) -> float:
        """
        Возвращает последнее значение RSI.

        Args:
            df (pd.DataFrame): таблица с рассчитанным RSI.

        Returns:
            float: последнее значение RSI.
        """
        col_name = self.column_names.get('main', 'RSI_14')
        return df[col_name].iloc[-1]


class EMAIndicator(BaseIndicator):
    """

    Config:
        length: период EMA (default: 20)
        offset: смещение (default: 0)
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает EMA и добавляет колонку EMA_{length} в DataFrame.

        Args:
            df (pd.DataFrame): таблица с колонкой 'close'.

        Returns:
            pd.DataFrame: таблица с добавленной колонкой EMA.
        """
        length = self.config.get('length', 20)
        offset = self.config.get('offset', 0)

        ema = ta.ema(
            df['close'],
            length=length,
            offset=offset
        )

        col_name = f'EMA_{length}'
        df[col_name] = ema
        self.column_names['main'] = col_name

        return df

    def last(self, df: pd.DataFrame) -> float:
        """
        Возвращает последнее значение EMA.

        Args:
            df (pd.DataFrame): таблица с рассчитанным EMA.

        Returns:
            float: последнее значение EMA.
        """
        col_name = self.column_names.get('main', 'EMA_20')
        return df[col_name].iloc[-1]


class SMAIndicator(BaseIndicator):
    """
    Простое скользящее среднее (Simple Moving Average).

    Среднее значение цены за указанный период.

    Config:
        length: период SMA (default: 20)
        offset: смещение (default: 0)
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает SMA и добавляет колонку SMA_{length} в DataFrame.

        Args:
            df (pd.DataFrame): таблица с колонкой 'close'.

        Returns:
            pd.DataFrame: таблица с добавленной колонкой SMA.
        """
        length = self.config.get('length', 20)
        offset = self.config.get('offset', 0)

        sma = ta.sma(
            df['close'],
            length=length,
            offset=offset
        )

        col_name = f'SMA_{length}'
        df[col_name] = sma
        self.column_names['main'] = col_name

        return df

    def last(self, df: pd.DataFrame) -> float:
        """
        Возвращает последнее значение SMA.

        Args:
            df (pd.DataFrame): таблица с рассчитанным SMA.

        Returns:
            float: последнее значение SMA.
        """
        col_name = self.column_names.get('main', 'SMA_20')
        return df[col_name].iloc[-1]


class MACDIndicator(BaseIndicator):
    """
    MACD (Moving Average Convergence Divergence).

    Показывает разницу между быстрой и медленной EMA.
    Создаёт три колонки: MACD линия, сигнальная линия и гистограмма.

    Config:
        fast: быстрый период (default: 12)
        slow: медленный период (default: 26)
        signal: период сигнальной линии (default: 9)
        offset: смещение (default: 0)
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает MACD и добавляет три колонки в DataFrame.

        Колонки: MACD_{fast}_{slow}_{signal},
        MACD_{...}_SIGNAL, MACD_{...}_HIST.

        Args:
            df (pd.DataFrame): таблица с колонкой 'close'.

        Returns:
            pd.DataFrame: таблица с добавленными колонками MACD.
        """
        fast = self.config.get('fast', 12)
        slow = self.config.get('slow', 26)
        signal = self.config.get('signal', 9)
        offset = self.config.get('offset', 0)

        macd = ta.macd(
            df['close'],
            fast=fast,
            slow=slow,
            signal=signal,
            offset=offset
        )

        # pandas-ta возвращает несколько колонок
        prefix = f'MACD_{fast}_{slow}_{signal}'
        df[f'{prefix}'] = macd[f'MACD_{fast}_{slow}_{signal}']
        df[f'{prefix}_SIGNAL'] = macd[f'MACDs_{fast}_{slow}_{signal}']
        df[f'{prefix}_HIST'] = macd[f'MACDh_{fast}_{slow}_{signal}']

        self.column_names['main'] = f'{prefix}'
        self.column_names['signal'] = f'{prefix}_SIGNAL'
        self.column_names['histogram'] = f'{prefix}_HIST'

        return df

    def last(self, df: pd.DataFrame) -> float:
        """
        Возвращает последнее значение MACD линии.

        Args:
            df (pd.DataFrame): таблица с рассчитанным MACD.

        Returns:
            float: последнее значение MACD.
        """
        col_name = self.column_names.get('main', 'MACD_12_26_9')
        return df[col_name].iloc[-1]


class BollingerBandsIndicator(BaseIndicator):
    """
    Полосы Боллинджера (Bollinger Bands).

    Показывает верхнюю, среднюю и нижнюю границы волатильности цены.
    Создаёт пять колонок: нижняя, средняя, верхняя полоса, ширина и процент.

    Config:
        length: период расчета (default: 20)
        std: количество стандартных отклонений (default: 2)
        offset: смещение (default: 0)
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает Bollinger Bands и добавляет 5 колонок в DataFrame.

        Колонки: BB_{length}_{std}_LOWER, _MIDDLE, _UPPER, _WIDTH, _PERCENT.

        Args:
            df (pd.DataFrame): таблица с колонкой 'close'.

        Returns:
            pd.DataFrame: таблица с добавленными колонками BB.
        """
        length = self.config.get('length', 20)
        std = self.config.get('std', 2)
        offset = self.config.get('offset', 0)

        bb = ta.bbands(
            df['close'],
            length=length,
            std=std,
            offset=offset
        )

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
        """
        Возвращает последнее значение средней полосы Боллинджера.

        Args:
            df (pd.DataFrame): таблица с рассчитанными BB.

        Returns:
            float: последнее значение средней полосы.
        """
        # Возвращаем последнее значение средней линии
        col_name = self.column_names.get('middle', 'BB_20_2_MIDDLE')
        return df[col_name].iloc[-1]


class ATRIndicator(BaseIndicator):
    """
    Средний истинный диапазон (Average True Range).

    Показывает волатильность актива — средний размер свечи за период.

    Config:
        length: период ATR (default: 14)
        offset: смещение (default: 0)
        mamode: режим сглаживания (default: 'rma')
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает ATR и добавляет колонку ATR_{length} в DataFrame.

        Args:
            df (pd.DataFrame): таблица с колонками 'high', 'low', 'close'.

        Returns:
            pd.DataFrame: таблица с добавленной колонкой ATR.
        """
        length = self.config.get('length', 14)
        offset = self.config.get('offset', 0)
        mamode = self.config.get('mamode', 'rma')

        atr = ta.atr(
            df['high'],
            df['low'],
            df['close'],
            length=length,
            offset=offset,
            mamode=mamode
        )

        col_name = f'ATR_{length}'
        df[col_name] = atr
        self.column_names['main'] = col_name

        return df

    def last(self, df: pd.DataFrame) -> float:
        """
        Возвращает последнее значение ATR.

        Args:
            df (pd.DataFrame): таблица с рассчитанным ATR.

        Returns:
            float: последнее значение ATR.
        """
        col_name = self.column_names.get('main', 'ATR_14')
        return df[col_name].iloc[-1]


class StochasticIndicator(BaseIndicator):
    """
    Стохастический осциллятор (Stochastic Oscillator).

    Показывает положение цены относительно диапазона High-Low.
    Создаёт две колонки: %K (быстрая) и %D (медленная).

    Config:
        k: период %K (default: 14)
        d: период %D (default: 3)
        smooth_k: сглаживание %K (default: 3)
        offset: смещение (default: 0)
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает Stochastic и добавляет колонки %K и %D в DataFrame.

        Args:
            df (pd.DataFrame): таблица с колонками 'high', 'low', 'close'.

        Returns:
            pd.DataFrame: таблица с добавленными колонками STOCH_K и STOCH_D.
        """
        k = self.config.get('k', 14)
        d = self.config.get('d', 3)
        smooth_k = self.config.get('smooth_k', 3)
        offset = self.config.get('offset', 0)

        stoch = ta.stoch(
            df['high'],
            df['low'],
            df['close'],
            k=k,
            d=d,
            smooth_k=smooth_k,
            offset=offset
        )

        prefix = f'STOCH_{k}_{d}_{smooth_k}'
        df[f'{prefix}_K'] = stoch[f'STOCHk_{k}_{d}_{smooth_k}']
        df[f'{prefix}_D'] = stoch[f'STOCHd_{k}_{d}_{smooth_k}']

        self.column_names['k'] = f'{prefix}_K'
        self.column_names['d'] = f'{prefix}_D'

        return df

    def last(self, df: pd.DataFrame) -> float:
        """
        Возвращает последнее значение %K.

        Args:
            df (pd.DataFrame): таблица с рассчитанным Stochastic.

        Returns:
            float: последнее значение %K.
        """
        # Возвращаем последнее значение %K
        col_name = self.column_names.get('k', 'STOCH_14_3_3_K')
        return df[col_name].iloc[-1]


class OBVIndicator(BaseIndicator):
    """
    Балансовый объём (On-Balance Volume).

    Показывает кумулятивный объём: растёт когда цена растёт,
    падает когда цена падает.

    Config:
        offset: смещение (default: 0)
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает OBV и добавляет колонку OBV в DataFrame.

        Args:
            df (pd.DataFrame): таблица с колонками 'close' и 'volume'.

        Returns:
            pd.DataFrame: таблица с добавленной колонкой OBV.
        """
        offset = self.config.get('offset', 0)

        obv = ta.obv(
            df['close'],
            df['volume'],
            offset=offset
        )

        col_name = 'OBV'
        df[col_name] = obv
        self.column_names['main'] = col_name

        return df

    def last(self, df: pd.DataFrame) -> float:
        """
        Возвращает последнее значение OBV.

        Args:
            df (pd.DataFrame): таблица с рассчитанным OBV.

        Returns:
            float: последнее значение OBV.
        """
        col_name = self.column_names.get('main', 'OBV')
        return df[col_name].iloc[-1]


class CCIIndicator(BaseIndicator):
    """
    Индекс товарного канала (Commodity Channel Index).

    Измеряет отклонение цены от среднего. Значения выше +100
    говорят о перекупленности, ниже -100 — о перепроданности.

    Config:
        length: период CCI (default: 20)
        constant: константа (default: 0.015)
        offset: смещение (default: 0)
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает CCI и добавляет колонку CCI_{length} в DataFrame.

        Args:
            df (pd.DataFrame): таблица с колонками 'high', 'low', 'close'.

        Returns:
            pd.DataFrame: таблица с добавленной колонкой CCI.
        """
        length = self.config.get('length', 20)
        constant = self.config.get('constant', 0.015)
        offset = self.config.get('offset', 0)

        cci = ta.cci(
            df['high'],
            df['low'],
            df['close'],
            length=length,
            constant=constant,
            offset=offset
        )

        col_name = f'CCI_{length}'
        df[col_name] = cci
        self.column_names['main'] = col_name

        return df

    def last(self, df: pd.DataFrame) -> float:
        """
        Возвращает последнее значение CCI.

        Args:
            df (pd.DataFrame): таблица с рассчитанным CCI.

        Returns:
            float: последнее значение CCI.
        """
        col_name = self.column_names.get('main', 'CCI_20')
        return df[col_name].iloc[-1]


class ADXIndicator(BaseIndicator):
    """
    Индекс направленного движения (Average Directional Index).

    Показывает силу тренда (не направление). Значения выше 25
    говорят о сильном тренде. Создаёт три колонки: ADX, DMP (+DI), DMN (-DI).

    Config:
        length: период ADX (default: 14)
        offset: смещение (default: 0)
    """

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает ADX и добавляет колонки ADX, DMP и DMN в DataFrame.

        Args:
            df (pd.DataFrame): таблица с колонками 'high', 'low', 'close'.

        Returns:
            pd.DataFrame: таблица с добавленными колонками ADX.
        """
        length = self.config.get('length', 14)
        offset = self.config.get('offset', 0)

        adx = ta.adx(
            df['high'],
            df['low'],
            df['close'],
            length=length,
            offset=offset
        )

        prefix = f'ADX_{length}'
        df[f'{prefix}'] = adx[f'ADX_{length}']
        df[f'{prefix}_DMP'] = adx[f'DMP_{length}']
        df[f'{prefix}_DMN'] = adx[f'DMN_{length}']

        self.column_names['main'] = f'{prefix}'
        self.column_names['dmp'] = f'{prefix}_DMP'
        self.column_names['dmn'] = f'{prefix}_DMN'

        return df

    def last(self, df: pd.DataFrame) -> float:
        """
        Возвращает последнее значение ADX.

        Args:
            df (pd.DataFrame): таблица с рассчитанным ADX.

        Returns:
            float: последнее значение ADX.
        """
        col_name = self.column_names.get('main', 'ADX_14')
        return df[col_name].iloc[-1]


class IndicatorFactory:
    """
    Фабрика для создания индикаторов по имени.

    Содержит реестр всех доступных индикаторов.
    Создаёт нужный индикатор через метод create().
    """

    # Словарь доступных индикаторов: ключ → класс
    REGISTRY = {
        'rsi': RSIIndicator,
        'ema': EMAIndicator,
        'sma': SMAIndicator,
        'macd': MACDIndicator,
        'bb': BollingerBandsIndicator,
        'bollinger': BollingerBandsIndicator,  # алиас
        'atr': ATRIndicator,
        'stoch': StochasticIndicator,
        'stochastic': StochasticIndicator,  # алиас
        'obv': OBVIndicator,
        'cci': CCIIndicator,
        'adx': ADXIndicator,
    }

    @classmethod
    def create(cls, name: str, config: Dict[str, Any] = None) -> BaseIndicator:
        """
        Создает экземпляр индикатора по имени

        Args:
            name (str): имя индикатора (ключ из REGISTRY, например 'rsi', 'ema').
            config (dict, optional): параметры для индикатора.

        Returns:
            BaseIndicator: готовый экземпляр индикатора.

        Raises:
            ValueError: Если индикатор с таким именем не найден
        """
        name = name.lower()

        if name not in cls.REGISTRY:
            available = ', '.join(sorted(cls.REGISTRY.keys()))
            raise ValueError(f"Индикатор '{name}' не найден. Доступные: {available}")

        indicator_class = cls.REGISTRY[name]
        return indicator_class(config or {})