"""
Движок анализа тикеров по условиям стратегий.

Поддерживает:
- Обязательные условия (ALL must pass — AND логика)
- OR-группы (хотя бы одно из группы — OR логика)
- Кросс-индикаторные условия (EMA пересекает SMA)
- Стандартные сравнения (RSI < 30, MACD > 0)

Лимиты:
- Максимум 15 условий в стратегии (совпадает с UI)
- Максимум 5 OR-групп (совпадает с UI)
- История загрузки: 2 года (при дневном таймфрейме ≈ 504 бара)
"""
import asyncio
import json
import math
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import pandas_ta as ta
import yfinance as yf


# ─────────────────────────────────────────────────────────────────────────────
# ОГРАНИЧЕНИЯ (зеркалируют UI-лимиты)
# ─────────────────────────────────────────────────────────────────────────────
MAX_CONDITIONS = 15
MAX_OR_GROUPS  = 5
HISTORY_PERIOD = "2y"        # 2 года — достаточно для SMA(200) и не бан Yahoo


# ─────────────────────────────────────────────────────────────────────────────
# НОРМАЛИЗАЦИЯ ВХОДНОГО ФОРМАТА
# ─────────────────────────────────────────────────────────────────────────────
def _parse_strategy_config(strategy_config: Dict[str, Any]) -> Tuple[List, List]:
    """
    Разбирает конфиг стратегии в два списка: обязательные условия и OR-группы.

    Поддерживает два формата:
    1. Новый: {"required_conditions": [...], "optional_groups": [...]}
    2. Старый (legacy): {"conditions": [...]} или просто список-условие

    Args:
        strategy_config (dict): конфиг стратегии из Django.

    Returns:
        Tuple[required_conditions, optional_groups]:
            - required_conditions: список условий, ALL должны выполниться (AND)
            - optional_groups: список групп, в каждой хотя бы одно (OR внутри, AND между)
    """
    if not strategy_config:
        return [], []

    # Новый формат
    if "required_conditions" in strategy_config or "optional_groups" in strategy_config:
        required = strategy_config.get("required_conditions") or []
        groups = strategy_config.get("optional_groups") or []
        return required, groups

    # Старый legacy-формат: flat список условий
    conditions = strategy_config.get("conditions")
    if isinstance(conditions, list):
        return conditions, []

    # Совсем старый: сам объект — одно условие
    if {"indicator", "operator"}.issubset(strategy_config.keys()):
        return [strategy_config], []

    return [], []


# ─────────────────────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ УТИЛИТЫ
# ─────────────────────────────────────────────────────────────────────────────
def _indicator_cache_key(indicator: str, params: Dict[str, Any]) -> str:
    """Формирует стабильный строковый ключ для кэша индикаторов."""
    indicator = (indicator or "").strip()
    if not params:
        return indicator
    params_json = json.dumps(params, sort_keys=True, separators=(",", ":"))
    return f"{indicator}:{params_json}"


def _series_tail_two(series: pd.Series) -> Tuple[Optional[float], Optional[float]]:
    """
    Возвращает предпоследнее и последнее значение серии.

    Args:
        series (pd.Series): числовая серия.

    Returns:
        Tuple[prev, last]: два последних значения (prev может быть None).
    """
    s = series.dropna()
    if s.empty:
        return None, None
    last = float(s.iloc[-1])
    prev = float(s.iloc[-2]) if len(s) >= 2 else None
    return prev, last


# ─────────────────────────────────────────────────────────────────────────────
# ВЫЧИСЛЕНИЕ ИНДИКАТОРА
# ─────────────────────────────────────────────────────────────────────────────
def _compute_indicator_series(
    indicator_name: str,
    df: pd.DataFrame,
    params: Dict[str, Any],
) -> pd.Series:
    """
    Вычисляет серию значений технического индикатора через IndicatorFactory.

    Args:
        indicator_name (str): имя индикатора ('rsi', 'ema', 'macd', ...).
        df (pd.DataFrame): OHLCV данные.
        params (dict): параметры индикатора.

    Returns:
        pd.Series: серия значений.

    Raises:
        ValueError: если индикатор неизвестен или вычисление провалилось.
    """
    from indicators.factory import IndicatorFactory

    try:
        # Создаем экземпляр индикатора через фабрику
        indicator = IndicatorFactory.create(indicator_name, config=params)
        
        # Индикаторы и pandas_ta обычно ожидают колонки в нижнем регистре (open, high, low, close, volume)
        df_calc = df.copy()
        
        # Мапим стандартные колонки, если они с большой буквы
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col in df_calc.columns and col.lower() not in df_calc.columns:
                df_calc[col.lower()] = df_calc[col]
        
        df_result = indicator.calculate(df_calc)
        
        # Получаем имя главной колонки (например, 'RSI_14' или 'MACD_12_26_9')
        main_col = indicator.column_names.get('main')
        if not main_col or main_col not in df_result.columns:
            raise ValueError(f"Indicator calculation failed, missing main column: {main_col}")
            
        return df_result[main_col]

    except Exception as e:
        raise ValueError(f"Failed to compute {indicator_name}: {e}") from e

