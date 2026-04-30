import os
import httpx
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"
API_KEY = os.getenv("ALPHA_VANTAGE_KEY", "demo")

# Common Indian stocks on BSE/NSE — Alpha Vantage uses BSE: prefix for BSE-listed stocks
# and NSE: prefix for NSE. For TIME_SERIES endpoints, use symbol like "BSE:RELIANCE"
POPULAR_INDIAN_STOCKS = {
    "RELIANCE.BSE": "Reliance Industries",
    "TCS.BSE": "Tata Consultancy Services",
    "INFY.BSE": "Infosys",
    "HDFCBANK.BSE": "HDFC Bank",
    "ICICIBANK.BSE": "ICICI Bank",
    "SBIN.BSE": "State Bank of India",
    "WIPRO.BSE": "Wipro",
    "HINDUNILVR.BSE": "Hindustan Unilever",
    "ITC.BSE": "ITC Limited",
    "BAJFINANCE.BSE": "Bajaj Finance",
    "MARUTI.BSE": "Maruti Suzuki",
    "AXISBANK.BSE": "Axis Bank",
    "KOTAKBANK.BSE": "Kotak Mahindra Bank",
    "LT.BSE": "Larsen & Toubro",
    "TECHM.BSE": "Tech Mahindra",
}


async def fetch_intraday(symbol: str, interval: str = "5min", outputsize: str = "compact") -> dict:
    """Fetch intraday time series data for a stock."""
    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": API_KEY,
        "datatype": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(ALPHA_VANTAGE_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    if "Error Message" in data:
        raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
    if "Note" in data:
        logger.warning(f"Alpha Vantage rate limit note: {data['Note']}")
    if "Information" in data:
        raise ValueError(f"Alpha Vantage API limit reached: {data['Information']}")

    return data


async def fetch_daily(symbol: str, outputsize: str = "compact") -> dict:
    """Fetch daily time series data."""
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": outputsize,
        "apikey": API_KEY,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(ALPHA_VANTAGE_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    if "Error Message" in data:
        raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
    if "Information" in data:
        raise ValueError(f"Alpha Vantage API limit reached: {data['Information']}")

    return data


async def fetch_quote(symbol: str) -> dict:
    """Fetch latest global quote for a symbol."""
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": API_KEY,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(ALPHA_VANTAGE_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    if "Error Message" in data:
        raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
    if "Information" in data:
        raise ValueError(f"Alpha Vantage API limit reached: {data['Information']}")

    return data


async def search_symbol(keywords: str) -> dict:
    """Search for a stock symbol."""
    params = {
        "function": "SYMBOL_SEARCH",
        "keywords": keywords,
        "apikey": API_KEY,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(ALPHA_VANTAGE_BASE, params=params)
        resp.raise_for_status()
        return resp.json()


def parse_intraday_series(data: dict, symbol: str, interval: str) -> list[dict]:
    """Parse Alpha Vantage intraday response into list of OHLCV dicts."""
    key = f"Time Series ({interval})"
    series = data.get(key, {})
    result = []
    for ts_str, values in series.items():
        result.append({
            "symbol": symbol,
            "timestamp": datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S"),
            "open": float(values["1. open"]),
            "high": float(values["2. high"]),
            "low": float(values["3. low"]),
            "close": float(values["4. close"]),
            "volume": float(values["5. volume"]),
            "interval": interval,
        })
    return sorted(result, key=lambda x: x["timestamp"])


def parse_daily_series(data: dict, symbol: str) -> list[dict]:
    """Parse Alpha Vantage daily response into list of OHLCV dicts."""
    series = data.get("Time Series (Daily)", {})
    result = []
    for date_str, values in series.items():
        result.append({
            "symbol": symbol,
            "timestamp": datetime.strptime(date_str, "%Y-%m-%d"),
            "open": float(values["1. open"]),
            "high": float(values["2. high"]),
            "low": float(values["3. low"]),
            "close": float(values["4. close"]),
            "volume": float(values["5. volume"]),
            "interval": "1day",
        })
    return sorted(result, key=lambda x: x["timestamp"])


def parse_quote(data: dict) -> dict:
    """Parse global quote response."""
    q = data.get("Global Quote", {})
    if not q:
        return {}
    return {
        "symbol": q.get("01. symbol"),
        "open": float(q.get("02. open", 0)),
        "high": float(q.get("03. high", 0)),
        "low": float(q.get("04. low", 0)),
        "price": float(q.get("05. price", 0)),
        "volume": float(q.get("06. volume", 0)),
        "latest_trading_day": q.get("07. latest trading day"),
        "previous_close": float(q.get("08. previous close", 0)),
        "change": float(q.get("09. change", 0)),
        "change_percent": q.get("10. change percent", "0%").replace("%", ""),
    }
