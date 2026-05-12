from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from auth.service import verify_internal_key
from schemas.schemas import AnalyzeRequest, AnalyzeResponse, TickerResult
from worker import run_analysis_task
from celery.result import AsyncResult
from logger import setup_logging, get_logger
import yfinance as yf
import math
import asyncio
import json
import os
import redis

setup_logging()
logger = get_logger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "http://django:8000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Redis-клиент для кэша ────────────────────────────────────────────────────
_redis_client = None

def get_redis():
    global _redis_client
    if _redis_client is None:
        url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        _redis_client = redis.from_url(url, decode_responses=True)
    return _redis_client

# ── Маппинг таймфреймов ──────────────────────────────────────────────────────
# tf_id -> (yfinance period, yfinance interval, TTL кэша в секундах)
TF_MAP = {
    "5m":  ("7d",  "5m",   300),     # 5 мин  — кэш 5 мин
    "30m": ("60d", "30m",  600),     # 30 мин — кэш 10 мин
    "1h":  ("2y",  "1h",   1800),    # 1 час  — кэш 30 мин
    "4h":  ("2y",  "1h",   3600),    # 4 часа — кэш 1 час (агрегируем на клиенте)
    "1d":  ("5y",  "1d",   7200),    # День   — кэш 2 часа
    "1w":  ("10y", "1wk",  86400),   # Неделя — кэш 1 день
    "1mo": ("max", "1mo",  86400),   # Месяц  — кэш 1 день
}


@app.post("/analyze/")
async def analyze(request: AnalyzeRequest, _=Depends(verify_internal_key)):
    """Ставит задачу на анализ в очередь Celery. Возвращает task_id."""
    logger.info("Запуск анализа: %d тикеров, стратегия: %s",
                len(request.tickers), list(request.strategy_config.keys())[:2])
    task = run_analysis_task.delay(request.tickers, request.strategy_config)
    logger.debug("Задача создана: task_id=%s", task.id)
    return {"task_id": task.id, "status": "pending"}


@app.get("/analyze/status/{task_id}")
async def analyze_status(task_id: str, _=Depends(verify_internal_key)):
    """Возвращает статус задачи из Celery. Если задача готова, возвращает результат."""
    task_result = AsyncResult(task_id)
    if task_result.ready():
        if task_result.successful():
            result = task_result.result
            matched = result.get("matched", [])
            logger.info("Анализ завершён task_id=%s: найдено %d тикеров", task_id, len(matched))
            detail_models = [TickerResult(**d) for d in result.get("details", [])]
            return {
                "status": "completed",
                "result": AnalyzeResponse(
                    matched=matched,
                    details=detail_models,
                ).dict(),
            }
        else:
            logger.error("Задача task_id=%s завершилась с ошибкой: %s", task_id, task_result.result)
            return {"status": "failed", "error": str(task_result.result)}
    return {"status": "pending"}


