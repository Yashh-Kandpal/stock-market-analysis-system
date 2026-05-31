"""
Search History Router — /api/search-history/...
Saves and retrieves per-user search history.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc
from pydantic import BaseModel
from datetime import datetime

from database import get_db, SearchHistory, User
from auth import get_current_user

router = APIRouter()


class SearchRecord(BaseModel):
    query:         str
    results_count: int = 0


@router.get("/")
async def get_search_history(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent search history for the current user."""
    result = await db.execute(
        select(SearchHistory)
        .where(SearchHistory.user_id == current_user.id)
        .order_by(desc(SearchHistory.searched_at))
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id":            r.id,
            "query":         r.query,
            "results_count": r.results_count,
            "searched_at":   r.searched_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/")
async def save_search(
    body: SearchRecord,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a search query to history. Deduplicates within last 10 entries."""
    # Check if same query exists in last 10 — avoid duplicates from debounce
    recent = await db.execute(
        select(SearchHistory)
        .where(SearchHistory.user_id == current_user.id)
        .order_by(desc(SearchHistory.searched_at))
        .limit(10)
    )
    recent_queries = [r.query.lower() for r in recent.scalars().all()]
    if body.query.lower() in recent_queries:
        return {"message": "duplicate, not saved"}

    entry = SearchHistory(
        user_id       = current_user.id,
        query         = body.query,
        results_count = body.results_count,
    )
    db.add(entry)
    await db.commit()
    return {"message": "saved"}


@router.delete("/")
async def clear_search_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear all search history for the current user."""
    await db.execute(
        delete(SearchHistory).where(SearchHistory.user_id == current_user.id)
    )
    await db.commit()
    return {"message": "Search history cleared"}


@router.delete("/{entry_id}")
async def delete_search_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single search history entry."""
    await db.execute(
        delete(SearchHistory).where(
            SearchHistory.id      == entry_id,
            SearchHistory.user_id == current_user.id,
        )
    )
    await db.commit()
    return {"message": "Entry deleted"}
