"""
Тесты для модуля schemas/analyze_engine.py.

Используется стандартная библиотека unittest.
"""
import asyncio
import math
import sys
import os
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

# Позволяем импортировать из корня fastapi_service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.analyze_engine import (
    MAX_CONDITIONS,
    MAX_OR_GROUPS,
    _check_condition,
    _compute_indicator_series,
    _evaluate_strategy,
    _indicator_cache_key,
    _parse_strategy_config,
    _series_tail_two,
    analyze_tickers_async,
)


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательная функция
# ─────────────────────────────────────────────────────────────────────────────

def make_ohlcv(n=200, base_price=100.0):
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
# _parse_strategy_config
# ─────────────────────────────────────────────────────────────────────────────

class TestParseStrategyConfig(unittest.TestCase):
    def test_new_format_full(self):
        cfg = {
            "required_conditions": [{"indicator": "rsi"}],
            "optional_groups": [{"group_id": 1, "conditions": []}],
        }
        req, grp = _parse_strategy_config(cfg)
        self.assertEqual(req, [{"indicator": "rsi"}])
        self.assertEqual(len(grp), 1)

    def test_new_format_only_required(self):
        cfg = {"required_conditions": [{"indicator": "ema"}]}
        req, grp = _parse_strategy_config(cfg)
        self.assertEqual(len(req), 1)
        self.assertEqual(grp, [])

    def test_new_format_only_optional(self):
        cfg = {"optional_groups": [{"group_id": 1, "conditions": []}]}
        req, grp = _parse_strategy_config(cfg)
        self.assertEqual(req, [])
        self.assertEqual(len(grp), 1)

    def test_legacy_conditions_list(self):
        cfg = {"conditions": [{"indicator": "rsi"}, {"indicator": "ema"}]}
        req, grp = _parse_strategy_config(cfg)
        self.assertEqual(len(req), 2)
        self.assertEqual(grp, [])

    def test_legacy_single_condition(self):
        cfg = {"indicator": "macd", "operator": ">", "value": 0}
        req, grp = _parse_strategy_config(cfg)
        self.assertEqual(len(req), 1)
        self.assertEqual(grp, [])

    def test_empty_config(self):
        req, grp = _parse_strategy_config({})
        self.assertEqual(req, [])
        self.assertEqual(grp, [])

    def test_none_config(self):
        req, grp = _parse_strategy_config(None)
        self.assertEqual(req, [])
        self.assertEqual(grp, [])

    def test_required_conditions_none_value(self):
        cfg = {"required_conditions": None, "optional_groups": None}
        req, grp = _parse_strategy_config(cfg)
        self.assertEqual(req, [])
        self.assertEqual(grp, [])


# ─────────────────────────────────────────────────────────────────────────────
# _indicator_cache_key
# ─────────────────────────────────────────────────────────────────────────────

class TestIndicatorCacheKey(unittest.TestCase):
    def test_no_params(self):
        self.assertEqual(_indicator_cache_key("rsi", {}), "rsi")

    def test_with_params(self):
        key = _indicator_cache_key("ema", {"length": 20})
        self.assertIn("ema", key)
        self.assertIn("20", key)

    def test_param_order_stable(self):
        k1 = _indicator_cache_key("sma", {"length": 50, "offset": 0})
        k2 = _indicator_cache_key("sma", {"offset": 0, "length": 50})
        self.assertEqual(k1, k2)

    def test_different_params_different_key(self):
        k1 = _indicator_cache_key("rsi", {"length": 14})
        k2 = _indicator_cache_key("rsi", {"length": 21})
        self.assertNotEqual(k1, k2)

    def test_strip_whitespace(self):
        self.assertEqual(_indicator_cache_key("  rsi  ", {}), "rsi")

    def test_none_params(self):
        self.assertEqual(_indicator_cache_key("rsi", None), "rsi")


# ─────────────────────────────────────────────────────────────────────────────
# _series_tail_two
# ─────────────────────────────────────────────────────────────────────────────

