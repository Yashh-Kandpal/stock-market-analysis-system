from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database import get_db, WatchlistItem

router = APIRouter()


class WatchlistAdd(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    exchange: Optional[str] = "BSE"
    notes: Optional[str] = None


class WatchlistUpdate(BaseModel):
    company_name: Optional[str] = None
    notes: Optional[str] = None


@router.get("/")
async def get_watchlist(db: AsyncSession = Depends(get_db)):
    """Get all watchlist items."""
    result = await db.execute(select(WatchlistItem).order_by(WatchlistItem.added_at.desc()))
    items = result.scalars().all()
    return [_item_to_dict(i) for i in items]


@router.post("/")
async def add_to_watchlist(body: WatchlistAdd, db: AsyncSession = Depends(get_db)):
    """Add a stock to the watchlist."""
    symbol = body.symbol.upper()
    # Check duplicate
    existing = await db.execute(select(WatchlistItem).where(WatchlistItem.symbol == symbol))
    if existing.scalar():
        raise HTTPException(status_code=409, detail=f"{symbol} is already in watchlist")

    item = WatchlistItem(
        symbol=symbol,
        company_name=body.company_name,
        exchange=body.exchange,
        notes=body.notes,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _item_to_dict(item)


@router.delete("/{symbol}")
async def remove_from_watchlist(symbol: str, db: AsyncSession = Depends(get_db)):
    """Remove a stock from the watchlist."""
    symbol = symbol.upper()
    result = await db.execute(delete(WatchlistItem).where(WatchlistItem.symbol == symbol))
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"{symbol} not found in watchlist")
    return {"message": f"{symbol} removed from watchlist"}


@router.patch("/{symbol}")
async def update_watchlist_item(symbol: str, body: WatchlistUpdate, db: AsyncSession = Depends(get_db)):
    """Update notes or company name for a watchlist item."""
    symbol = symbol.upper()
    result = await db.execute(select(WatchlistItem).where(WatchlistItem.symbol == symbol))
    item = result.scalar()
    if not item:
        raise HTTPException(status_code=404, detail=f"{symbol} not found in watchlist")
    if body.company_name is not None:
        item.company_name = body.company_name
    if body.notes is not None:
        item.notes = body.notes
    await db.commit()
    await db.refresh(item)
    return _item_to_dict(item)


def _item_to_dict(item: WatchlistItem) -> dict:
    return {
        "id": item.id,
        "symbol": item.symbol,
        "company_name": item.company_name,
        "exchange": item.exchange,
        "notes": item.notes,
        "added_at": item.added_at.isoformat() if isinstance(item.added_at, datetime) else item.added_at,
    }
