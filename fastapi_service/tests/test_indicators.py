"""
Тесты для индикаторов технического анализа (indicators/).

Покрывает calculate() и last() для каждого индикатора:
ADX, ATR, Bollinger Bands, CCI, EMA, MACD, OBV, RSI, SMA, Stochastic.
"""
import sys
import os
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from indicators.factory import IndicatorFactory
from indicators.adx import ADXIndicator
from indicators.atr import ATRIndicator
from indicators.bollinger import BollingerBandsIndicator
from indicators.cci import CCIIndicator
from indicators.ema import EMAIndicator
from indicators.macd import MACDIndicator
from indicators.obv import OBVIndicator
from indicators.rsi import RSIIndicator
from indicators.sma import SMAIndicator
from indicators.stochastic import StochasticIndicator


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательная функция
# ─────────────────────────────────────────────────────────────────────────────

def make_ohlcv(n=100, base_price=100.0):
    """Генерирует синтетический OHLCV DataFrame (колонки в нижнем регистре)."""
    np.random.seed(0)
    closes = base_price + np.cumsum(np.random.randn(n) * 0.5)
    opens = closes + np.random.randn(n) * 0.3
    highs = np.maximum(opens, closes) + np.abs(np.random.randn(n) * 0.2)
    lows = np.minimum(opens, closes) - np.abs(np.random.randn(n) * 0.2)
    volumes = np.random.randint(100_000, 1_000_000, n).astype(float)
    index = pd.date_range("2023-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
        index=index,
    )


# ─────────────────────────────────────────────────────────────────────────────
# IndicatorFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestIndicatorFactory(unittest.TestCase):
    def test_create_rsi(self):
        ind = IndicatorFactory.create("rsi")
        self.assertIsInstance(ind, RSIIndicator)

    def test_create_ema(self):
        ind = IndicatorFactory.create("ema")
        self.assertIsInstance(ind, EMAIndicator)

    def test_create_sma(self):
        ind = IndicatorFactory.create("sma")
        self.assertIsInstance(ind, SMAIndicator)

    def test_create_macd(self):
        ind = IndicatorFactory.create("macd")
        self.assertIsInstance(ind, MACDIndicator)

    def test_create_bollinger(self):
        ind = IndicatorFactory.create("bollinger")
        self.assertIsInstance(ind, BollingerBandsIndicator)

    def test_create_bb_alias(self):
        ind = IndicatorFactory.create("bb")
        self.assertIsInstance(ind, BollingerBandsIndicator)

    def test_create_atr(self):
        ind = IndicatorFactory.create("atr")
        self.assertIsInstance(ind, ATRIndicator)

    def test_create_stoch(self):
        ind = IndicatorFactory.create("stoch")
        self.assertIsInstance(ind, StochasticIndicator)

    def test_create_stochastic_alias(self):
        ind = IndicatorFactory.create("stochastic")
        self.assertIsInstance(ind, StochasticIndicator)

    def test_create_obv(self):
        ind = IndicatorFactory.create("obv")
        self.assertIsInstance(ind, OBVIndicator)

    def test_create_cci(self):
        ind = IndicatorFactory.create("cci")
        self.assertIsInstance(ind, CCIIndicator)

    def test_create_adx(self):
        ind = IndicatorFactory.create("adx")
        self.assertIsInstance(ind, ADXIndicator)

    def test_unknown_raises_value_error(self):
        with self.assertRaises(ValueError):
            IndicatorFactory.create("unknown_xyz")

    def test_case_insensitive(self):
        ind = IndicatorFactory.create("RSI")
        self.assertIsInstance(ind, RSIIndicator)

    def test_config_passed_to_indicator(self):
        ind = IndicatorFactory.create("rsi", config={"length": 21})
        self.assertEqual(ind.config["length"], 21)


# ─────────────────────────────────────────────────────────────────────────────
# RSI
# ─────────────────────────────────────────────────────────────────────────────

