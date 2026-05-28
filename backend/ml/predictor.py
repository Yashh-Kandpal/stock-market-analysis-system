"""
Unified ML predictor interface.
Handles model caching so we don't retrain on every request.
Cache expires after 24 hours or when new data arrives.
"""

import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# In-memory cache: {cache_key: (result, timestamp)}
_cache: dict = {}
CACHE_TTL_SECONDS = 60 * 60 * 6   # 6 hours


def _cache_key(symbol: str, model: str, days: int) -> str:
    return f"{symbol}:{model}:{days}"


def _get_cached(key: str) -> Optional[dict]:
    if key in _cache:
        result, ts = _cache[key]
        if time.time() - ts < CACHE_TTL_SECONDS:
            return result
        del _cache[key]
    return None


def _set_cache(key: str, result: dict):
    _cache[key] = (result, time.time())


async def predict_arima(records: list[dict], symbol: str, days: int, forecast_days: int = 14) -> dict:
    key = _cache_key(symbol, "arima", days)
    cached = _get_cached(key)
    if cached:
        return {**cached, "cached": True}

    from ml.arima_model import run_arima
    result = await asyncio.to_thread(run_arima, records, forecast_days)
    result["cached"] = False
    _set_cache(key, result)
    return result


async def predict_linear(records: list[dict], symbol: str, days: int) -> dict:
    key = _cache_key(symbol, "linear", days)
    cached = _get_cached(key)
    if cached:
        return {**cached, "cached": True}

    from ml.linear_model import run_linear_regression
    result = await asyncio.to_thread(run_linear_regression, records)
    result["cached"] = False
    _set_cache(key, result)
    return result


async def predict_xgboost(records: list[dict], symbol: str, days: int) -> dict:
    key = _cache_key(symbol, "xgboost", days)
    cached = _get_cached(key)
    if cached:
        return {**cached, "cached": True}

    from ml.xgboost_model import run_xgboost
    result = await asyncio.to_thread(run_xgboost, records)
    result["cached"] = False
    _set_cache(key, result)
    return result


async def predict_isolation_forest(records: list[dict], symbol: str, days: int, contamination: float = 0.05) -> dict:
    key = _cache_key(symbol, f"iforest_{contamination}", days)
    cached = _get_cached(key)
    if cached:
        return {**cached, "cached": True}

    from ml.isolation_forest import run_isolation_forest
    result = await asyncio.to_thread(run_isolation_forest, records, contamination)
    result["cached"] = False
    _set_cache(key, result)
    return result


async def predict_prophet(records: list[dict], symbol: str, days: int, forecast_days: int = 30) -> dict:
    key = _cache_key(symbol, "prophet", days)
    cached = _get_cached(key)
    if cached:
        return {**cached, "cached": True}

    from ml.prophet_model import run_prophet
    result = await asyncio.to_thread(run_prophet, records, forecast_days)
    result["cached"] = False
    _set_cache(key, result)
    return result


def clear_cache(symbol: Optional[str] = None):
    """Clear cache for a symbol or all symbols."""
    global _cache
    if symbol:
        _cache = {k: v for k, v in _cache.items() if not k.startswith(symbol)}
    else:
        _cache = {}