class TestSeriesTailTwo(unittest.TestCase):
    def test_normal_series(self):
        prev, last = _series_tail_two(pd.Series([1.0, 2.0, 3.0, 4.0, 5.0]))
        self.assertAlmostEqual(last, 5.0)
        self.assertAlmostEqual(prev, 4.0)

    def test_single_element(self):
        prev, last = _series_tail_two(pd.Series([42.0]))
        self.assertAlmostEqual(last, 42.0)
        self.assertIsNone(prev)

    def test_empty_series(self):
        prev, last = _series_tail_two(pd.Series([], dtype=float))
        self.assertIsNone(prev)
        self.assertIsNone(last)

    def test_nan_values_dropped(self):
        prev, last = _series_tail_two(pd.Series([float("nan"), 1.0, 2.0]))
        self.assertAlmostEqual(last, 2.0)
        self.assertAlmostEqual(prev, 1.0)

    def test_all_nan(self):
        prev, last = _series_tail_two(pd.Series([float("nan"), float("nan")]))
        self.assertIsNone(prev)
        self.assertIsNone(last)

    def test_two_elements(self):
        prev, last = _series_tail_two(pd.Series([10.0, 20.0]))
        self.assertAlmostEqual(last, 20.0)
        self.assertAlmostEqual(prev, 10.0)


# ─────────────────────────────────────────────────────────────────────────────
# _compute_indicator_series
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeIndicatorSeries(unittest.TestCase):
    def setUp(self):
        self.df = make_ohlcv()

    def test_rsi_returns_series(self):
        series = _compute_indicator_series("rsi", self.df, {"length": 14})
        self.assertIsInstance(series, pd.Series)
        self.assertEqual(len(series), len(self.df))

    def test_ema_returns_series(self):
        series = _compute_indicator_series("ema", self.df, {"length": 20})
        self.assertIsInstance(series, pd.Series)

    def test_sma_returns_series(self):
        series = _compute_indicator_series("sma", self.df, {"length": 50})
        self.assertIsInstance(series, pd.Series)

    def test_macd_returns_series(self):
        series = _compute_indicator_series("macd", self.df, {})
        self.assertIsInstance(series, pd.Series)

    def test_unknown_indicator_raises(self):
        with self.assertRaises(ValueError):
            _compute_indicator_series("unknown_xyz", self.df, {})

    def test_rsi_values_in_range(self):
        series = _compute_indicator_series("rsi", self.df, {"length": 14})
        valid = series.dropna()
        self.assertTrue((valid >= 0).all())
        self.assertTrue((valid <= 100).all())

    def test_uppercase_columns_handled(self):
        series = _compute_indicator_series("rsi", self.df, {"length": 14})
        self.assertFalse(series.dropna().empty)


# ─────────────────────────────────────────────────────────────────────────────
# _check_condition
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckCondition(unittest.TestCase):
    def setUp(self):
        self.df = make_ohlcv()

    def test_rsi_less_than_passes(self):
        cond = {"indicator": "rsi", "operator": "<", "value": 80, "params": {"length": 14}}
        result = _check_condition(cond, self.df, {})
        self.assertIsInstance(result, bool)

    def test_rsi_less_than_fails(self):
        cond = {"indicator": "rsi", "operator": "<", "value": 0, "params": {"length": 14}}
        self.assertFalse(_check_condition(cond, self.df, {}))

    def test_rsi_greater_than_passes(self):
        cond = {"indicator": "rsi", "operator": ">", "value": 0, "params": {"length": 14}}
        self.assertTrue(_check_condition(cond, self.df, {}))

    def test_missing_indicator_returns_false(self):
        cond = {"indicator": "", "operator": "<", "value": 50, "params": {}}
        self.assertFalse(_check_condition(cond, self.df, {}))

    def test_missing_operator_returns_false(self):
        cond = {"indicator": "rsi", "operator": "", "value": 50, "params": {}}
        self.assertFalse(_check_condition(cond, self.df, {}))

    def test_invalid_value_returns_false(self):
        cond = {"indicator": "rsi", "operator": "<", "value": None, "params": {}}
        self.assertFalse(_check_condition(cond, self.df, {}))

    def test_cross_up_result_is_bool(self):
        cond = {
            "indicator": "ema", "operator": "cross_up",
            "compare_to_indicator": "sma", "compare_to_params": {"length": 50},
            "params": {"length": 20}, "value": None,
        }
        self.assertIsInstance(_check_condition(cond, self.df, {}), bool)

    def test_cross_down_result_is_bool(self):
        cond = {
            "indicator": "ema", "operator": "cross_down",
            "compare_to_indicator": "sma", "compare_to_params": {"length": 50},
            "params": {"length": 20}, "value": None,
        }
        self.assertIsInstance(_check_condition(cond, self.df, {}), bool)

    def test_equality_operator_false(self):
        cond = {"indicator": "rsi", "operator": "=", "value": -999.0, "params": {}}
        self.assertFalse(_check_condition(cond, self.df, {}))

    def test_cross_up_with_threshold_is_bool(self):
        cond = {"indicator": "rsi", "operator": "cross_up", "value": 50, "params": {}}
        self.assertIsInstance(_check_condition(cond, self.df, {}), bool)

    def test_cache_is_reused(self):
        cache = {}
        cond = {"indicator": "rsi", "operator": "<", "value": 80, "params": {"length": 14}}
        _check_condition(cond, self.df, cache)
        key_count_after_first = len(cache)
        _check_condition(cond, self.df, cache)
        self.assertEqual(len(cache), key_count_after_first)


