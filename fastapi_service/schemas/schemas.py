from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    tickers: List[str]
    strategy_config: Dict[str, Any]


class ConditionResult(BaseModel):
    label: str
    indicator: str
    params: Dict[str, Any]
    operator: str
    threshold: Optional[float] = None
    compare_to: Optional[str] = None
    value: Optional[float] = None
    passed: bool
    group_type: str  # "must" | "or"
    group_id: Optional[int] = None
    error: Optional[str] = None


class TickerResult(BaseModel):
    ticker: str
    matched: bool
    conditions: List[ConditionResult] = []
    error: Optional[str] = None


class AnalyzeResponse(BaseModel):
    matched: List[str]
    details: List[TickerResult]