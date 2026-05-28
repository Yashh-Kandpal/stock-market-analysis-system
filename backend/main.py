from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
from routers import analysis 
from database import create_tables
from routers import stocks, watchlist, ml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — creating tables...")
    await create_tables()
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Indian Stock Market Analysis API",
    description="Real-time stock data fetcher for Indian markets via Alpha Vantage",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])


@app.get("/")
async def root():
    return {"message": "Indian Stock Market Analysis API", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(ml.router, prefix="/api/ml", tags=["ml"])