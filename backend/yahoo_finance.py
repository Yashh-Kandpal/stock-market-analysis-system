import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Yahoo Finance uses .NS suffix for NSE, .BO suffix for BSE
# Example: RELIANCE.NS, TCS.NS, INFY.NS
POPULAR_INDIAN_STOCKS = {
    "RELIANCE.NS": "Reliance Industries",
    "TCS.NS": "Tata Consultancy Services",
    "INFY.NS": "Infosys",
    "HDFCBANK.NS": "HDFC Bank",
    "ICICIBANK.NS": "ICICI Bank",
    "SBIN.NS": "State Bank of India",
    "WIPRO.NS": "Wipro",
    "HINDUNILVR.NS": "Hindustan Unilever",
    "ITC.NS": "ITC Limited",
    "BAJFINANCE.NS": "Bajaj Finance",
    "MARUTI.NS": "Maruti Suzuki",
    "AXISBANK.NS": "Axis Bank",
    "KOTAKBANK.NS": "Kotak Mahindra Bank",
    "LT.NS": "Larsen & Toubro",
    "TECHM.NS": "Tech Mahindra",
}

# Map our interval strings to yfinance interval strings
INTERVAL_MAP = {
    "1min":  "1m",
    "5min":  "5m",
    "15min": "15m",
    "30min": "30m",
    "60min": "60m",
    "1day":  "1d",
}

# yfinance requires a matching period for intraday intervals
INTRADAY_PERIOD = {
    "1m":  "1d",
    "5m":  "5d",
    "15m": "5d",
    "30m": "1mo",
    "60m": "1mo",
}


def fetch_quote(symbol: str) -> dict:
    """Fetch latest quote using yfinance fast_info."""
    ticker = yf.Ticker(symbol)
    info = ticker.fast_info
    hist = ticker.history(period="2d", interval="1d")

    if hist.empty:
        raise ValueError(f"No data found for symbol: {symbol}")

    latest = hist.iloc[-1]
    prev = hist.iloc[-2] if len(hist) > 1 else hist.iloc[-1]

    price = float(latest["Close"])
    prev_close = float(prev["Close"])
    change = price - prev_close
    change_pct = (change / prev_close * 100) if prev_close else 0.0

    return {
        "symbol": symbol,
        "open":           float(latest["Open"]),
        "high":           float(latest["High"]),
        "low":            float(latest["Low"]),
        "price":          price,
        "volume":         float(latest["Volume"]),
        "latest_trading_day": str(hist.index[-1].date()),
        "previous_close": prev_close,
        "change":         round(change, 2),
        "change_percent": str(round(change_pct, 2)),
    }


def fetch_intraday(symbol: str, interval: str = "5min") -> list[dict]:
    """Fetch intraday OHLCV using yfinance."""
    yf_interval = INTERVAL_MAP.get(interval, "5m")
    period = INTRADAY_PERIOD.get(yf_interval, "5d")

    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period, interval=yf_interval)

    if hist.empty:
        raise ValueError(f"No intraday data for {symbol}")

    return _df_to_records(hist, symbol, interval)


def fetch_daily(symbol: str, days: int = 30) -> list[dict]:
    """Fetch daily OHLCV using yfinance."""
    start = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    ticker = yf.Ticker(symbol)
    hist = ticker.history(start=start, interval="1d")

    if hist.empty:
        raise ValueError(f"No daily data for {symbol}")

    return _df_to_records(hist, symbol, "1day")


def search_symbol(keywords: str) -> list[dict]:
    """
    Search for tickers using yfinance search.
    Filters results to Indian exchanges (NSE/BSE).
    """
    results = yf.Search(keywords, max_results=10)
    quotes = results.quotes if hasattr(results, "quotes") else []

    indian = [
        {
            "symbol":       q.get("symbol", ""),
            "name":         q.get("longname") or q.get("shortname", ""),
            "type":         q.get("quoteType", ""),
            "region":       "India" if q.get("exchange") in ("NSI", "BSE") else q.get("exchange", ""),
            "currency":     q.get("currency", "INR"),
            "match_score":  "1.0000",
        }
        for q in quotes
        if q.get("exchange") in ("NSI", "BSE") or ".NS" in q.get("symbol", "") or ".BO" in q.get("symbol", "")
    ]

    # Fall back to all results if no Indian ones found
    return indian or [
        {
            "symbol":      q.get("symbol", ""),
            "name":        q.get("longname") or q.get("shortname", ""),
            "type":        q.get("quoteType", ""),
            "region":      q.get("exchange", ""),
            "currency":    q.get("currency", ""),
            "match_score": "1.0000",
        }
        for q in quotes[:5]
    ]


# ── helpers ──────────────────────────────────────────────────────────────────

def _df_to_records(df: pd.DataFrame, symbol: str, interval: str) -> list[dict]:
    """Convert a yfinance DataFrame to list of OHLCV dicts."""
    records = []
    for ts, row in df.iterrows():
        # yfinance index is timezone-aware; strip tz for DB storage
        naive_ts = ts.to_pydatetime().replace(tzinfo=None)
        records.append({
            "symbol":    symbol,
            "timestamp": naive_ts,
            "open":      float(row["Open"]),
            "high":      float(row["High"]),
            "low":       float(row["Low"]),
            "close":     float(row["Close"]),
            "volume":    float(row["Volume"]),
            "interval":  interval,
        })
    return records