# ─────────────────────────────────────────────────────────────────────────────
# _evaluate_strategy
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluateStrategy(unittest.TestCase):
    def setUp(self):
        self.df = make_ohlcv()

    def test_empty_strategy_matches(self):
        matched, details, err = _evaluate_strategy([], [], self.df)
        self.assertTrue(matched)
        self.assertEqual(details, [])
        self.assertIsNone(err)

    def test_single_must_passes(self):
        required = [{"indicator": "rsi", "operator": "<", "value": 100, "params": {"length": 14}, "name": "RSI<100"}]
        matched, details, err = _evaluate_strategy(required, [], self.df)
        self.assertTrue(matched)
        self.assertEqual(len(details), 1)
        self.assertEqual(details[0]["label"], "RSI<100")

    def test_single_must_fails(self):
        required = [{"indicator": "rsi", "operator": ">", "value": 999, "params": {"length": 14}, "name": "RSI>999"}]
        matched, _, _ = _evaluate_strategy(required, [], self.df)
        self.assertFalse(matched)

    def test_multiple_must_and_logic(self):
        required = [
            {"indicator": "rsi", "operator": "<", "value": 100, "params": {"length": 14}, "name": "R1"},
            {"indicator": "rsi", "operator": ">", "value": 999, "params": {"length": 14}, "name": "R2"},
        ]
        matched, _, _ = _evaluate_strategy(required, [], self.df)
        self.assertFalse(matched)

    def test_or_group_one_passes(self):
        groups = [{"group_id": 1, "conditions": [
            {"indicator": "rsi", "operator": ">", "value": 999, "params": {}, "name": "fail"},
            {"indicator": "rsi", "operator": "<", "value": 100, "params": {}, "name": "pass"},
        ]}]
        matched, _, _ = _evaluate_strategy([], groups, self.df)
        self.assertTrue(matched)

    def test_or_group_all_fail(self):
        groups = [{"group_id": 1, "conditions": [
            {"indicator": "rsi", "operator": ">", "value": 999, "params": {}, "name": "fail1"},
            {"indicator": "rsi", "operator": ">", "value": 998, "params": {}, "name": "fail2"},
        ]}]
        matched, _, _ = _evaluate_strategy([], groups, self.df)
        self.assertFalse(matched)

    def test_details_contain_group_type(self):
        required = [{"indicator": "rsi", "operator": "<", "value": 100, "params": {}, "name": "R"}]
        groups = [{"group_id": 1, "conditions": [
            {"indicator": "rsi", "operator": "<", "value": 100, "params": {}, "name": "O"}
        ]}]
        _, details, _ = _evaluate_strategy(required, groups, self.df)
        group_types = {d["group_type"] for d in details}
        self.assertIn("must", group_types)
        self.assertIn("or", group_types)

    def test_invalid_indicator_recorded_as_error(self):
        required = [{"indicator": "unknown_xyz", "operator": "<", "value": 50, "params": {}, "name": "BAD"}]
        matched, details, _ = _evaluate_strategy(required, [], self.df)
        self.assertFalse(matched)
        self.assertIsNotNone(details[0]["error"])

    def test_empty_or_group_skipped(self):
        groups = [{"group_id": 1, "conditions": []}]
        matched, _, _ = _evaluate_strategy([], groups, self.df)
        self.assertTrue(matched)


