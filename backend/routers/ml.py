"""
ML Router — /api/ml/{symbol}/...
Updated to log predictions automatically after each successful model run.
"""

import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta

from database import get_db, StockPrice
from yahoo_finance import fetch_daily
from ml.predictor import (
    predict_arima, predict_linear, predict_xgboost,
    predict_isolation_forest, predict_prophet, clear_cache,
)
from prediction_logger import log_prediction

router  = APIRouter()
logger  = logging.getLogger(__name__)
MIN_ROWS = 30


async def _load_records(symbol: str, days: int, db: AsyncSession) -> list[dict]:
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    cutoff = datetime.utcnow() - timedelta(days=days)
    stmt = (
        select(StockPrice)
        .where(and_(
            StockPrice.symbol   == symbol,
            StockPrice.interval == "1day",
            StockPrice.timestamp >= cutoff,
        ))
        .order_by(StockPrice.timestamp)
    )
    rows = (await db.execute(stmt)).scalars().all()

    expected = days * 5 / 7
    if len(rows) >= expected * 0.8:
        return [
            {
                "timestamp": r.timestamp.isoformat(),
                "open": r.open, "high": r.high,
                "low":  r.low,  "close": r.close,
                "volume": r.volume,
            }
            for r in rows
        ]

    logger.info(f"ML: fetching {days}d data for {symbol} from yfinance")
    try:
        fresh = await asyncio.to_thread(fetch_daily, symbol, days)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"yfinance error: {e}")

    if fresh:
        try:
            insert_stmt = pg_insert(StockPrice).values([
                {
                    "symbol":    r["symbol"],
                    "timestamp": r["timestamp"],
                    "open":      r["open"],
                    "high":      r["high"],
                    "low":       r["low"],
                    "close":     r["close"],
                    "volume":    r["volume"],
                    "interval":  r["interval"],
                }
                for r in fresh
            ]).on_conflict_do_nothing(
                index_elements=["symbol", "timestamp", "interval"]
            )
            await db.execute(insert_stmt)
            await db.commit()
        except Exception:
            await db.rollback()

    return [
        {**r, "timestamp": r["timestamp"].isoformat() if isinstance(r["timestamp"], datetime) else r["timestamp"]}
        for r in fresh
    ]


def _get_prev_close(records: list[dict]) -> float | None:
    """Get the most recent closing price from records."""
    if not records:
        return None
    try:
        return float(records[-1]["close"])
    except (KeyError, TypeError, ValueError):
        return None


@router.get("/{symbol}/arima")
async def get_arima(
    symbol:        str,
    days:          int = Query(365, ge=90,  le=730),
    forecast_days: int = Query(14,  ge=5,   le=30),
    db: AsyncSession = Depends(get_db),
):
    records = await _load_records(symbol.upper(), days, db)
    if len(records) < MIN_ROWS:
        raise HTTPException(status_code=422, detail=f"Only {len(records)} data points")
    try:
        result = await predict_arima(records, symbol.upper(), days, forecast_days, db)
        # Log prediction silently
        await log_prediction(db, symbol.upper(), "arima", result, _get_prev_close(records))
        return {"symbol": symbol.upper(), "days": days, **result}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/linear")
async def get_linear(
    symbol: str,
    days:   int = Query(365, ge=90, le=730),
    db: AsyncSession = Depends(get_db),
):
    records = await _load_records(symbol.upper(), days, db)
    if len(records) < MIN_ROWS:
        raise HTTPException(status_code=422, detail=f"Only {len(records)} data points")
    try:
        result = await predict_linear(records, symbol.upper(), days, db)
        await log_prediction(db, symbol.upper(), "linear", result, _get_prev_close(records))
        return {"symbol": symbol.upper(), "days": days, **result}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/xgboost")
async def get_xgboost(
    symbol: str,
    days:   int = Query(365, ge=90, le=730),
    db: AsyncSession = Depends(get_db),
):
    records = await _load_records(symbol.upper(), days, db)
    if len(records) < MIN_ROWS:
        raise HTTPException(status_code=422, detail=f"Only {len(records)} data points")
    try:
        result = await predict_xgboost(records, symbol.upper(), days, db)
        await log_prediction(db, symbol.upper(), "xgboost", result, _get_prev_close(records))
        return {"symbol": symbol.upper(), "days": days, **result}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/isolation-forest")
async def get_isolation_forest(
    symbol:        str,
    days:          int   = Query(365,  ge=90,  le=730),
    contamination: float = Query(0.05, ge=0.01, le=0.2),
    db: AsyncSession = Depends(get_db),
):
    records = await _load_records(symbol.upper(), days, db)
    if len(records) < MIN_ROWS:
        raise HTTPException(status_code=422, detail=f"Only {len(records)} data points")
    try:
        result = await predict_isolation_forest(records, symbol.upper(), days, contamination, db)
        # Isolation forest is anomaly detection, not directional — skip logging
        return {"symbol": symbol.upper(), "days": days, **result}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/prophet")
async def get_prophet(
    symbol:        str,
    days:          int = Query(730, ge=180, le=1460),
    forecast_days: int = Query(30,  ge=7,   le=90),
    db: AsyncSession = Depends(get_db),
):
    records = await _load_records(symbol.upper(), days, db)
    if len(records) < 60:
        raise HTTPException(status_code=422, detail=f"Only {len(records)} data points")
    try:
        result = await predict_prophet(records, symbol.upper(), days, forecast_days, db)
        await log_prediction(db, symbol.upper(), "prophet", result, _get_prev_close(records))
        return {"symbol": symbol.upper(), "days": days, **result}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/summary")
async def get_ml_summary(
    symbol: str,
    days:   int = Query(365, ge=90, le=730),
    db: AsyncSession = Depends(get_db),
):
    records = await _load_records(symbol.upper(), days, db)
    if len(records) < MIN_ROWS:
        raise HTTPException(status_code=422, detail="Not enough data")

    sym = symbol.upper()

    async def _safe(coro, name):
        try:
            return name, await coro
        except Exception as e:
            logger.warning(f"ML summary: {name} failed — {e}")
            return name, {"error": str(e)}

    results = await asyncio.gather(
        _safe(predict_arima(records, sym, days, 14, db),        "arima"),
        _safe(predict_linear(records, sym, days, db),           "linear"),
        _safe(predict_xgboost(records, sym, days, db),          "xgboost"),
        _safe(predict_isolation_forest(records, sym, days, db=db), "isolation_forest"),
    )

    prev_close = _get_prev_close(records)
    out = {"symbol": sym, "days": days}
    for name, res in results:
        if "error" not in res:
            if name in ("arima", "linear", "xgboost", "prophet"):
                await log_prediction(db, sym, name, res, prev_close)
            stripped = {k: v for k, v in res.items()
                        if k not in ("historical", "forecast", "score_series",
                                     "anomalies", "returns_series", "drawdown_series")}
            out[name] = stripped
        else:
            out[name] = res

    return out


@router.delete("/{symbol}/cache")
async def clear_model_cache(symbol: str):
    clear_cache(symbol.upper())
    return {"message": f"Cache cleared for {symbol.upper()}"}
