import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import (
    Column, String, Float, DateTime, Integer,
    Text, UniqueConstraint, ForeignKey, Boolean, Date
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

class PredictionLog(Base):
    __tablename__ = "prediction_log"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    symbol             = Column(String(20),  nullable=False, index=True)
    model              = Column(String(20),  nullable=False)  # arima/xgboost/linear/prophet
    prediction_date    = Column(Date,        nullable=False, index=True)  # the day being predicted
    predicted_at       = Column(DateTime,    default=datetime.utcnow)

    # Prediction values (locked at prediction time)
    predicted_direction = Column(String(4),  nullable=False)   # UP / DOWN
    predicted_price     = Column(Float,      nullable=True)
    confidence_pct      = Column(Float,      nullable=True)
    prev_close          = Column(Float,      nullable=True)    # price when prediction was made

    # Actuals (filled in after market close via backfill)
    actual_price        = Column(Float,      nullable=True)
    actual_direction    = Column(String(4),  nullable=True)
    was_correct         = Column(Boolean,    nullable=True)
    price_error_pct     = Column(Float,      nullable=True)    # abs % error on price
    filled_at           = Column(DateTime,   nullable=True)

    __table_args__ = (
        UniqueConstraint("symbol", "model", "prediction_date", name="uq_pred_log"),
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