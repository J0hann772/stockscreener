"""
Модуль для работы с Redis кэшем.

Кэширует рыночные данные (DataFrame) в Redis с TTL,
чтобы не дёргать Yahoo Finance при каждом запросе.
"""
import pickle
from typing import Any, Optional

import redis


class RedisCache:
    """
    Кэш на основе Redis для хранения рыночных данных.

    Сериализует объекты Python через pickle и хранит их
    в Redis с автоматическим удалением по TTL (15 минут).

    Attributes:
        client (redis.Redis): клиент подключения к Redis.
        ttl (int): время жизни кэша в секундах (по умолчанию 900).
    """

    def __init__(self):
        """Создаёт подключение к Redis на стандартном порту."""
        self.client: redis.Redis = redis.Redis(
            host="redis",
            port=6379,
            db=0,
            decode_responses=False)
        self.ttl: int = 900

    def _make_key(self, ticker: str, period: str) -> str:
        """
        Формирует ключ для хранения данных в Redis.

        Args:
            ticker (str): тикер акции.
            period (str): период данных.

        Returns:
            str: ключ в формате "market:{ticker}:{period}".
        """

        return f"market:{ticker}:{period}"

    def get(self, ticker: str, period: str) -> Optional[Any]:
        """
        Получает объект из Redis по ключу.

        Args:
            ticker (str): тикер акции.
            period (str): период данных.

        Returns:
            object | None: десериализованный объект Python, либо None если ключ отсутствует.
        """

        key = self._make_key(ticker, period)
        cached = self.client.get(key)

        if cached is None:
            return None

        return pickle.loads(cached)

    def set(self, ticker: str, period: str, data: Any) -> None:
        """
        Сохраняет объект в Redis с TTL.

        Объект сериализуется через pickle и сохраняется с
        автоматическим удалением через self.ttl секунд.

        Args:
            ticker (str): тикер акции.
            period (str): период данных.
            data (object): объект Python для сохранения (обычно pd.DataFrame).
        """
        key = self._make_key(ticker, period)

        self.client.setex(key, self.ttl, pickle.dumps(data))