# ─────────────────────────────────────────────────────────────────────────────
# ОЦЕНКА ОДНОГО УСЛОВИЯ
# ─────────────────────────────────────────────────────────────────────────────
def _check_condition(
    cond: Dict[str, Any],
    df: pd.DataFrame,
    series_cache: Dict[str, pd.Series],
) -> bool:
    """
    Проверяет выполнение одного условия стратегии.

    Поддерживает:
    - Стандартное: indicator op value (RSI < 30)
    - Кросс-индикаторное: indicator cross_up/down compare_to_indicator (EMA cross_up SMA)

    Args:
        cond (dict): условие стратегии.
        df (pd.DataFrame): OHLCV данные.
        series_cache (dict): кэш уже вычисленных серий.

    Returns:
        bool: True если условие выполняется.
    """
    indicator = (cond.get("indicator") or "").strip()
    operator  = (cond.get("operator")  or "").strip().lower()
    params    = cond.get("params") or {}

    if not indicator or not operator:
        return False

    key1 = _indicator_cache_key(indicator, params)
    if key1 not in series_cache:
        series_cache[key1] = _compute_indicator_series(indicator, df, params)
    series1 = series_cache[key1]
    prev1, last1 = _series_tail_two(series1)
    if last1 is None:
        return False

    # Кросс-индикаторное сравнение
    compare_to = (cond.get("compare_to_indicator") or "").strip()
    if compare_to and operator in ("cross_up", "cross_down"):
        compare_params = cond.get("compare_to_params") or {}
        key2 = _indicator_cache_key(compare_to, compare_params)
        if key2 not in series_cache:
            series_cache[key2] = _compute_indicator_series(compare_to, df, compare_params)
        series2 = series_cache[key2]
        prev2, last2 = _series_tail_two(series2)
        if last2 is None or prev1 is None or prev2 is None:
            return False
        if operator == "cross_up":
            return prev1 < prev2 and last1 > last2
        if operator == "cross_down":
            return prev1 > prev2 and last1 < last2
        return False

    # Стандартное сравнение с числом
    try:
        threshold = float(cond.get("value"))
    except (TypeError, ValueError):
        # value=None допустимо только для кросс-условий; здесь провал
        return False

    if operator == ">":
        return last1 > threshold
    if operator == "<":
        return last1 < threshold
    if operator == "=":
        return math.isclose(last1, threshold, rel_tol=1e-9, abs_tol=1e-12)
    if operator == "cross_up":
        return prev1 is not None and prev1 < threshold and last1 > threshold
    if operator == "cross_down":
        return prev1 is not None and prev1 > threshold and last1 < threshold

    return False


# ─────────────────────────────────────────────────────────────────────────────
# ГЛАВНАЯ ЛОГИКА СТРАТЕГИИ
# ─────────────────────────────────────────────────────────────────────────────
def _evaluate_strategy(
    required: List[Dict[str, Any]],
    groups: List[Dict[str, Any]],
    df: pd.DataFrame,
) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """
    Оценивает, соответствует ли тикер стратегии.

    Логика:
        - ВСЕ required_conditions должны выполниться (AND)
        - ДЛЯ КАЖДОЙ optional_group хотя бы одно условие должно выполниться (OR)
        - Если optional_groups пустой — считается успехом

    Args:
        required (list): список обязательных условий.
        groups (list): список OR-групп (каждая содержит {"group_id": N, "conditions": [...]}).
        df (pd.DataFrame): OHLCV данные тикера.

    Returns:
        Tuple[matched, indicators_debug, error_msg]:
            - matched (bool): True если тикер прошёл стратегию
            - indicators_debug (dict): промежуточные значения для отладки
            - error_msg (str|None): сообщение об ошибке если было
    """
    series_cache: Dict[str, pd.Series] = {}
    conditions_detail: list = []  # детали по КАЖДОМУ условию
    error_msg: Optional[str] = None
    strategy_matched = True

    def _run_cond(cond: Dict[str, Any], group_type: str, group_id: Optional[int] = None) -> bool:
        """Проверяет условие и записывает детали."""
        indicator = (cond.get("indicator") or "").strip()
        operator  = (cond.get("operator") or "").strip()
        label     = cond.get("name") or indicator.upper()
        params    = cond.get("params") or {}
        threshold = cond.get("value")
        compare_to = (cond.get("compare_to_indicator") or "").strip()

        detail: Dict[str, Any] = {
            "label": label,
            "indicator": indicator,
            "params": params,
            "operator": operator,
            "threshold": threshold,
            "compare_to": compare_to or None,
            "value": None,
            "passed": False,
            "group_type": group_type,  # "must" | "or"
            "group_id": group_id,
            "error": None,
        }
        try:
            key1 = _indicator_cache_key(indicator, params)
            if key1 not in series_cache:
                series_cache[key1] = _compute_indicator_series(indicator, df, params)
            _, last1 = _series_tail_two(series_cache[key1])
            detail["value"] = round(last1, 4) if last1 is not None else None

            passed = _check_condition(cond, df, series_cache)
            detail["passed"] = passed
        except Exception as e:
            detail["error"] = str(e)
            passed = False

        conditions_detail.append(detail)
        return passed

    # Шаг 1 — обязательные условия (AND)
    for cond in required:
        try:
            passed = _run_cond(cond, "must")
        except Exception as e:
            error_msg = str(e)
            strategy_matched = False
            continue
        if not passed:
            strategy_matched = False

    # Шаг 2 — каждая OR-группа (хотя бы одно условие)
    for group in groups:
        gid = group.get("group_id")
        group_conds = group.get("conditions") or []
        if not group_conds:
            continue
        group_matched = False
        for cond in group_conds:
            try:
                passed = _run_cond(cond, "or", gid)
            except Exception as e:
                error_msg = str(e)
                continue
            if passed:
                group_matched = True
        if not group_matched:
            strategy_matched = False

    return strategy_matched, conditions_detail, error_msg



