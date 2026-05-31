"""
Statistical Analysis Router
All endpoints under /api/analysis/{symbol}/...

Design choices:
- Data is fetched from DB first; falls back to yfinance if not enough rows.
- The `days` query param controls the time window for every stat.
- Each stat can also be requested independently for granular control.
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta

from database import get_db, StockPrice
from yahoo_finance import fetch_daily
from analysis.statistics import (
    moving_averages,
    volatility,
    zscore_anomalies,
    rsi,
    macd,
    support_resistance,
    returns_analysis,
    full_summary,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# ─── shared helper ────────────────────────────────────────────────────────────

async def _load_records(
    symbol: str,
    days: int,
    db: AsyncSession,
    min_rows: int = 30,
) -> list[dict]:
    """
    Load OHLCV records from DB; fall back to yfinance if insufficient.
    Returns plain dicts sorted by timestamp ascending.
    """
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

    if len(rows) >= min_rows:
        return [
            {
                "timestamp": r.timestamp.isoformat(),
                "open":      r.open,
                "high":      r.high,
                "low":       r.low,
                "close":     r.close,
                "volume":    r.volume,
            }
            for r in rows
        ]

    # Fallback: fetch from yfinance and upsert
    logger.info(f"DB has only {len(rows)} rows for {symbol}/{days}d — fetching from yfinance")
    try:
        fresh = await asyncio.to_thread(fetch_daily, symbol, days)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"yfinance error: {e}")

    for r in fresh:
        existing = (await db.execute(
            select(StockPrice).where(and_(
                StockPrice.symbol == r["symbol"],
                StockPrice.timestamp == r["timestamp"],
                StockPrice.interval == "1day",
            ))
        )).scalar()
        if not existing:
            db.add(StockPrice(**r))
    await db.commit()

    return [
        {**r, "timestamp": r["timestamp"].isoformat() if isinstance(r["timestamp"], datetime) else r["timestamp"]}
        for r in fresh
    ]


# ─── endpoints ────────────────────────────────────────────────────────────────

@router.get("/{symbol}/summary")
async def get_summary(
    symbol: str,
    days: int = Query(90, ge=30, le=365, description="Lookback window in days"),
    db: AsyncSession = Depends(get_db),
):
    """
    Quick overview card: current price, MAs, volatility, RSI, Z-score, drawdown.
    Ideal for the stock detail page sidebar.
    """
    records = await _load_records(symbol.upper(), days, db)
    if len(records) < 5:
        raise HTTPException(status_code=422, detail="Not enough data for analysis")
    return {"symbol": symbol.upper(), "days": days, **full_summary(records)}


@router.get("/{symbol}/moving-averages")
async def get_moving_averages(
    symbol: str,
    days:    int = Query(180, ge=30, le=730),
    windows: str = Query("9,20,50,200", description="Comma-separated MA windows e.g. 9,20,50,200"),
    db: AsyncSession = Depends(get_db),
):
    """
    SMA + EMA for each requested window.
    Returns full series (for charting) + latest values + golden/death cross signals.
    """
    win_list = [int(w.strip()) for w in windows.split(",") if w.strip().isdigit()]
    if not win_list:
        raise HTTPException(status_code=422, detail="Invalid windows parameter")

    records = await _load_records(symbol.upper(), days, db, min_rows=max(win_list))
    return {"symbol": symbol.upper(), "days": days, **moving_averages(records, win_list)}


@router.get("/{symbol}/volatility")
async def get_volatility(
    symbol: str,
    days:   int = Query(180, ge=30, le=730),
    window: int = Query(20, ge=5, le=100, description="Rolling window for vol calculation"),
    db: AsyncSession = Depends(get_db),
):
    """
    Annualised rolling volatility, ATR, and Bollinger Bands.
    """
    records = await _load_records(symbol.upper(), days, db, min_rows=window + 5)
    return {"symbol": symbol.upper(), "days": days, **volatility(records, window)}


@router.get("/{symbol}/anomalies")
async def get_anomalies(
    symbol:    str,
    days:      int   = Query(180, ge=30, le=730),
    window:    int   = Query(20, ge=5, le=100, description="Rolling window for Z-score baseline"),
    threshold: float = Query(2.5, ge=1.0, le=5.0, description="Z-score threshold for anomaly flag"),
    db: AsyncSession = Depends(get_db),
):
    """
    Rolling Z-score anomaly detection on price and volume.
    Returns flagged candles with severity.
    """
    records = await _load_records(symbol.upper(), days, db, min_rows=window + 5)
    return {"symbol": symbol.upper(), "days": days, **zscore_anomalies(records, window, threshold)}


@router.get("/{symbol}/rsi")
async def get_rsi(
    symbol: str,
    days:   int = Query(180, ge=30, le=730),
    period: int = Query(14, ge=5, le=50),
    db: AsyncSession = Depends(get_db),
):
    """RSI with overbought / oversold signals."""
    records = await _load_records(symbol.upper(), days, db, min_rows=period + 10)
    return {"symbol": symbol.upper(), "days": days, **rsi(records, period)}


@router.get("/{symbol}/macd")
async def get_macd(
    symbol:         str,
    days:           int = Query(180, ge=90, le=730),
    fast:           int = Query(12, ge=3,  le=50),
    slow:           int = Query(26, ge=10, le=100),
    signal_period:  int = Query(9,  ge=3,  le=30),
    db: AsyncSession = Depends(get_db),
):
    """MACD line, signal line, histogram, and crossover events."""
    if fast >= slow:
        raise HTTPException(status_code=422, detail="fast must be less than slow")
    records = await _load_records(symbol.upper(), days, db, min_rows=slow + 10)
    return {"symbol": symbol.upper(), "days": days, **macd(records, fast, slow, signal_period)}


@router.get("/{symbol}/support-resistance")
async def get_support_resistance(
    symbol: str,
    days:   int = Query(180, ge=90, le=730),
    window: int = Query(10, ge=3, le=30, description="Pivot window for local extrema"),
    db: AsyncSession = Depends(get_db),
):
    """Pivot-point based support & resistance levels."""
    records = await _load_records(symbol.upper(), days, db, min_rows=window * 3)
    return {"symbol": symbol.upper(), "days": days, **support_resistance(records, window)}


@router.get("/{symbol}/returns")
async def get_returns(
    symbol: str,
    days:   int = Query(365, ge=30, le=730),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns distribution, Sharpe ratio (India rf=6%), max drawdown,
    skewness, kurtosis, win rate.
    """
    records = await _load_records(symbol.upper(), days, db, min_rows=20)
    return {"symbol": symbol.upper(), "days": days, **returns_analysis(records)}


@router.get("/{symbol}/full")
async def get_full_analysis(
    symbol: str,
    days:   int = Query(180, ge=60, le=730),
    db: AsyncSession = Depends(get_db),
):
    """
    All statistics in one call — used for the full analysis page.
    Heavier endpoint; results are computed fresh each time.
    """
    records = await _load_records(symbol.upper(), days, db, min_rows=30)
    if len(records) < 30:
        raise HTTPException(status_code=422, detail="Not enough data for full analysis")

    return {
        "symbol":             symbol.upper(),
        "days":               days,
        "data_points":        len(records),
        "summary":            full_summary(records),
        "moving_averages":    moving_averages(records),
        "volatility":         volatility(records),
        "anomalies":          zscore_anomalies(records),
        "rsi":                rsi(records),
        "macd":               macd(records),
        "support_resistance": support_resistance(records),
        "returns":            returns_analysis(records),
    }