@app.get("/chart-data/{ticker}")
async def chart_data(
    ticker: str,
    tf: str = Query(default="1d", description="Таймфрейм: 5m, 30m, 1h, 4h, 1d, 1w, 1mo"),
    # Обратная совместимость — старые параметры period/interval игнорируются если есть tf
    period: str = Query(default=None),
    interval: str = Query(default=None),
):
    """
    OHLCV данные для Lightweight Charts.
    Кэшируется в Redis по ключу ticker:tf с TTL согласно таймфрейму.
    """
    # Нормализация tf
    tf = tf.lower()
    if tf not in TF_MAP:
        # Попытка угадать по старым параметрам period/interval
        tf = "1d"

    cache_key = f"chart:{ticker.upper()}:{tf}"

    # 1. Пробуем отдать из кэша
    try:
        cached = get_redis().get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass  # Redis недоступен — идём дальше без кэша

    yf_period, yf_interval, ttl = TF_MAP[tf]

    # 2. Загружаем с Yahoo Finance
    try:
        df = yf.download(
            ticker,
            period=yf_period,
            interval=yf_interval,
            progress=False,
            threads=False,
            auto_adjust=True,
        )
    except Exception as e:
        logger.error("Ошибка загрузки данных %s tf=%s: %s", ticker, tf, e)
        return {"error": str(e), "candles": [], "volume": []}

    if df is None or df.empty:
        logger.warning("Нет данных для %s tf=%s", ticker, tf)
        return {"error": "No data", "candles": [], "volume": []}

    # Нормализуем MultiIndex
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)

    candles, volume = [], []
    is_intraday = yf_interval not in ("1d", "1wk", "1mo")

    # 3. Агрегация 4h из 1h баров
    if tf == "4h":
        df = df.resample("4h").agg({
            "Open": "first", "High": "max", "Low": "min",
            "Close": "last", "Volume": "sum",
        }).dropna(subset=["Close"])

    for idx, row in df.iterrows():
        try:
            if is_intraday or tf == "4h":
                # Внутридневные: UNIX timestamp в секундах
                import pandas as pd
                ts = int(pd.Timestamp(idx).timestamp())
                time_val = ts
            else:
                time_val = str(idx.date()) if hasattr(idx, "date") else str(idx)

            o = float(row.get("Open",  row.get("open",  0)) or 0)
            h = float(row.get("High",  row.get("high",  0)) or 0)
            l = float(row.get("Low",   row.get("low",   0)) or 0)
            c = float(row.get("Close", row.get("close", 0)) or 0)
            v = float(row.get("Volume",row.get("volume",0)) or 0)

            if any(math.isnan(x) for x in [o, h, l, c]):
                continue

            candles.append({"time": time_val, "open": round(o,4), "high": round(h,4),
                            "low": round(l,4), "close": round(c,4)})
            volume.append({"time": time_val, "value": round(v,0),
                           "color": "#22c55e" if c >= o else "#ef4444"})
        except Exception:
            continue

    result = {"ticker": ticker.upper(), "tf": tf, "candles": candles, "volume": volume}

    # 4. Сохраняем в Redis
    try:
        get_redis().setex(cache_key, ttl, json.dumps(result))
    except Exception:
        pass

    return result


