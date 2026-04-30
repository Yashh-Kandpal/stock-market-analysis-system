from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import Optional
from datetime import datetime, timedelta
import logging

from database import get_db, StockPrice
from alpha_vantage import (
    fetch_intraday, fetch_daily, fetch_quote, search_symbol,
    parse_intraday_series, parse_daily_series, parse_quote,
    POPULAR_INDIAN_STOCKS
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/popular")
async def get_popular_stocks():
    """Return list of popular Indian stocks."""
    return [
        {"symbol": sym, "company_name": name}
        for sym, name in POPULAR_INDIAN_STOCKS.items()
    ]


@router.get("/search")
async def search_stocks(q: str = Query(..., min_length=1)):
    """Search for stock symbols via Alpha Vantage."""
    try:
        data = await search_symbol(q)
        matches = data.get("bestMatches", [])
        # Filter for Indian stocks (BSE/NSE/BOM)
        indian = [
            {
                "symbol": m["1. symbol"],
                "name": m["2. name"],
                "type": m["3. type"],
                "region": m["4. region"],
                "currency": m["8. currency"],
                "match_score": m["9. matchScore"],
            }
            for m in matches
            if "India" in m.get("4. region", "") or "BSE" in m.get("1. symbol", "") or "NSE" in m.get("1. symbol", "")
        ]
        return indian or [
            {
                "symbol": m["1. symbol"],
                "name": m["2. name"],
                "type": m["3. type"],
                "region": m["4. region"],
                "currency": m["8. currency"],
                "match_score": m["9. matchScore"],
            }
            for m in matches[:5]
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get the latest quote for a stock."""
    try:
        data = await fetch_quote(symbol.upper())
        parsed = parse_quote(data)
        if not parsed:
            raise HTTPException(status_code=404, detail=f"No quote found for {symbol}")
        return parsed
    except ValueError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intraday/{symbol}")
async def get_intraday(
    symbol: str,
    interval: str = Query("5min", regex="^(1min|5min|15min|30min|60min)$"),
    refresh: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Get intraday OHLCV data for a stock.
    - Checks DB first unless refresh=True
    - Fetches from Alpha Vantage and stores if missing
    """
    symbol = symbol.upper()
    cutoff = datetime.utcnow() - timedelta(hours=1)

    if not refresh:
        # Try to serve from DB
        stmt = (
            select(StockPrice)
            .where(and_(StockPrice.symbol == symbol, StockPrice.interval == interval, StockPrice.timestamp >= cutoff))
            .order_by(StockPrice.timestamp)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        if rows:
            return {
                "symbol": symbol,
                "interval": interval,
                "source": "database",
                "count": len(rows),
                "data": [_row_to_dict(r) for r in rows],
            }

    # Fetch from Alpha Vantage
    try:
        raw = await fetch_intraday(symbol, interval)
        parsed = parse_intraday_series(raw, symbol, interval)
    except ValueError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alpha Vantage error: {e}")

    # Upsert into DB
    saved = 0
    for row in parsed:
        existing = await db.execute(
            select(StockPrice).where(
                and_(
                    StockPrice.symbol == row["symbol"],
                    StockPrice.timestamp == row["timestamp"],
                    StockPrice.interval == row["interval"],
                )
            )
        )
        if not existing.scalar():
            db.add(StockPrice(**row))
            saved += 1
    await db.commit()
    logger.info(f"Saved {saved} new rows for {symbol} ({interval})")

    return {
        "symbol": symbol,
        "interval": interval,
        "source": "alpha_vantage",
        "count": len(parsed),
        "data": parsed,
    }


@router.get("/daily/{symbol}")
async def get_daily(
    symbol: str,
    days: int = Query(30, ge=1, le=365),
    refresh: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Get daily OHLCV data for a stock (last N days).
    """
    symbol = symbol.upper()
    cutoff = datetime.utcnow() - timedelta(days=days)

    if not refresh:
        stmt = (
            select(StockPrice)
            .where(and_(StockPrice.symbol == symbol, StockPrice.interval == "1day", StockPrice.timestamp >= cutoff))
            .order_by(StockPrice.timestamp)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        if rows:
            return {
                "symbol": symbol,
                "interval": "1day",
                "source": "database",
                "count": len(rows),
                "data": [_row_to_dict(r) for r in rows],
            }

    try:
        raw = await fetch_daily(symbol, outputsize="full" if days > 100 else "compact")
        parsed = parse_daily_series(raw, symbol)
        # Filter to requested range
        parsed = [p for p in parsed if p["timestamp"] >= cutoff]
    except ValueError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alpha Vantage error: {e}")

    # Upsert
    saved = 0
    for row in parsed:
        existing = await db.execute(
            select(StockPrice).where(
                and_(
                    StockPrice.symbol == row["symbol"],
                    StockPrice.timestamp == row["timestamp"],
                    StockPrice.interval == "1day",
                )
            )
        )
        if not existing.scalar():
            db.add(StockPrice(**row))
            saved += 1
    await db.commit()

    # Convert timestamps to strings for JSON
    serialized = [{**r, "timestamp": r["timestamp"].isoformat()} for r in parsed]
    return {
        "symbol": symbol,
        "interval": "1day",
        "source": "alpha_vantage",
        "count": len(serialized),
        "data": serialized,
    }


@router.get("/history/{symbol}")
async def get_history_from_db(
    symbol: str,
    interval: str = Query("1day"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Get stored history for a symbol from the database."""
    symbol = symbol.upper()
    stmt = (
        select(StockPrice)
        .where(and_(StockPrice.symbol == symbol, StockPrice.interval == interval))
        .order_by(desc(StockPrice.timestamp))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return {
        "symbol": symbol,
        "interval": interval,
        "count": len(rows),
        "data": [_row_to_dict(r) for r in reversed(rows)],
    }


def _row_to_dict(row: StockPrice) -> dict:
    return {
        "symbol": row.symbol,
        "timestamp": row.timestamp.isoformat() if isinstance(row.timestamp, datetime) else row.timestamp,
        "open": row.open,
        "high": row.high,
        "low": row.low,
        "close": row.close,
        "volume": row.volume,
        "interval": row.interval,
    }
