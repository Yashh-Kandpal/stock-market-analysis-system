import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import (
    Column, String, Float, DateTime, Integer,
    Text, UniqueConstraint, ForeignKey, Boolean
)
from datetime import datetime

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://stockuser:stockpass@localhost:5432/stockdb"
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    google_id  = Column(String(128), unique=True, nullable=False, index=True)
    email      = Column(String(255), unique=True, nullable=False)
    name       = Column(String(255))
    avatar_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    is_active  = Column(Boolean, default=True)


class StockPrice(Base):
    __tablename__ = "stock_prices"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    symbol     = Column(String(20), nullable=False, index=True)
    open       = Column(Float)
    high       = Column(Float)
    low        = Column(Float)
    close      = Column(Float)
    volume     = Column(Float)
    timestamp  = Column(DateTime, nullable=False, index=True)
    interval   = Column(String(10), default="5min")
    fetched_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", "interval", name="uq_symbol_ts_interval"),
    )


class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol       = Column(String(20), nullable=False)
    company_name = Column(String(100))
    exchange     = Column(String(10), default="NSE")
    added_at     = Column(DateTime, default=datetime.utcnow)
    notes        = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_user_symbol"),
    )


class SearchHistory(Base):
    __tablename__ = "search_history"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    query         = Column(String(255), nullable=False)
    results_count = Column(Integer, default=0)
    searched_at   = Column(DateTime, default=datetime.utcnow)


class MLResult(Base):
    __tablename__ = "ml_results"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    symbol     = Column(String(20), nullable=False, index=True)
    model      = Column(String(50), nullable=False)
    days       = Column(Integer, nullable=False)
    result     = Column(Text, nullable=False)
    trained_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "model", "days", name="uq_ml_result"),
    )


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()