@app.get("/stock-info/{ticker}")
async def stock_info(ticker: str):
    """
    Возвращает детальную информацию об акции с Yahoo Finance.
    Открытый endpoint — данные публичны.
    """
    import concurrent.futures
    def _fetch_info():
        t = yf.Ticker(ticker)
        return t.info

    try:
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            info = await asyncio.wait_for(
                loop.run_in_executor(pool, _fetch_info),
                timeout=20.0
            )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Превышено время ожидания данных от Yahoo Finance")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not info or (not info.get("symbol") and not info.get("shortName")):
        raise HTTPException(status_code=404, detail="Тикер не найден")

    def safe(v, default="—"):
        if v is None or v == "":
            return default
        return v

    def fmt_num(v):
        if v is None:
            return "—"
        if isinstance(v, (int, float)):
            if v >= 1_000_000_000_000:
                return f"{v/1_000_000_000_000:.2f} трлн"
            if v >= 1_000_000_000:
                return f"{v/1_000_000_000:.2f} млрд"
            if v >= 1_000_000:
                return f"{v/1_000_000:.2f} млн"
        return str(v)

    SECTOR_MAP = {
        "Technology": "Технологии", "Financial Services": "Финансы",
        "Healthcare": "Здравоохранение", "Consumer Cyclical": "Потребительский (цикл.)",
        "Consumer Defensive": "Потребительский (защ.)", "Industrials": "Промышленность",
        "Communication Services": "Телекоммуникации", "Energy": "Энергетика",
        "Utilities": "Коммунальные услуги", "Real Estate": "Недвижимость",
        "Basic Materials": "Сырьё и материалы",
    }

    price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")

    return {
        "symbol": safe(info.get("symbol"), ticker.upper()),
        "name": safe(info.get("longName") or info.get("shortName"), ticker.upper()),
        "sector": SECTOR_MAP.get(info.get("sector", ""), safe(info.get("sector"))),
        "industry": safe(info.get("industry")),
        "country": safe(info.get("country")),
        "currency": safe(info.get("currency"), "USD"),
        "exchange": safe(info.get("exchange")),
        "website": safe(info.get("website")),
        "description": safe(info.get("longBusinessSummary")),
        "price": price,
        "previous_close": safe(info.get("previousClose")),
        "open": safe(info.get("open")),
        "day_low": safe(info.get("dayLow")),
        "day_high": safe(info.get("dayHigh")),
        "week_52_low": safe(info.get("fiftyTwoWeekLow")),
        "week_52_high": safe(info.get("fiftyTwoWeekHigh")),
        "volume": fmt_num(info.get("volume")),
        "avg_volume": fmt_num(info.get("averageVolume")),
        "market_cap": fmt_num(info.get("marketCap")),
        "enterprise_value": fmt_num(info.get("enterpriseValue")),
        "pe_ratio": safe(info.get("trailingPE")),
        "forward_pe": safe(info.get("forwardPE")),
        "peg_ratio": safe(info.get("trailingPegRatio")),
        "ps_ratio": safe(info.get("priceToSalesTrailing12Months")),
        "pb_ratio": safe(info.get("priceToBook")),
        "ev_ebitda": safe(info.get("enterpriseToEbitda")),
        "revenue": fmt_num(info.get("totalRevenue")),
        "gross_profit": fmt_num(info.get("grossProfits")),
        "ebitda": fmt_num(info.get("ebitda")),
        "net_income": fmt_num(info.get("netIncomeToCommon")),
        "eps": safe(info.get("trailingEps")),
        "earnings_growth": safe(info.get("earningsGrowth")),
        "revenue_growth": safe(info.get("revenueGrowth")),
        "dividend_rate": safe(info.get("dividendRate")),
        "dividend_yield": f"{round(info.get('dividendYield', 0) * 100, 2)}%" if info.get("dividendYield") else "—",
        "payout_ratio": safe(info.get("payoutRatio")),
        "profit_margin": f"{round(info.get('profitMargins', 0) * 100, 2)}%" if info.get("profitMargins") else "—",
        "gross_margin": f"{round(info.get('grossMargins', 0) * 100, 2)}%" if info.get("grossMargins") else "—",
        "operating_margin": f"{round(info.get('operatingMargins', 0) * 100, 2)}%" if info.get("operatingMargins") else "—",
        "roe": f"{round(info.get('returnOnEquity', 0) * 100, 2)}%" if info.get("returnOnEquity") else "—",
        "roa": f"{round(info.get('returnOnAssets', 0) * 100, 2)}%" if info.get("returnOnAssets") else "—",
        "total_cash": fmt_num(info.get("totalCash")),
        "total_debt": fmt_num(info.get("totalDebt")),
        "debt_to_equity": safe(info.get("debtToEquity")),
        "current_ratio": safe(info.get("currentRatio")),
        "beta": safe(info.get("beta")),
        "shares_outstanding": fmt_num(info.get("sharesOutstanding")),
        "held_by_insiders": f"{round(info.get('heldPercentInsiders', 0) * 100, 2)}%" if info.get("heldPercentInsiders") else "—",
        "held_by_institutions": f"{round(info.get('heldPercentInstitutions', 0) * 100, 2)}%" if info.get("heldPercentInstitutions") else "—",
        "recommendation": safe(info.get("recommendationKey")),
        "target_price": safe(info.get("targetMeanPrice")),
        "analyst_count": safe(info.get("numberOfAnalystOpinions")),
    }


@app.post("/analyze-one/")
async def analyze_one(request: dict, _=Depends(verify_internal_key)):
    """Анализирует один тикер по стратегии. Используется на странице акции."""
    ticker = request.get("ticker")
    strategy_config = request.get("strategy_config")
    if not ticker or not strategy_config:
        raise HTTPException(status_code=400, detail="ticker и strategy_config обязательны")

    from schemas.analyze_engine import analyze_tickers_async
    matched, details = await analyze_tickers_async([ticker], strategy_config)
    return {"matched": matched, "details": details}