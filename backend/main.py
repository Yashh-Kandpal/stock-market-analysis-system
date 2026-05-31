from dotenv import load_dotenv
load_dotenv()

import warnings
import logging

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logging.getLogger('statsmodels').setLevel(logging.ERROR)
logging.getLogger('prophet').setLevel(logging.ERROR)
logging.getLogger('cmdstanpy').setLevel(logging.ERROR)
logging.getLogger('yfinance').setLevel(logging.ERROR)
logging.getLogger('matplotlib').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)   # ← move this here

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import create_tables
from routers import stocks, watchlist, analysis, ml
from routers.auth import router as auth_router
from routers.search_history import router as search_history_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — creating tables...")
    await create_tables()
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Indian Stock Market Analysis API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router,           prefix="/api/auth",           tags=["auth"])
app.include_router(stocks.router,         prefix="/api/stocks",         tags=["stocks"])
app.include_router(watchlist.router,      prefix="/api/watchlist",      tags=["watchlist"])
app.include_router(analysis.router,       prefix="/api/analysis",       tags=["analysis"])
app.include_router(ml.router,             prefix="/api/ml",             tags=["ml"])
app.include_router(search_history_router, prefix="/api/search-history", tags=["search-history"])


@app.get("/")
async def root():
    return {"message": "Indian Stock Market Analysis API v2", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