# ─────────────────────────────────────────────────────────────────────────────
# analyze_tickers_async (с mock yfinance)
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalyzeTickersAsync(unittest.TestCase):
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def _patch_fetch(self, df):
        return patch("schemas.analyze_engine._fetch_ohlc_sync", return_value=df)

    def test_empty_tickers(self):
        matched, results = self._run(analyze_tickers_async([], {}))
        self.assertEqual(matched, [])
        self.assertEqual(results, [])

    def test_ticker_passes_strategy(self):
        df = make_ohlcv()
        config = {
            "required_conditions": [
                {"indicator": "rsi", "operator": "<", "value": 100, "params": {"length": 14}, "name": "RSI<100"}
            ],
            "optional_groups": [],
        }
        with self._patch_fetch(df):
            matched, results = self._run(analyze_tickers_async(["AAPL"], config))
        self.assertIn("AAPL", matched)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["matched"])

    def test_ticker_fails_strategy(self):
        df = make_ohlcv()
        config = {
            "required_conditions": [
                {"indicator": "rsi", "operator": ">", "value": 999, "params": {"length": 14}, "name": "RSI>999"}
            ],
            "optional_groups": [],
        }
        with self._patch_fetch(df):
            matched, results = self._run(analyze_tickers_async(["TSLA"], config))
        self.assertEqual(matched, [])
        self.assertFalse(results[0]["matched"])

    def test_empty_dataframe_returns_no_data(self):
        config = {"required_conditions": [], "optional_groups": []}
        with self._patch_fetch(pd.DataFrame()):
            matched, results = self._run(analyze_tickers_async(["FAKE"], config))
        self.assertEqual(matched, [])
        self.assertEqual(results[0]["error"], "No data")

    def test_multiple_tickers(self):
        df = make_ohlcv()
        config = {
            "required_conditions": [
                {"indicator": "rsi", "operator": "<", "value": 100, "params": {}, "name": "R"}
            ],
            "optional_groups": [],
        }
        with self._patch_fetch(df):
            matched, results = self._run(analyze_tickers_async(["AAPL", "GOOG", "MSFT"], config))
        self.assertEqual(len(results), 3)
        self.assertEqual(len(matched), 3)

    def test_too_many_conditions_rejected(self):
        df = make_ohlcv()
        conditions = [
            {"indicator": "rsi", "operator": "<", "value": 100, "params": {}, "name": f"C{i}"}
            for i in range(MAX_CONDITIONS + 1)
        ]
        config = {"required_conditions": conditions, "optional_groups": []}
        with self._patch_fetch(df):
            matched, results = self._run(analyze_tickers_async(["X"], config))
        self.assertEqual(matched, [])
        self.assertIn("error", results[0])

    def test_too_many_or_groups_rejected(self):
        df = make_ohlcv()
        groups = [{"group_id": i, "conditions": []} for i in range(MAX_OR_GROUPS + 1)]
        config = {"required_conditions": [], "optional_groups": groups}
        with self._patch_fetch(df):
            matched, results = self._run(analyze_tickers_async(["X"], config))
        self.assertEqual(matched, [])
        self.assertIn("error", results[0])

    def test_empty_config_all_pass(self):
        df = make_ohlcv()
        with self._patch_fetch(df):
            matched, _ = self._run(analyze_tickers_async(["AAPL"], {}))
        self.assertIn("AAPL", matched)

    def test_results_contain_conditions_detail(self):
        df = make_ohlcv()
        config = {
            "required_conditions": [
                {"indicator": "rsi", "operator": "<", "value": 100, "params": {}, "name": "RSI"}
            ],
            "optional_groups": [],
        }
        with self._patch_fetch(df):
            _, results = self._run(analyze_tickers_async(["AAPL"], config))
        self.assertIn("conditions", results[0])
        self.assertEqual(len(results[0]["conditions"]), 1)


if __name__ == "__main__":
    unittest.main()
