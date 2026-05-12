import os
import asyncio
from celery import Celery
from schemas.analyze_engine import analyze_tickers_async

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/1")

celery_app = Celery(
    "analysis_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

def _run_async(tickers, strategy_config):
    # Создаем новый цикл для каждого потока/таски
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(analyze_tickers_async(tickers, strategy_config))
    finally:
        loop.close()

@celery_app.task(name="tasks.analyze", bind=True)
def run_analysis_task(self, tickers: list, strategy_config: dict):
    """
    Фоновая задача анализа тикеров.
    """
    matched, details = _run_async(tickers, strategy_config)
    return {
        "matched": matched,
        "details": details
    }