class TestRSIIndicator(unittest.TestCase):
    def setUp(self):
        self.df = make_ohlcv()
        self.ind = RSIIndicator({"length": 14})

    def test_calculate_adds_column(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIn("RSI_14", result.columns)

    def test_values_in_range(self):
        result = self.ind.calculate(self.df.copy())
        valid = result["RSI_14"].dropna()
        self.assertTrue((valid >= 0).all())
        self.assertTrue((valid <= 100).all())

    def test_last_returns_float(self):
        result = self.ind.calculate(self.df.copy())
        val = self.ind.last(result)
        self.assertIsInstance(val, float)

    def test_custom_period(self):
        ind = RSIIndicator({"length": 21})
        result = ind.calculate(self.df.copy())
        self.assertIn("RSI_21", result.columns)

    def test_column_names_set(self):
        self.ind.calculate(self.df.copy())
        self.assertEqual(self.ind.column_names["main"], "RSI_14")


# ─────────────────────────────────────────────────────────────────────────────
# EMA
# ─────────────────────────────────────────────────────────────────────────────

class TestEMAIndicator(unittest.TestCase):
    def setUp(self):
        self.df = make_ohlcv()
        self.ind = EMAIndicator({"length": 20})

    def test_calculate_adds_column(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIn("EMA_20", result.columns)

    def test_last_is_float(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIsInstance(self.ind.last(result), float)

    def test_values_not_all_nan(self):
        result = self.ind.calculate(self.df.copy())
        self.assertFalse(result["EMA_20"].dropna().empty)


# ─────────────────────────────────────────────────────────────────────────────
# SMA
# ─────────────────────────────────────────────────────────────────────────────

class TestSMAIndicator(unittest.TestCase):
    def setUp(self):
        self.df = make_ohlcv()
        self.ind = SMAIndicator({"length": 50})

    def test_calculate_adds_column(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIn("SMA_50", result.columns)

    def test_last_is_float(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIsInstance(self.ind.last(result), float)

    def test_values_not_all_nan(self):
        result = self.ind.calculate(self.df.copy())
        self.assertFalse(result["SMA_50"].dropna().empty)


# ─────────────────────────────────────────────────────────────────────────────
# MACD
# ─────────────────────────────────────────────────────────────────────────────

class TestMACDIndicator(unittest.TestCase):
    def setUp(self):
        self.df = make_ohlcv()
        self.ind = MACDIndicator({})

    def test_calculate_adds_main_column(self):
        result = self.ind.calculate(self.df.copy())
        main_col = self.ind.column_names.get("main")
        self.assertIn(main_col, result.columns)

    def test_signal_and_hist_columns(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIn("signal", self.ind.column_names)
        self.assertIn("histogram", self.ind.column_names)

    def test_last_is_float(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIsInstance(self.ind.last(result), float)


# ─────────────────────────────────────────────────────────────────────────────
# ATR
# ─────────────────────────────────────────────────────────────────────────────

class TestATRIndicator(unittest.TestCase):
    def setUp(self):
        self.df = make_ohlcv()
        self.ind = ATRIndicator({"length": 14})

    def test_calculate_adds_column(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIn("ATR_14", result.columns)

    def test_values_positive(self):
        result = self.ind.calculate(self.df.copy())
        valid = result["ATR_14"].dropna()
        self.assertTrue((valid > 0).all())

    def test_last_is_float(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIsInstance(self.ind.last(result), float)

    def test_custom_mamode(self):
        ind = ATRIndicator({"length": 14, "mamode": "ema"})
        result = ind.calculate(self.df.copy())
        self.assertFalse(result["ATR_14"].dropna().empty)

    def test_column_names_set(self):
        self.ind.calculate(self.df.copy())
        self.assertEqual(self.ind.column_names["main"], "ATR_14")


# ─────────────────────────────────────────────────────────────────────────────
# ADX
# ─────────────────────────────────────────────────────────────────────────────

class TestADXIndicator(unittest.TestCase):
    def setUp(self):
        self.df = make_ohlcv()
        self.ind = ADXIndicator({"length": 14})

    def test_calculate_adds_adx_column(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIn("ADX_14", result.columns)

    def test_calculate_adds_dmp_dmn_columns(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIn("ADX_14_DMP", result.columns)
        self.assertIn("ADX_14_DMN", result.columns)

    def test_values_in_range(self):
        result = self.ind.calculate(self.df.copy())
        valid = result["ADX_14"].dropna()
        self.assertTrue((valid >= 0).all())
        self.assertTrue((valid <= 100).all())

    def test_last_is_float(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIsInstance(self.ind.last(result), float)

    def test_column_names_set(self):
        self.ind.calculate(self.df.copy())
        self.assertEqual(self.ind.column_names["main"], "ADX_14")
        self.assertIn("dmp", self.ind.column_names)
        self.assertIn("dmn", self.ind.column_names)


# ─────────────────────────────────────────────────────────────────────────────
# Bollinger Bands
# ─────────────────────────────────────────────────────────────────────────────

class TestBollingerBandsIndicator(unittest.TestCase):
    def setUp(self):
        self.df = make_ohlcv()
        self.ind = BollingerBandsIndicator({"length": 20, "std": 2})

    def test_calculate_adds_lower_upper(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIn("BB_20_2_LOWER", result.columns)
        self.assertIn("BB_20_2_UPPER", result.columns)

    def test_calculate_adds_middle(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIn("BB_20_2_MIDDLE", result.columns)

    def test_upper_above_lower(self):
        result = self.ind.calculate(self.df.copy())
        upper = result["BB_20_2_UPPER"].dropna()
        lower = result["BB_20_2_LOWER"].dropna()
        self.assertTrue((upper >= lower).all())

    def test_last_is_float(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIsInstance(self.ind.last(result), float)

    def test_column_names_set(self):
        self.ind.calculate(self.df.copy())
        self.assertIn("lower", self.ind.column_names)
        self.assertIn("upper", self.ind.column_names)
        self.assertIn("middle", self.ind.column_names)

    def test_width_and_percent_columns(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIn("BB_20_2_WIDTH", result.columns)
        self.assertIn("BB_20_2_PERCENT", result.columns)


# ─────────────────────────────────────────────────────────────────────────────
# CCI
# ─────────────────────────────────────────────────────────────────────────────

class TestCCIIndicator(unittest.TestCase):
    def setUp(self):
        self.df = make_ohlcv()
        self.ind = CCIIndicator({"length": 20})

    def test_calculate_adds_column(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIn("CCI_20", result.columns)

    def test_values_not_all_nan(self):
        result = self.ind.calculate(self.df.copy())
        self.assertFalse(result["CCI_20"].dropna().empty)

    def test_last_is_float(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIsInstance(self.ind.last(result), float)

    def test_custom_constant(self):
        ind = CCIIndicator({"length": 20, "constant": 0.015})
        result = ind.calculate(self.df.copy())
        self.assertFalse(result["CCI_20"].dropna().empty)

    def test_column_names_set(self):
        self.ind.calculate(self.df.copy())
        self.assertEqual(self.ind.column_names["main"], "CCI_20")


# ─────────────────────────────────────────────────────────────────────────────
# OBV
# ─────────────────────────────────────────────────────────────────────────────

class TestOBVIndicator(unittest.TestCase):
    def setUp(self):
        self.df = make_ohlcv()
        self.ind = OBVIndicator({})

    def test_calculate_adds_column(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIn("OBV", result.columns)

    def test_values_not_all_nan(self):
        result = self.ind.calculate(self.df.copy())
        self.assertFalse(result["OBV"].dropna().empty)

    def test_last_is_float(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIsInstance(self.ind.last(result), float)

    def test_column_names_set(self):
        self.ind.calculate(self.df.copy())
        self.assertEqual(self.ind.column_names["main"], "OBV")

    def test_with_offset(self):
        ind = OBVIndicator({"offset": 1})
        result = ind.calculate(self.df.copy())
        self.assertIn("OBV", result.columns)


# ─────────────────────────────────────────────────────────────────────────────
# Stochastic
# ─────────────────────────────────────────────────────────────────────────────

class TestStochasticIndicator(unittest.TestCase):
    def setUp(self):
        self.df = make_ohlcv()
        self.ind = StochasticIndicator({"k": 14, "d": 3, "smooth_k": 3})

    def test_calculate_adds_k_column(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIn("STOCH_14_3_3_K", result.columns)

    def test_calculate_adds_d_column(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIn("STOCH_14_3_3_D", result.columns)

    def test_k_values_in_range(self):
        result = self.ind.calculate(self.df.copy())
        valid = result["STOCH_14_3_3_K"].dropna()
        self.assertTrue((valid >= 0).all())
        self.assertTrue((valid <= 100).all())

    def test_last_is_float(self):
        result = self.ind.calculate(self.df.copy())
        self.assertIsInstance(self.ind.last(result), float)

    def test_column_names_k_and_d(self):
        self.ind.calculate(self.df.copy())
        self.assertIn("k", self.ind.column_names)
        self.assertIn("d", self.ind.column_names)

    def test_default_config(self):
        ind = StochasticIndicator({})
        result = ind.calculate(self.df.copy())
        self.assertIn("STOCH_14_3_3_K", result.columns)


if __name__ == "__main__":
    unittest.main()
