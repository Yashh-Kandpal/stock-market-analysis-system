import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import MLResult

logger = logging.getLogger(__name__)

CACHE_TTL_HOURS = 24  # retrain after 24 hours


async def _get_db_cache(symbol: str, model: str, days: int, db: AsyncSession) -> Optional[dict]:
    result = await db.execute(
        select(MLResult).where(
            MLResult.symbol == symbol,
            MLResult.model  == model,
            MLResult.days   == days,
        )
    )
    row = result.scalar()
    if not row:
        return None
    age_hours = (datetime.utcnow() - row.trained_at).total_seconds() / 3600
    if age_hours > CACHE_TTL_HOURS:
        return None
    return json.loads(row.result)


async def _set_db_cache(symbol: str, model: str, days: int, result: dict, db: AsyncSession):
    existing = await db.execute(
        select(MLResult).where(
            MLResult.symbol == symbol,
            MLResult.model  == model,
            MLResult.days   == days,
        )
    )
    row = existing.scalar()
    result_json = json.dumps(result)
    if row:
        row.result     = result_json
        row.trained_at = datetime.utcnow()
    else:
        db.add(MLResult(
            symbol=symbol, model=model, days=days, result=result_json
        ))
    await db.commit()


async def predict_arima(records, symbol, days, forecast_days=14, db=None):
    if db:
        cached = await _get_db_cache(symbol, f"arima_{forecast_days}", days, db)
        if cached:
            return {**cached, "cached": True}
    from ml.arima_model import run_arima
    result = await asyncio.to_thread(run_arima, records, forecast_days)
    result["cached"] = False
    if db:
        await _set_db_cache(symbol, f"arima_{forecast_days}", days, result, db)
    return result


async def predict_linear(records, symbol, days, db=None):
    if db:
        cached = await _get_db_cache(symbol, "linear", days, db)
        if cached:
            return {**cached, "cached": True}
    from ml.linear_model import run_linear_regression
    result = await asyncio.to_thread(run_linear_regression, records)
    result["cached"] = False
    if db:
        await _set_db_cache(symbol, "linear", days, result, db)
    return result


async def predict_xgboost(records, symbol, days, db=None):
    if db:
        cached = await _get_db_cache(symbol, "xgboost", days, db)
        if cached:
            return {**cached, "cached": True}
    from ml.xgboost_model import run_xgboost
    result = await asyncio.to_thread(run_xgboost, records)
    result["cached"] = False
    if db:
        await _set_db_cache(symbol, "xgboost", days, result, db)
    return result


async def predict_isolation_forest(records, symbol, days, contamination=0.05, db=None):
    if db:
        cached = await _get_db_cache(symbol, f"iforest_{contamination}", days, db)
        if cached:
            return {**cached, "cached": True}
    from ml.isolation_forest import run_isolation_forest
    result = await asyncio.to_thread(run_isolation_forest, records, contamination)
    result["cached"] = False
    if db:
        await _set_db_cache(symbol, f"iforest_{contamination}", days, result, db)
    return result


async def predict_prophet(records, symbol, days, forecast_days=30, db=None):
    if db:
        cached = await _get_db_cache(symbol, f"prophet_{forecast_days}", days, db)
        if cached:
            return {**cached, "cached": True}
    from ml.prophet_model import run_prophet
    result = await asyncio.to_thread(run_prophet, records, forecast_days)
    result["cached"] = False
    if db:
        await _set_db_cache(symbol, f"prophet_{forecast_days}", days, result, db)
    return result


def clear_cache(symbol=None):
    pass  # DB cache is cleared via the DELETE endpoint