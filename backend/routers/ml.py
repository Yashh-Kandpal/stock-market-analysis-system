"""
ML Router — /api/ml/{symbol}/...

Endpoints:
  GET /api/ml/{symbol}/arima          → ARIMA price forecast
  GET /api/ml/{symbol}/linear         → LR direction prediction
  GET /api/ml/{symbol}/xgboost        → XGBoost direction + 5d prediction
  GET /api/ml/{symbol}/isolation-forest → Isolation Forest anomalies
  GET /api/ml/{symbol}/prophet        → Prophet multi-week forecast
  GET /api/ml/{symbol}/summary        → All models, latest predictions only
  DELETE /api/ml/{symbol}/cache       → Clear cached results
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

router  = APIRouter()
logger  = logging.getLogger(__name__)
MIN_ROWS = 30   # minimum data points needed for any model


# ─── shared data loader (same pattern as analysis router) ─────────────────────

async def _load_records(symbol: str, days: int, db: AsyncSession) -> list[dict]:
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    cutoff = datetime.utcnow() - timedelta(days=days)
    stmt = (
        select(StockPrice)
        .where(and_(
            StockPrice.symbol == symbol,
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
                "low": r.low,   "close": r.close,
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

    # Use INSERT ... ON CONFLICT DO NOTHING to safely handle duplicates
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


# ─── endpoints ────────────────────────────────────────────────────────────────

@router.get("/{symbol}/arima")
async def get_arima(
    symbol:       str,
    days:         int = Query(365, ge=90,  le=730, description="Training window in days"),
    forecast_days: int = Query(14,  ge=5,   le=30,  description="How many days to forecast"),
    db: AsyncSession = Depends(get_db),
):
    """ARIMA price forecast with confidence intervals."""
    records = await _load_records(symbol.upper(), days, db)
    if len(records) < MIN_ROWS:
        raise HTTPException(status_code=422, detail=f"Only {len(records)} data points — need {MIN_ROWS}+")
    try:
        return {"symbol": symbol.upper(), "days": days,
                **await predict_arima(records, symbol.upper(), days, forecast_days)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/linear")
async def get_linear(
    symbol: str,
    days:   int = Query(365, ge=90, le=730),
    db: AsyncSession = Depends(get_db),
):
    """Linear + Logistic Regression: next-day direction prediction."""
    records = await _load_records(symbol.upper(), days, db)
    if len(records) < MIN_ROWS:
        raise HTTPException(status_code=422, detail=f"Only {len(records)} data points — need {MIN_ROWS}+")
    try:
        return {"symbol": symbol.upper(), "days": days,
                **await predict_linear(records, symbol.upper(), days)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/xgboost")
async def get_xgboost(
    symbol: str,
    days:   int = Query(365, ge=90, le=730),
    db: AsyncSession = Depends(get_db),
):
    """XGBoost: next-day + 5-day direction prediction with feature importance."""
    records = await _load_records(symbol.upper(), days, db)
    if len(records) < MIN_ROWS:
        raise HTTPException(status_code=422, detail=f"Only {len(records)} data points — need {MIN_ROWS}+")
    try:
        return {"symbol": symbol.upper(), "days": days,
                **await predict_xgboost(records, symbol.upper(), days)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/isolation-forest")
async def get_isolation_forest(
    symbol:        str,
    days:          int   = Query(365,  ge=90,  le=730),
    contamination: float = Query(0.05, ge=0.01, le=0.2,
                                 description="Expected fraction of anomalies (0.01–0.20)"),
    db: AsyncSession = Depends(get_db),
):
    """Isolation Forest multi-dimensional anomaly detection."""
    records = await _load_records(symbol.upper(), days, db)
    if len(records) < MIN_ROWS:
        raise HTTPException(status_code=422, detail=f"Only {len(records)} data points — need {MIN_ROWS}+")
    try:
        return {"symbol": symbol.upper(), "days": days,
                **await predict_isolation_forest(records, symbol.upper(), days, contamination)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/prophet")
async def get_prophet(
    symbol:        str,
    days:          int = Query(730, ge=180, le=1460, description="Training window (Prophet needs more data)"),
    forecast_days: int = Query(30,  ge=7,   le=90),
    db: AsyncSession = Depends(get_db),
):
    """Prophet multi-week forecast with trend + seasonality decomposition."""
    records = await _load_records(symbol.upper(), days, db)
    if len(records) < 60:
        raise HTTPException(status_code=422, detail=f"Only {len(records)} data points — need 60+")
    try:
        return {"symbol": symbol.upper(), "days": days,
                **await predict_prophet(records, symbol.upper(), days, forecast_days)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/summary")
async def get_ml_summary(
    symbol: str,
    days:   int = Query(365, ge=90, le=730),
    db: AsyncSession = Depends(get_db),
):
    """
    Runs all models and returns only their prediction cards (no series data).
    Used for the ML overview panel on the stock detail page.
    Runs models in parallel for speed.
    """
    records = await _load_records(symbol.upper(), days, db)
    if len(records) < MIN_ROWS:
        raise HTTPException(status_code=422, detail=f"Not enough data")

    sym = symbol.upper()

    async def _safe(coro, name):
        try:
            return name, await coro
        except Exception as e:
            logger.warning(f"ML summary: {name} failed — {e}")
            return name, {"error": str(e)}

    results = await asyncio.gather(
        _safe(predict_arima(records, sym, days, 14),          "arima"),
        _safe(predict_linear(records, sym, days),             "linear"),
        _safe(predict_xgboost(records, sym, days),            "xgboost"),
        _safe(predict_isolation_forest(records, sym, days),   "isolation_forest"),
    )

    out = {"symbol": sym, "days": days}
    for name, res in results:
        if "error" in res:
            out[name] = res
        else:
            # Strip heavy series arrays — keep only prediction cards
            stripped = {k: v for k, v in res.items()
                        if k not in ("historical", "forecast", "score_series",
                                     "anomalies", "returns_series", "drawdown_series")}
            out[name] = stripped

    return out


@router.delete("/{symbol}/cache")
async def clear_model_cache(symbol: str):
    """Clear cached ML results for a symbol (forces retrain on next request)."""
    clear_cache(symbol.upper())
    return {"message": f"Cache cleared for {symbol.upper()}"}
