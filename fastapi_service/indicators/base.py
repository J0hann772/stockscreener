"""
Базовый абстрактный класс для всех технических индикаторов.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict

import pandas as pd


class BaseIndicator(ABC):
    """
    Абстрактный базовый класс для всех индикаторов (паттерн Strategy).

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
        self.column_names = {}

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает индикатор и добавляет его в DataFrame.

        Args:
            df (pd.DataFrame): таблица с ценами (close, high, low, volume).

        Returns:
            pd.DataFrame: таблица с добавленными колонками индикатора.
        """

    @abstractmethod
    def last(self, df: pd.DataFrame) -> float:
        """
        Возвращает последнее значение индикатора.

        Args:
            df (pd.DataFrame): DataFrame с рассчитанным индикатором.

        Returns:
            float: последнее значение индикатора.
        """
