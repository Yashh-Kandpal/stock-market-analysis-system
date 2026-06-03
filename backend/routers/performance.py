"""
Performance Router — /api/performance/...
Fully dynamic — new models appear automatically in all endpoints.
"""

import logging
from datetime import datetime, date, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, distinct

from database import get_db, PredictionLog

router = APIRouter()
logger = logging.getLogger(__name__)


# ── dynamic model discovery ───────────────────────────────────────────────────

async def _get_active_models(db: AsyncSession) -> list[str]:
    """Returns all model names that have at least one prediction logged."""
    result = await db.execute(select(distinct(PredictionLog.model)))
    models = [r[0] for r in result.fetchall()]
    # Sort in a consistent order, known models first
    priority = ['arima', 'prophet', 'linear', 'xgboost']
    known    = [m for m in priority if m in models]
    unknown  = sorted([m for m in models if m not in priority])
    return known + unknown


# ── helpers ───────────────────────────────────────────────────────────────────

def _row_to_dict(row: PredictionLog) -> dict:
    return {
        "id":                   row.id,
        "symbol":               row.symbol,
        "model":                row.model,
        "prediction_date":      str(row.prediction_date),
        "predicted_at":         row.predicted_at.isoformat() if row.predicted_at else None,
        "predicted_direction":  row.predicted_direction,
        "predicted_price":      row.predicted_price,
        "confidence_pct":       row.confidence_pct,
        "prev_close":           row.prev_close,
        "actual_price":         row.actual_price,
        "actual_direction":     row.actual_direction,
        "was_correct":          row.was_correct,
        "price_error_pct":      row.price_error_pct,
        "filled_at":            row.filled_at.isoformat() if row.filled_at else None,
        "pending":              row.actual_price is None,
    }


def _compute_stats(rows: list[PredictionLog]) -> dict:
    filled    = [r for r in rows if r.actual_price is not None]
    pending   = [r for r in rows if r.actual_price is None]
    correct   = [r for r in filled if r.was_correct]
    incorrect = [r for r in filled if r.was_correct is False]

    if not filled:
        return {
            "total_predictions":        len(rows),
            "filled_predictions":       0,
            "pending_predictions":      len(pending),
            "directional_accuracy_pct": None,
            "avg_price_error_pct":      None,
            "up_accuracy_pct":          None,
            "down_accuracy_pct":        None,
            "correct_count":            0,
            "incorrect_count":          0,
            "recent_10_accuracy_pct":   None,
        }

    up_preds     = [r for r in filled if r.predicted_direction == "UP"]
    down_preds   = [r for r in filled if r.predicted_direction == "DOWN"]
    up_correct   = [r for r in up_preds   if r.was_correct]
    down_correct = [r for r in down_preds if r.was_correct]

    price_errors = [r.price_error_pct for r in filled if r.price_error_pct is not None]
    avg_price_err = round(sum(price_errors) / len(price_errors), 3) if price_errors else None

    recent      = sorted(filled, key=lambda x: x.prediction_date, reverse=True)[:10]
    recent_acc  = round(sum(1 for r in recent if r.was_correct) / len(recent) * 100, 1) if recent else None

    return {
        "total_predictions":        len(rows),
        "filled_predictions":       len(filled),
        "pending_predictions":      len(pending),
        "directional_accuracy_pct": round(len(correct) / len(filled) * 100, 1),
        "avg_price_error_pct":      avg_price_err,
        "up_accuracy_pct":          round(len(up_correct)   / len(up_preds)   * 100, 1) if up_preds   else None,
        "down_accuracy_pct":        round(len(down_correct) / len(down_preds) * 100, 1) if down_preds else None,
        "correct_count":            len(correct),
        "incorrect_count":          len(incorrect),
        "recent_10_accuracy_pct":   recent_acc,
    }


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.get("/models")
async def get_active_models(db: AsyncSession = Depends(get_db)):
    """Returns all model names that have logged predictions."""
    models = await _get_active_models(db)
    return {"models": models}


