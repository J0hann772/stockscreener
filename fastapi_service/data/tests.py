"""
Модуль тестов для DataFetcher и RedisCache.
Содержит unit-тесты с использованием unittest и моков.
"""
import unittest
import pickle
from unittest.mock import MagicMock, patch
import pandas as pd

from .cache import RedisCache
from .fetcher import DataFetcher


class TestDataFetcher(unittest.TestCase):
    """
    Тесты для DataFetcher.
    Проверяется поведение кэша и вызов yfinance.
    """
    def test_no_cache(self):
        """Проверяет, что при отсутствии данных в кэше вызывается yfinance."""
        cache = MagicMock()
        cache.get.return_value = None
        fake_df = pd.DataFrame({"Close": [1, 2, 3]})

        with patch("yfinance.download", return_value=fake_df) as mock_download:
            fetcher = DataFetcher(cache=cache)
            result = fetcher.fetch("AAPL", "12mo")
            cache.get.assert_called_once_with("AAPL", "12mo")
            cache.set.assert_called_once()
            mock_download.assert_called_once()
            pd.testing.assert_frame_equal(result, fake_df)

    def test_cache_exist(self):
        """Проверяет, что при наличии данных в кэше yfinance не вызывается."""
        cache = MagicMock()
        fake_df = pd.DataFrame({"Close": [1, 2, 3]})
        cache.get.return_value = fake_df

        with patch("yfinance.download") as mock_download:
            fetcher = DataFetcher(cache=cache)
            result = fetcher.fetch("AAPL", "12mo")
            cache.get.assert_called_once_with("AAPL", "12mo")
            mock_download.assert_not_called()
            pd.testing.assert_frame_equal(result, fake_df)

    def test_first_cache_second_yfinance(self):
        """Проверяет, что первый вызов -> yfinance, а второй -> Redis."""
        cache = MagicMock()
        fake_df = pd.DataFrame({"Close": [1, 2, 3]})
        cache.get.side_effect = [None, fake_df]

        with patch("yfinance.download", return_value=fake_df) as mock_download:
            fetcher = DataFetcher(cache=cache)
            result1 = fetcher.fetch("AAPL")
            result2 = fetcher.fetch("AAPL")
            self.assertEqual(mock_download.call_count, 1)
            pd.testing.assert_frame_equal(result1, result2)

    def test_empty_data_error(self):
        """Проверяет, что, если yfinance вернул пустой DataFrame, raise ValueError."""
        cache = MagicMock()
        cache.get.return_value = None
        empty_df = pd.DataFrame()

        with patch("yfinance.download", return_value=empty_df):
            fetcher = DataFetcher(cache=cache)
            with self.assertRaises(ValueError):
                fetcher.fetch("AAPL")


class TestRedisCache(unittest.TestCase):
    """
    Тесты для RedisCache.
    Проверяется get, set и поведение при отсутствии ключа.
    """

    def test_cache_get(self):
        """Проверка получения данных из Redis."""
        cache = RedisCache()
        fake_data = {"test": 123}
        serialized = pickle.dumps(fake_data)
        cache.client = MagicMock()
        cache.client.get.return_value = serialized
        result = cache.get("AAPL", "12mo")
        self.assertEqual(result, fake_data)

    def test_cache_get_none(self):
        """Проверяет, что, если ключа нет в Redis, возвращается None."""
        cache = RedisCache()
        cache.client = MagicMock()
        cache.client.get.return_value = None
        result = cache.get("AAPL", "12mo")
        self.assertIsNone(result)

    def test_cache_set(self):
        """Проверка сохранения данных в Redis."""
        cache = RedisCache()
        cache.client = MagicMock()
        data = {"test": 123}
        cache.set("AAPL", "12mo", data)
        cache.client.setex.assert_called_once()
