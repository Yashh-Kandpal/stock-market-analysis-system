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
    ticker = yf.Ticker(symbol)
    
    # fast_info is more reliable for current price
    try:
        fi = ticker.fast_info
        price = float(fi.last_price) if fi.last_price else None
        prev_close = float(fi.previous_close) if fi.previous_close else None
    except Exception:
        price = None
        prev_close = None

    # fallback to history if fast_info fails
    if not price:
        hist = ticker.history(period="5d", interval="1d")
        if hist.empty:
            raise ValueError(f"No data found for symbol: {symbol}")
        # drop rows where Close is 0 or NaN
        hist = hist[hist["Close"] > 0].dropna(subset=["Close"])
        if hist.empty:
            raise ValueError(f"No valid price data for symbol: {symbol}")
        latest = hist.iloc[-1]
        prev   = hist.iloc[-2] if len(hist) > 1 else hist.iloc[-1]
        price      = float(latest["Close"])
        prev_close = float(prev["Close"])
        open_  = float(latest["Open"])
        high   = float(latest["High"])
        low    = float(latest["Low"])
        volume = float(latest["Volume"])
        day    = str(hist.index[-1].date())
    else:
        def _s(val):
            try:
                f = float(val)
                return 0.0 if (f != f) else f
            except Exception:
                return 0.0
        open_  = _s(getattr(fi, 'open',   None))
        high   = _s(getattr(fi, 'day_high', None))
        low    = _s(getattr(fi, 'day_low',  None))
        volume = _s(getattr(fi, 'three_month_average_volume', None))
        day    = str(datetime.utcnow().date())

    prev_close = prev_close or price
    change     = round(price - prev_close, 2)
    change_pct = round((change / prev_close * 100) if prev_close else 0.0, 2)

    return {
        "symbol":             symbol,
        "open":               open_,
        "high":               high,
        "low":                low,
        "price":              price,
        "volume":             volume,
        "latest_trading_day": day,
        "previous_close":     prev_close,
        "change":             change,
        "change_percent":     str(change_pct),
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
    results = []

    # Use yf.Search for partial/name queries
    try:
        search = yf.Search(keywords, max_results=15, news_count=0)
        quotes = getattr(search, 'quotes', []) or []
        for q in quotes:
            sym = q.get('symbol', '')
            if not sym:
                continue
            is_indian = (
                q.get('exchange') in ('NSI', 'BSE', 'NMS', 'NSE')
                or '.NS' in sym
                or '.BO' in sym
            )
            results.append({
                "symbol":      sym,
                "name":        q.get('longname') or q.get('shortname', sym),
                "type":        q.get('quoteType', ''),
                "region":      "India" if is_indian else q.get('exchange', ''),
                "currency":    q.get('currency', 'INR' if is_indian else ''),
                "match_score": "1.0000",
            })
        indian = [r for r in results if r['region'] == 'India']
        return indian or results[:5]
    except Exception:
        pass

    # Fallback: direct ticker lookup
    for suffix in ['.NS', '.BO']:
        sym = keywords.upper() + suffix
        try:
            t = yf.Ticker(sym)
            price = getattr(t.fast_info, 'last_price', None)
            if price and float(price) > 0:
                results.append({
                    "symbol":      sym,
                    "name":        sym,
                    "type":        "EQUITY",
                    "region":      "India",
                    "currency":    "INR",
                    "match_score": "1.0000",
                })
        except Exception:
            continue

    return results


# ── helpers ──────────────────────────────────────────────────────────────────

def _df_to_records(df: pd.DataFrame, symbol: str, interval: str) -> list[dict]:
    def safe(val):
        try:
            f = float(val)
            return 0.0 if (f != f) else f
        except (TypeError, ValueError):
            return 0.0

    records = []
    for ts, row in df.iterrows():
        naive_ts = ts.to_pydatetime().replace(tzinfo=None)
        # skip rows where close is 0 or missing
        if safe(row["Close"]) == 0.0:
            continue
        records.append({
            "symbol":    symbol,
            "timestamp": naive_ts,
            "open":      safe(row["Open"]),
            "high":      safe(row["High"]),
            "low":       safe(row["Low"]),
            "close":     safe(row["Close"]),
            "volume":    safe(row["Volume"]),
            "interval":  interval,
        })
    return records