@router.get("/summary")
async def get_performance_summary(
    days: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.utcnow().date() - timedelta(days=days)
    result = await db.execute(
        select(PredictionLog)
        .where(PredictionLog.prediction_date >= cutoff)
        .order_by(PredictionLog.prediction_date.desc())
    )
    all_rows = result.scalars().all()

    # Discover models dynamically
    models = list(set(r.model for r in all_rows)) or await _get_active_models(db)

    by_model  = defaultdict(list)
    by_symbol = defaultdict(list)
    for row in all_rows:
        by_model[row.model].append(row)
        by_symbol[row.symbol].append(row)

    model_stats = {}
    for model in models:
        rows  = by_model.get(model, [])
        stats = _compute_stats(rows)

        stock_accs = {}
        for sym, sym_rows in by_symbol.items():
            model_rows = [r for r in sym_rows if r.model == model and r.actual_price is not None]
            if len(model_rows) >= 3:
                acc = sum(1 for r in model_rows if r.was_correct) / len(model_rows) * 100
                stock_accs[sym] = round(acc, 1)

        best_stock  = max(stock_accs, key=stock_accs.get) if stock_accs else None
        worst_stock = min(stock_accs, key=stock_accs.get) if stock_accs else None

        model_stats[model] = {
            **stats,
            "best_stock":      best_stock,
            "best_stock_acc":  stock_accs.get(best_stock),
            "worst_stock":     worst_stock,
            "worst_stock_acc": stock_accs.get(worst_stock),
        }

    return {
        "days":            days,
        "models":          models,
        "overall":         _compute_stats(all_rows),
        "by_model":        model_stats,
        "tracked_symbols": list(set(r.symbol for r in all_rows)),
        "date_range": {
            "from": str(cutoff),
            "to":   str(datetime.utcnow().date()),
        },
    }


@router.get("/log")
async def get_prediction_log(
    symbol: str  | None = None,
    model:  str  | None = None,
    days:   int         = Query(30, ge=1, le=365),
    limit:  int         = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    cutoff  = datetime.utcnow().date() - timedelta(days=days)
    filters = [PredictionLog.prediction_date >= cutoff]
    if symbol:
        filters.append(PredictionLog.symbol == symbol.upper())
    if model:
        filters.append(PredictionLog.model == model.lower())

    result = await db.execute(
        select(PredictionLog).where(and_(*filters))
        .order_by(PredictionLog.prediction_date.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return {"count": len(rows), "rows": [_row_to_dict(r) for r in rows]}


@router.get("/symbol/{symbol}")
async def get_symbol_performance(
    symbol: str,
    days:   int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
):
    symbol = symbol.upper()
    cutoff = datetime.utcnow().date() - timedelta(days=days)
    result = await db.execute(
        select(PredictionLog).where(and_(
            PredictionLog.symbol          == symbol,
            PredictionLog.prediction_date >= cutoff,
        )).order_by(PredictionLog.prediction_date.desc())
    )
    rows   = result.scalars().all()
    models = list(set(r.model for r in rows)) or await _get_active_models(db)

    by_model = defaultdict(list)
    for row in rows:
        by_model[row.model].append(row)

    return {
        "symbol":   symbol,
        "days":     days,
        "models":   models,
        "by_model": {m: _compute_stats(by_model.get(m, [])) for m in models},
        "log":      [_row_to_dict(r) for r in rows[:30]],
    }


@router.get("/calibration")
async def get_calibration(
    days: int = Query(60, ge=14, le=365),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.utcnow().date() - timedelta(days=days)
    result = await db.execute(
        select(PredictionLog).where(and_(
            PredictionLog.prediction_date >= cutoff,
            PredictionLog.actual_price    != None,   # noqa: E711
            PredictionLog.confidence_pct  != None,   # noqa: E711
        ))
    )
    rows   = result.scalars().all()
    models = list(set(r.model for r in rows))

    buckets = [
        ("50-55%", 50, 55), ("55-60%", 55, 60),
        ("60-65%", 60, 65), ("65-70%", 65, 70), ("70%+", 70, 100),
    ]

    # Per-model calibration
    all_calibration = {}
    for model in (models or ["all"]):
        model_rows = [r for r in rows if r.model == model] if models else rows
        calibration = []
        for label, low, high in buckets:
            bucket = [r for r in model_rows if r.confidence_pct and low <= r.confidence_pct < high]
            if not bucket:
                continue
            actual_acc = round(sum(1 for r in bucket if r.was_correct) / len(bucket) * 100, 1)
            calibration.append({
                "bucket":              label,
                "mid_confidence":      round((low + high) / 2, 1),
                "actual_accuracy_pct": actual_acc,
                "count":               len(bucket),
                "well_calibrated":     abs(actual_acc - (low + high) / 2) < 8,
            })
        all_calibration[model] = calibration

    return {
        "days":        days,
        "total_rows":  len(rows),
        "models":      models,
        "calibration": all_calibration,
    }
