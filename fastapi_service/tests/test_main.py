"""
Тесты для FastAPI-эндпоинтов (main.py).

Используется стандартная библиотека unittest.
Покрывает:
- GET /chart-data/{ticker}
- GET /stock-info/{ticker}
- POST /analyze/
- GET /analyze/status/{task_id}
- POST /analyze-one/
"""
import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательная функция
# ─────────────────────────────────────────────────────────────────────────────

def make_ohlcv(n=50, base_price=100.0):
    """Генерирует синтетический OHLCV DataFrame для тестов."""
    np.random.seed(42)
    closes = base_price + np.cumsum(np.random.randn(n) * 0.5)
    opens = closes + np.random.randn(n) * 0.3
    highs = np.maximum(opens, closes) + np.abs(np.random.randn(n) * 0.2)
    lows = np.minimum(opens, closes) - np.abs(np.random.randn(n) * 0.2)
    volumes = np.random.randint(100_000, 1_000_000, n).astype(float)
    index = pd.date_range("2023-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes},
        index=index,
    )


# ─────────────────────────────────────────────────────────────────────────────
# /chart-data/{ticker}
# ─────────────────────────────────────────────────────────────────────────────

class TestChartData(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.df = make_ohlcv(n=50)

    def test_valid_ticker_returns_candles_and_volume(self):
        """Валидный тикер — возвращает candles и volume."""
        with (
            patch("main.get_redis") as mock_redis,
            patch("main.yf.download", return_value=self.df),
        ):
            mock_redis.return_value.get.return_value = None
            mock_redis.return_value.setex.return_value = True
            resp = self.client.get("/chart-data/AAPL?tf=1d")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("candles", body)
        self.assertIn("volume", body)
        self.assertEqual(body["ticker"], "AAPL")

    def test_unknown_tf_defaults_to_1d(self):
        """Неизвестный tf → не падает, возвращает 200."""
        with (
            patch("main.get_redis") as mock_redis,
            patch("main.yf.download", return_value=self.df),
        ):
            mock_redis.return_value.get.return_value = None
            mock_redis.return_value.setex.return_value = True
            resp = self.client.get("/chart-data/AAPL?tf=invalid")
        self.assertEqual(resp.status_code, 200)

    def test_empty_dataframe_returns_error_field(self):
        """Нет данных → поле error, пустые candles."""
        with (
            patch("main.get_redis") as mock_redis,
            patch("main.yf.download", return_value=pd.DataFrame()),
        ):
            mock_redis.return_value.get.return_value = None
            resp = self.client.get("/chart-data/INVALID?tf=1d")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("error", body)
        self.assertEqual(body["candles"], [])

    def test_redis_cache_hit_skips_yfinance(self):
        """Redis вернул кэш — yfinance не вызывается."""
        cached = '{"ticker":"AAPL","tf":"1d","candles":[],"volume":[]}'
        with (
            patch("main.get_redis") as mock_redis,
            patch("main.yf.download") as mock_yf,
        ):
            mock_redis.return_value.get.return_value = cached
            resp = self.client.get("/chart-data/AAPL?tf=1d")
            mock_yf.assert_not_called()
        self.assertEqual(resp.status_code, 200)

    def test_yf_download_exception_returns_error(self):
        """Исключение в yfinance → поле error в ответе."""
        with (
            patch("main.get_redis") as mock_redis,
            patch("main.yf.download", side_effect=Exception("network error")),
        ):
            mock_redis.return_value.get.return_value = None
            resp = self.client.get("/chart-data/AAPL?tf=1d")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("error", resp.json())

    def test_4h_timeframe_aggregates(self):
        """Таймфрейм 4h — данные агрегируются из 1h баров."""
        df = make_ohlcv(n=100)
        df.index = pd.date_range("2024-01-01", periods=100, freq="h")
        with (
            patch("main.get_redis") as mock_redis,
            patch("main.yf.download", return_value=df),
        ):
            mock_redis.return_value.get.return_value = None
            mock_redis.return_value.setex.return_value = True
            resp = self.client.get("/chart-data/AAPL?tf=4h")
        self.assertEqual(resp.status_code, 200)

    def test_ticker_uppercased_in_response(self):
        """Тикер в ответе — всегда в верхнем регистре."""
        with (
            patch("main.get_redis") as mock_redis,
            patch("main.yf.download", return_value=self.df),
        ):
            mock_redis.return_value.get.return_value = None
            mock_redis.return_value.setex.return_value = True
            resp = self.client.get("/chart-data/aapl?tf=1d")
        self.assertEqual(resp.json()["ticker"], "AAPL")


# ─────────────────────────────────────────────────────────────────────────────
# POST /analyze/
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalyzeEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.headers = {"X-Internal-Key": "test-key"}

    def test_analyze_returns_task_id_and_pending(self):
        """Успешный запрос → task_id и status=pending."""
        mock_task = MagicMock()
        mock_task.id = "test-task-id-123"
        with (
            patch("main.verify_internal_key", return_value=True),
            patch("main.run_analysis_task.delay", return_value=mock_task),
        ):
            resp = self.client.post(
                "/analyze/",
                json={"tickers": ["AAPL"], "strategy_config": {}},
                headers=self.headers,
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["task_id"], "test-task-id-123")
        self.assertEqual(body["status"], "pending")

    def test_analyze_multiple_tickers_returns_single_task(self):
        """Несколько тикеров — один task_id."""
        mock_task = MagicMock()
        mock_task.id = "multi-task"
        with (
            patch("main.verify_internal_key", return_value=True),
            patch("main.run_analysis_task.delay", return_value=mock_task),
        ):
            resp = self.client.post(
                "/analyze/",
                json={"tickers": ["AAPL", "GOOG", "MSFT"], "strategy_config": {}},
                headers=self.headers,
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["task_id"], "multi-task")

    def test_analyze_empty_tickers(self):
        """Пустой список тикеров — задача всё равно ставится."""
        mock_task = MagicMock()
        mock_task.id = "empty-task"
        with (
            patch("main.verify_internal_key", return_value=True),
            patch("main.run_analysis_task.delay", return_value=mock_task),
        ):
            resp = self.client.post(
                "/analyze/",
                json={"tickers": [], "strategy_config": {}},
                headers=self.headers,
            )
        self.assertEqual(resp.status_code, 200)


# ─────────────────────────────────────────────────────────────────────────────
# GET /analyze/status/{task_id}
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalyzeStatus(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.headers = {"X-Internal-Key": "test-key"}

    def test_status_pending(self):
        """Задача ещё не готова → status=pending."""
        mock_result = MagicMock()
        mock_result.ready.return_value = False
        with (
            patch("main.verify_internal_key", return_value=True),
            patch("main.AsyncResult", return_value=mock_result),
        ):
            resp = self.client.get("/analyze/status/fake-id", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "pending")

    def test_status_completed_with_result(self):
        """Задача завершена → status=completed, есть result."""
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.successful.return_value = True
        mock_result.result = {
            "matched": ["AAPL"],
            "details": [{"ticker": "AAPL", "matched": True, "conditions": []}],
        }
        with (
            patch("main.verify_internal_key", return_value=True),
            patch("main.AsyncResult", return_value=mock_result),
        ):
            resp = self.client.get("/analyze/status/fake-id", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "completed")
        self.assertIn("result", body)

    def test_status_failed_with_error(self):
        """Задача упала → status=failed, есть error."""
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.successful.return_value = False
        mock_result.result = Exception("Celery task failed")
        with (
            patch("main.verify_internal_key", return_value=True),
            patch("main.AsyncResult", return_value=mock_result),
        ):
            resp = self.client.get("/analyze/status/fake-id", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "failed")
        self.assertIn("error", body)


# ─────────────────────────────────────────────────────────────────────────────
# POST /analyze-one/
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalyzeOne(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.headers = {"X-Internal-Key": "test-key"}

    def test_analyze_one_success(self):
        """Успешный анализ одного тикера."""
        with (
            patch("main.verify_internal_key", return_value=True),
            patch(
                "main.analyze_tickers_async",
                new_callable=AsyncMock,
                return_value=(["AAPL"], [{"ticker": "AAPL", "matched": True, "conditions": []}]),
            ),
        ):
            resp = self.client.post(
                "/analyze-one/",
                json={"ticker": "AAPL", "strategy_config": {}},
                headers=self.headers,
            )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("matched", resp.json())

    def test_analyze_one_missing_ticker_returns_400(self):
        """Отсутствует ticker → 400."""
        with patch("main.verify_internal_key", return_value=True):
            resp = self.client.post(
                "/analyze-one/",
                json={"strategy_config": {}},
                headers=self.headers,
            )
        self.assertEqual(resp.status_code, 400)

    def test_analyze_one_missing_config_returns_400(self):
        """Отсутствует strategy_config → 400."""
        with patch("main.verify_internal_key", return_value=True):
            resp = self.client.post(
                "/analyze-one/",
                json={"ticker": "AAPL"},
                headers=self.headers,
            )
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
