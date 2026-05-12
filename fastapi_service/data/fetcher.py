"""
Модуль для загрузки рыночных данных с Yahoo Finance.

Использует Redis-кэш для ускорения повторных запросов.
"""
import pandas as pd
import yfinance as yf

from .cache import RedisCache


class DataFetcher:
    """
    Загрузчик исторических котировок с Yahoo Finance.

    Сначала проверяет Redis-кэш. Если данных нет — скачивает
    через yfinance и сохраняет в кэш.

    Attributes:
        cache (RedisCache): экземпляр кэша Redis.
    """

    def __init__(self):
        self.cache: RedisCache = RedisCache()

    def fetch(self, ticker: str, period: str = "12mo") -> pd.DataFrame:
        """
        Загружает исторические данные для тикера.

        Сначала проверяет кэш Redis. Если данные есть — возвращает их.
        Если данных нет — скачивает через yfinance, сохраняет в кэш и возвращает.

        Args:
            ticker (str): тикер акции (например, "AAPL").
            period (str, optional): период загрузки данных (по умолчанию "12mo").

        Returns:
            pd.DataFrame: исторические котировки с колонками:
                    Open, High, Low, Close, Adj Close, Volume.

        Raises:
            ValueError: если данные не найдены для указанного тикера.
        """
        cached = self.cache.get(ticker, period)
        if cached is not None:
            return cached

        data = yf.download(
            ticker,
            period=period,
            interval="1d",
            progress=False)

        if data.empty:
            raise ValueError(f"No data for ticker {ticker}")

        self.cache.set(ticker, period, data)

        return data