# ─────────────────────────────────────────────────────────────────────────────
# ЗАГРУЗКА ДАННЫХ
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_ohlc_sync(ticker: str) -> pd.DataFrame:
    """
    Синхронная загрузка OHLCV-данных через yfinance.

    Загружает 2 года дневных свечей (≈504 бара) — достаточно для
    расчёта любого индикатора с периодом до 200 и не перегружает Yahoo.

    Args:
        ticker (str): биржевой тикер.

    Returns:
        pd.DataFrame: OHLCV данные или пустой DataFrame при ошибке.
    """
    try:
        df = yf.download(
            ticker,
            period=HISTORY_PERIOD,
            interval="1d",
            progress=False,
            threads=False,
            auto_adjust=False,
            timeout=10,
        )

        if df is None or df.empty:
            return pd.DataFrame()

        # Обработка MultiIndex (частая проблема новых версий yfinance)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        required_cols = {"Open", "High", "Low", "Close", "Volume"}
        if not required_cols.issubset(df.columns):
            return pd.DataFrame()

        return df.dropna(how="all")

    except Exception:
        return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# ПУБЛИЧНЫЙ API
# ─────────────────────────────────────────────────────────────────────────────
async def analyze_tickers_async(
    tickers: List[str],
    strategy_config: Dict[str, Any],
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Асинхронно анализирует список тикеров по условиям стратегии.

    Загрузка данных для каждого тикера выполняется в пуле потоков,
    чтобы не блокировать event loop.

    Args:
        tickers (list[str]): список тикеров для анализа.
        strategy_config (dict): конфиг стратегии из Django (результат to_fastapi_config()).

    Returns:
        Tuple[matched, results]:
            - matched (list[str]): тикеры, прошедшие стратегию
            - results (list[dict]): подробные результаты по каждому тикеру
    """
    required_conds, optional_groups = _parse_strategy_config(strategy_config)

    # Клиентские лимиты на уровне FastAPI (дополнительная защита)
    total_conds = len(required_conds) + sum(
        len(g.get("conditions") or []) for g in optional_groups
    )
    if total_conds > MAX_CONDITIONS:
        return [], [{"error": f"Too many conditions (max {MAX_CONDITIONS})"}]
    if len(optional_groups) > MAX_OR_GROUPS:
        return [], [{"error": f"Too many OR-groups (max {MAX_OR_GROUPS})"}]

    results: List[Dict[str, Any]] = []
    matched: List[str] = []

    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=5)

    for ticker in tickers:
        df = await loop.run_in_executor(executor, _fetch_ohlc_sync, ticker)

        if df.empty or len(df) < 2:
            results.append({
                "ticker": ticker,
                "matched": False,
                "indicators": {},
                "error": "No data",
            })
            continue

        try:
            ok, conditions_detail, err = _evaluate_strategy(required_conds, optional_groups, df)
        except Exception as e:
            ok, conditions_detail, err = False, [], str(e)

        entry: Dict[str, Any] = {
            "ticker": ticker,
            "matched": ok,
            "conditions": conditions_detail,  # детальные результаты по каждому условию
        }
        if err:
            entry["error"] = err

        results.append(entry)
        if ok:
            matched.append(ticker)

    return matched, results
