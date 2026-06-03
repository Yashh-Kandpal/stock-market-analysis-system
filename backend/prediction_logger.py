"""
prediction_logger.py

Called from ml.py router after each successful prediction.
Saves the prediction to prediction_log if one doesn't already exist for today.

Design principles:
- Never overwrites an existing prediction for the same (symbol, model, date)
- Silently fails — a logging error should never break the prediction response
- Uses next trading day as prediction_date (we predict what tomorrow will do)
"""

import logging
from datetime import datetime, date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import PredictionLog

logger = logging.getLogger(__name__)


def _next_trading_day(from_date: date) -> date:
    """Returns the next weekday (Mon-Fri) from a given date."""
    d = from_date + timedelta(days=1)
    while d.weekday() >= 5:  # 5=Sat, 6=Sun
        d += timedelta(days=1)
    return d


async def log_prediction(
    db:          AsyncSession,
    symbol:      str,
    model:       str,
    result:      dict,
    prev_close:  float | None = None,
):
    """
    Log a prediction to the database.
    Called after each successful ML model run.

    result dict should contain:
      prediction.direction      → 'UP' or 'DOWN'
      prediction.predicted_price (optional, model-specific key)
      prediction.confidence_pct  (optional)
    """
    try:
        prediction_date = _next_trading_day(datetime.utcnow().date())

        # Extract prediction details — handle different model response shapes
        pred = result.get("prediction", {})
        direction      = pred.get("direction") or pred.get("predicted_direction")
        predicted_price = (
            pred.get("predicted_price") or
            pred.get("pred_5d_price") or        # XGBoost 5-day
            result.get("forecast", [{}])[0].get("predicted")  # ARIMA/Prophet first forecast day
        )
        confidence = pred.get("confidence_pct") or pred.get("prob_up_pct")

        if not direction:
            return  # can't log without a direction

        # Upsert — insert only if no prediction exists for this (symbol, model, date)
        stmt = pg_insert(PredictionLog).values(
            symbol              = symbol,
            model               = model,
            prediction_date     = prediction_date,
            predicted_at        = datetime.utcnow(),
            predicted_direction = direction,
            predicted_price     = float(predicted_price) if predicted_price else None,
            confidence_pct      = float(confidence) if confidence else None,
            prev_close          = float(prev_close) if prev_close else None,
        ).on_conflict_do_nothing(
            index_elements=["symbol", "model", "prediction_date"]
        )
        await db.execute(stmt)
        await db.commit()
        logger.debug(f"Logged prediction: {symbol} {model} {direction} for {prediction_date}")

    except Exception as e:
        logger.warning(f"Failed to log prediction for {symbol}/{model}: {e}")
        # Never re-raise — logging failure should not break the prediction response
        try:
            await db.rollback()
        except Exception:
            pass
