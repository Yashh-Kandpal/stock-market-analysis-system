"""
backfill.py

Runs on every server startup and fills in actual closing prices
for any prediction_log rows where actual_price is NULL.

Uses yfinance historical data — works regardless of when the server starts.
Safe to run multiple times (idempotent).
"""

import asyncio
import logging
from datetime import datetime, date, timedelta

import yfinance as yf
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from database import AsyncSessionLocal, PredictionLog

logger = logging.getLogger(__name__)


def _is_market_closed_for_date(d: date) -> bool:
    """
    Returns True if we can safely fetch actuals for this date.
    We consider a date "closed" if it's before today (IST ~UTC+5:30).
    Today's market may still be open so we skip it.
    """
    today_utc = datetime.utcnow().date()
    return d < today_utc


def _fetch_actual_close(symbol: str, target_date: date) -> float | None:
    """
    Fetch the actual closing price for a symbol on a specific date.
    Fetches a small window around the date to handle non-trading days.
    """
    start = target_date - timedelta(days=3)
    end   = target_date + timedelta(days=1)
    try:
        ticker = yf.Ticker(symbol)
        hist   = ticker.history(start=start.strftime("%Y-%m-%d"),
                                end=end.strftime("%Y-%m-%d"),
                                interval="1d")
        if hist.empty:
            return None

        # Find the row closest to (and on or before) target_date
        hist.index = hist.index.tz_localize(None) if hist.index.tz else hist.index
        hist_dates = [ts.date() for ts in hist.index]

        # Find exact match first
        for ts, row in zip(hist.index, hist.itertuples()):
            if ts.date() == target_date:
                return float(row.Close)

        # Fallback: last trading day on or before target_date
        candidates = [(ts.date(), row.Close) for ts, row in zip(hist.index, hist.itertuples())
                      if ts.date() <= target_date]
        if candidates:
            return float(candidates[-1][1])

        return None
    except Exception as e:
        logger.warning(f"Failed to fetch actual for {symbol} on {target_date}: {e}")
        return None


async def backfill_actuals():
    """
    Main backfill function. Called on server startup.
    Finds all pending predictions and fills in actuals.
    """
    async with AsyncSessionLocal() as db:
        try:
            # Find all rows missing actuals where prediction_date is in the past
            result = await db.execute(
                select(PredictionLog).where(
                    PredictionLog.actual_price == None  # noqa: E711
                )
            )
            pending = result.scalars().all()

            if not pending:
                logger.info("Backfill: no pending predictions to fill")
                return

            logger.info(f"Backfill: found {len(pending)} predictions needing actuals")

            filled = 0
            skipped = 0

            for row in pending:
                # Skip if market hasn't closed yet for this date
                if not _is_market_closed_for_date(row.prediction_date):
                    skipped += 1
                    continue

                # Fetch actual in a thread (yfinance is sync)
                actual_price = await asyncio.to_thread(
                    _fetch_actual_close, row.symbol, row.prediction_date
                )

                if actual_price is None:
                    logger.warning(f"Backfill: could not get actual for {row.symbol} on {row.prediction_date}")
                    continue

                # Determine actual direction vs prev_close
                actual_direction = None
                was_correct      = None
                if row.prev_close and row.prev_close > 0:
                    actual_direction = "UP" if actual_price > row.prev_close else "DOWN"
                    was_correct      = actual_direction == row.predicted_direction

                # Price error %
                price_error_pct = None
                if row.predicted_price and row.predicted_price > 0:
                    price_error_pct = abs(actual_price - row.predicted_price) / row.predicted_price * 100

                # Update row
                row.actual_price     = actual_price
                row.actual_direction = actual_direction
                row.was_correct      = was_correct
                row.price_error_pct  = round(price_error_pct, 4) if price_error_pct else None
                row.filled_at        = datetime.utcnow()
                filled += 1

            await db.commit()
            logger.info(f"Backfill complete: filled={filled}, skipped={skipped} (market not closed yet)")

        except Exception as e:
            logger.error(f"Backfill error: {e}")
            await db.rollback()
