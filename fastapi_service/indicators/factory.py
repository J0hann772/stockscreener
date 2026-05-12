"""
Фабрика индикаторов (паттерн Factory).

Создаёт нужный класс индикатора по строковому имени.
"""
from typing import Any, Dict

from .base import BaseIndicator
from .rsi import RSIIndicator
from .ema import EMAIndicator
from .sma import SMAIndicator
from .macd import MACDIndicator
from .bollinger import BollingerBandsIndicator
from .atr import ATRIndicator
from .stochastic import StochasticIndicator
from .obv import OBVIndicator
from .cci import CCIIndicator
from .adx import ADXIndicator


class IndicatorFactory:
    """
    Фабрика для создания индикаторов по имени.

    Содержит реестр всех доступных индикаторов (REGISTRY).
    Создаёт нужный индикатор через метод create().
    """

    REGISTRY = {
        'rsi': RSIIndicator,
        'ema': EMAIndicator,
        'sma': SMAIndicator,
        'macd': MACDIndicator,
        'bb': BollingerBandsIndicator,
        'bollinger': BollingerBandsIndicator,
        'atr': ATRIndicator,
        'stoch': StochasticIndicator,
        'stochastic': StochasticIndicator,
        'obv': OBVIndicator,
        'cci': CCIIndicator,
        'adx': ADXIndicator,
    }

    @classmethod
    def create(cls, name: str, config: Dict[str, Any] = None) -> BaseIndicator:
        """
        Создаёт экземпляр индикатора по имени.

        Args:
            name (str): имя индикатора (ключ из REGISTRY, например 'rsi').
            config (dict, optional): параметры для индикатора.

        Returns:
            BaseIndicator: готовый экземпляр индикатора.

        Raises:
            ValueError: если индикатор с таким именем не найден.
        """
        name_lower = name.lower()
        if name_lower not in cls.REGISTRY:
            available = ', '.join(sorted(cls.REGISTRY.keys()))
            raise ValueError(f"Индикатор '{name}' не найден. Доступные: {available}")
        return cls.REGISTRY[name_lower](config or {})
