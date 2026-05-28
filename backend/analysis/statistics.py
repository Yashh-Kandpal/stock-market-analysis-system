"""
Statistical analysis engine for stock price data.
All functions accept a list of OHLCV dicts (from DB or yfinance)
and return plain dicts/lists — no pandas dependency leaking into routers.
"""

import numpy as np
import pandas as pd
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _to_series(records: list[dict], field: str = "close") -> pd.Series:
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").set_index("timestamp")
    return df[field].astype(float)


def _safe(val) -> float | None:
    """Convert numpy scalars to Python float; return None for NaN/inf."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if (np.isnan(f) or np.isinf(f)) else round(f, 4)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 1. Moving Averages
# ─────────────────────────────────────────────────────────────────────────────

def moving_averages(records: list[dict], windows: list[int] = None) -> dict:
    """
    SMA and EMA for configurable windows.
    Returns per-candle series + latest values + crossover signals.
    """
    if windows is None:
        windows = [9, 20, 50, 200]

    close = _to_series(records)
    result: dict[str, Any] = {"windows": windows, "series": {}, "latest": {}, "signals": []}

    sma_latest: dict[int, float] = {}
    ema_latest: dict[int, float] = {}

    for w in windows:
        if len(close) < w:
            continue
        sma = close.rolling(w).mean()
        ema = close.ewm(span=w, adjust=False).mean()

        result["series"][f"sma_{w}"] = [
            {"timestamp": str(ts), "value": _safe(v)}
            for ts, v in sma.items() if not pd.isna(v)
        ]
        result["series"][f"ema_{w}"] = [
            {"timestamp": str(ts), "value": _safe(v)}
            for ts, v in ema.items() if not pd.isna(v)
        ]

        sma_latest[w] = _safe(sma.iloc[-1])
        ema_latest[w] = _safe(ema.iloc[-1])
        result["latest"][f"sma_{w}"] = sma_latest[w]
        result["latest"][f"ema_{w}"] = ema_latest[w]

    # Golden / Death cross detection (20 vs 50)
    if 20 in windows and 50 in windows and len(close) >= 50:
        sma20 = close.rolling(20).mean()
        sma50 = close.rolling(50).mean()
        diff = sma20 - sma50
        prev_diff = diff.shift(1)
        # Golden cross: sma20 crosses above sma50
        golden = diff[(diff > 0) & (prev_diff <= 0)]
        death  = diff[(diff < 0) & (prev_diff >= 0)]
        if not golden.empty:
            result["signals"].append({
                "type": "golden_cross",
                "date": str(golden.index[-1].date()),
                "description": "SMA-20 crossed above SMA-50 — bullish signal",
            })
        if not death.empty:
            result["signals"].append({
                "type": "death_cross",
                "date": str(death.index[-1].date()),
                "description": "SMA-20 crossed below SMA-50 — bearish signal",
            })

    return result


# ─────────────────────────────────────────────────────────────────────────────
# 2. Volatility
# ─────────────────────────────────────────────────────────────────────────────

def volatility(records: list[dict], window: int = 20) -> dict:
    """
    Rolling annualised volatility (std of log returns).
    Also returns ATR (Average True Range) and Bollinger Bands.
    """
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").set_index("timestamp")
    close = df["close"].astype(float)
    high  = df["high"].astype(float)
    low   = df["low"].astype(float)

    # Log returns
    log_ret = np.log(close / close.shift(1))

    # Rolling annualised volatility (252 trading days)
    roll_vol = log_ret.rolling(window).std() * np.sqrt(252) * 100  # in %

    # ATR
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(window).mean()

    # Bollinger Bands
    sma   = close.rolling(window).mean()
    std   = close.rolling(window).std()
    upper = sma + 2 * std
    lower = sma - 2 * std

    # %B  = (close - lower) / (upper - lower)
    pct_b = (close - lower) / (upper - lower)

    latest_close = float(close.iloc[-1])
    latest_upper = _safe(upper.iloc[-1])
    latest_lower = _safe(lower.iloc[-1])

    return {
        "window": window,
        "rolling_volatility_pct": [
            {"timestamp": str(ts), "value": _safe(v)}
            for ts, v in roll_vol.items() if not pd.isna(v)
        ],
        "bollinger_bands": [
            {
                "timestamp": str(ts),
                "upper": _safe(upper.loc[ts]),
                "mid":   _safe(sma.loc[ts]),
                "lower": _safe(lower.loc[ts]),
                "close": _safe(close.loc[ts]),
            }
            for ts in sma.dropna().index
        ],
        "atr_series": [
            {"timestamp": str(ts), "value": _safe(v)}
            for ts, v in atr.items() if not pd.isna(v)
        ],
        "latest": {
            "annualised_volatility_pct": _safe(roll_vol.iloc[-1]),
            "atr":                       _safe(atr.iloc[-1]),
            "bollinger_upper":           latest_upper,
            "bollinger_lower":           latest_lower,
            "bollinger_mid":             _safe(sma.iloc[-1]),
            "pct_b":                     _safe(pct_b.iloc[-1]),
            "bandwidth":                 _safe((upper.iloc[-1] - lower.iloc[-1]) / sma.iloc[-1] * 100) if _safe(sma.iloc[-1]) else None,
        },
        "interpretation": {
            "position": (
                "above_upper_band" if latest_close > (latest_upper or 0)
                else "below_lower_band" if latest_close < (latest_lower or 0)
                else "within_bands"
            ),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Z-Score Anomaly Detection
# ─────────────────────────────────────────────────────────────────────────────

def zscore_anomalies(
    records: list[dict],
    window: int = 20,
    threshold: float = 2.5,
    field: str = "close",
) -> dict:
    """
    Rolling Z-score on price and on volume.
    Flags candles where |z| > threshold as anomalies.
    """
    close  = _to_series(records, "close")
    volume = _to_series(records, "volume")

    def _rolling_z(series: pd.Series) -> pd.Series:
        mean = series.rolling(window).mean()
        std  = series.rolling(window).std()
        return (series - mean) / std.replace(0, np.nan)

    price_z  = _rolling_z(close)
    volume_z = _rolling_z(volume)

    price_anomalies  = price_z[price_z.abs() > threshold]
    volume_anomalies = volume_z[volume_z.abs() > threshold]

    def _fmt_anomaly(ts, z, price_val, vol_val, kind):
        return {
            "timestamp": str(ts),
            "z_score":   round(float(z), 3),
            "direction": "spike_up" if z > 0 else "spike_down",
            "kind":      kind,
            "close":     _safe(price_val),
            "volume":    _safe(vol_val),
        }

    price_anom_list = [
        _fmt_anomaly(ts, z, close.loc[ts], volume.loc[ts], "price")
        for ts, z in price_anomalies.items()
    ]
    volume_anom_list = [
        _fmt_anomaly(ts, z, close.loc[ts], volume.loc[ts], "volume")
        for ts, z in volume_anomalies.items()
    ]

    # Combined: candles that are anomalous in both price AND volume
    both_idx = set(price_anomalies.index) & set(volume_anomalies.index)
    combined = [
        {
            "timestamp":       str(ts),
            "price_z":         round(float(price_z.loc[ts]), 3),
            "volume_z":        round(float(volume_z.loc[ts]), 3),
            "close":           _safe(close.loc[ts]),
            "significance":    "high" if abs(price_z.loc[ts]) > threshold * 1.5 else "moderate",
        }
        for ts in sorted(both_idx)
    ]

    return {
        "window":    window,
        "threshold": threshold,
        "zscore_series": [
            {
                "timestamp": str(ts),
                "price_z":   _safe(price_z.loc[ts]),
                "volume_z":  _safe(volume_z.loc[ts]),
            }
            for ts in close.index if not pd.isna(price_z.loc[ts])
        ],
        "price_anomalies":  price_anom_list,
        "volume_anomalies": volume_anom_list,
        "combined_anomalies": combined,
        "summary": {
            "total_candles":        len(close),
            "price_anomaly_count":  len(price_anom_list),
            "volume_anomaly_count": len(volume_anom_list),
            "combined_count":       len(combined),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. RSI (Relative Strength Index)
# ─────────────────────────────────────────────────────────────────────────────

def rsi(records: list[dict], period: int = 14) -> dict:
    """RSI with overbought/oversold signals."""
    close = _to_series(records)
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

    rs       = avg_gain / avg_loss.replace(0, np.nan)
    rsi_vals = 100 - (100 / (1 + rs))

    latest = _safe(rsi_vals.iloc[-1])
    signal = (
        "overbought" if (latest or 0) > 70
        else "oversold" if (latest or 0) < 30
        else "neutral"
    )

    return {
        "period": period,
        "series": [
            {"timestamp": str(ts), "value": _safe(v)}
            for ts, v in rsi_vals.items() if not pd.isna(v)
        ],
        "latest": latest,
        "signal": signal,
        "levels": {"overbought": 70, "oversold": 30},
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. MACD
# ─────────────────────────────────────────────────────────────────────────────

def macd(
    records: list[dict],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> dict:
    """MACD line, signal line, histogram, and crossover events."""
    close = _to_series(records)

    ema_fast   = close.ewm(span=fast,   adjust=False).mean()
    ema_slow   = close.ewm(span=slow,   adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram  = macd_line - signal_line

    # Crossovers
    above = macd_line > signal_line
    cross_up   = above & ~above.shift(1).fillna(False)
    cross_down = ~above & above.shift(1).fillna(False)

    crossovers = []
    for ts in macd_line[cross_up].index:
        crossovers.append({"timestamp": str(ts), "type": "bullish_crossover"})
    for ts in macd_line[cross_down].index:
        crossovers.append({"timestamp": str(ts), "type": "bearish_crossover"})
    crossovers.sort(key=lambda x: x["timestamp"])

    latest_hist = _safe(histogram.iloc[-1])

    return {
        "params": {"fast": fast, "slow": slow, "signal": signal_period},
        "series": [
            {
                "timestamp":  str(ts),
                "macd":       _safe(macd_line.loc[ts]),
                "signal":     _safe(signal_line.loc[ts]),
                "histogram":  _safe(histogram.loc[ts]),
            }
            for ts in macd_line.dropna().index
        ],
        "latest": {
            "macd":      _safe(macd_line.iloc[-1]),
            "signal":    _safe(signal_line.iloc[-1]),
            "histogram": latest_hist,
        },
        "trend":      "bullish" if (latest_hist or 0) > 0 else "bearish",
        "crossovers": crossovers[-10:],  # last 10 crossovers
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. Support & Resistance Levels
# ─────────────────────────────────────────────────────────────────────────────

def support_resistance(records: list[dict], window: int = 10) -> dict:
    """
    Pivot-point based support & resistance using rolling local extrema.
    Also computes classic daily pivot points from last candle.
    """
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    close = df["close"].astype(float)
    high  = df["high"].astype(float)
    low   = df["low"].astype(float)

    # Local maxima / minima
    resistance_levels = []
    support_levels    = []
    for i in range(window, len(close) - window):
        slice_high = high.iloc[i - window: i + window + 1]
        slice_low  = low.iloc[i - window: i + window + 1]
        if high.iloc[i] == slice_high.max():
            resistance_levels.append({
                "price":     _safe(high.iloc[i]),
                "timestamp": str(df["timestamp"].iloc[i]),
                "strength":  "strong" if high.iloc[i] == high.rolling(50).max().iloc[i] else "moderate",
            })
        if low.iloc[i] == slice_low.min():
            support_levels.append({
                "price":     _safe(low.iloc[i]),
                "timestamp": str(df["timestamp"].iloc[i]),
                "strength":  "strong" if low.iloc[i] == low.rolling(50).min().iloc[i] else "moderate",
            })

    # Classic pivot points from last full candle
    last_high  = float(high.iloc[-1])
    last_low   = float(low.iloc[-1])
    last_close = float(close.iloc[-1])
    pivot = (last_high + last_low + last_close) / 3
    r1 = 2 * pivot - last_low
    s1 = 2 * pivot - last_high
    r2 = pivot + (last_high - last_low)
    s2 = pivot - (last_high - last_low)
    r3 = last_high + 2 * (pivot - last_low)
    s3 = last_low  - 2 * (last_high - pivot)

    return {
        "pivot_points": {
            "pivot": _safe(pivot),
            "r1": _safe(r1), "r2": _safe(r2), "r3": _safe(r3),
            "s1": _safe(s1), "s2": _safe(s2), "s3": _safe(s3),
        },
        "resistance_levels": resistance_levels[-8:],
        "support_levels":    support_levels[-8:],
        "current_price":     _safe(last_close),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7. Returns Analysis
# ─────────────────────────────────────────────────────────────────────────────

def returns_analysis(records: list[dict]) -> dict:
    """
    Daily/periodic returns distribution, Sharpe ratio estimate,
    max drawdown, skewness, kurtosis.
    """
    close    = _to_series(records)
    log_ret  = np.log(close / close.shift(1)).dropna()
    pct_ret  = close.pct_change().dropna()

    # Drawdown
    running_max = close.cummax()
    drawdown    = (close - running_max) / running_max * 100
    max_dd      = float(drawdown.min())
    max_dd_date = str(drawdown.idxmin().date()) if not drawdown.empty else None

    # Annualised Sharpe (assume risk-free = 6% for India)
    rf_daily = 0.06 / 252
    excess   = pct_ret - rf_daily
    sharpe   = _safe(excess.mean() / excess.std() * np.sqrt(252)) if excess.std() > 0 else None

    # Streaks
    up_days   = int((pct_ret > 0).sum())
    down_days = int((pct_ret < 0).sum())

    return {
        "total_return_pct":    _safe((close.iloc[-1] / close.iloc[0] - 1) * 100),
        "annualised_return_pct": _safe(((close.iloc[-1] / close.iloc[0]) ** (252 / max(len(close), 1)) - 1) * 100),
        "max_drawdown_pct":    round(max_dd, 4),
        "max_drawdown_date":   max_dd_date,
        "sharpe_ratio":        sharpe,
        "mean_daily_return_pct": _safe(pct_ret.mean() * 100),
        "std_daily_return_pct":  _safe(pct_ret.std() * 100),
        "skewness":            _safe(float(pct_ret.skew())),
        "kurtosis":            _safe(float(pct_ret.kurt())),
        "up_days":             up_days,
        "down_days":           down_days,
        "win_rate_pct":        _safe(up_days / max(up_days + down_days, 1) * 100),
        "returns_series": [
            {"timestamp": str(ts), "pct_return": _safe(v * 100)}
            for ts, v in pct_ret.items()
        ],
        "drawdown_series": [
            {"timestamp": str(ts), "drawdown_pct": _safe(v)}
            for ts, v in drawdown.items()
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8. Full Summary (single call for the UI overview card)
# ─────────────────────────────────────────────────────────────────────────────

def full_summary(records: list[dict], ma_windows: list[int] = None) -> dict:
    """Lightweight summary — only latest values, no series arrays."""
    if len(records) < 5:
        return {"error": "Not enough data for analysis"}

    close  = _to_series(records)
    volume = _to_series(records, "volume")

    ma_windows = ma_windows or [20, 50]
    ma_vals: dict = {}
    for w in ma_windows:
        if len(close) >= w:
            ma_vals[f"sma_{w}"] = _safe(close.rolling(w).mean().iloc[-1])
            ma_vals[f"ema_{w}"] = _safe(close.ewm(span=w, adjust=False).mean().iloc[-1])

    log_ret = np.log(close / close.shift(1)).dropna()
    vol_pct = _safe(log_ret.rolling(20).std().iloc[-1] * np.sqrt(252) * 100) if len(log_ret) >= 20 else None

    delta = close.diff()
    gain  = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss  = (-delta).clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi_v = _safe((100 - 100 / (1 + rs)).iloc[-1])

    z = (close.iloc[-1] - close.rolling(20).mean().iloc[-1]) / (close.rolling(20).std().iloc[-1] or 1)

    running_max = close.cummax()
    drawdown    = (close - running_max) / running_max * 100
    max_dd      = _safe(drawdown.min())

    return {
        "current_price":  _safe(close.iloc[-1]),
        "moving_averages": ma_vals,
        "volatility_pct": vol_pct,
        "rsi":            rsi_v,
        "rsi_signal":     "overbought" if (rsi_v or 0) > 70 else "oversold" if (rsi_v or 0) < 30 else "neutral",
        "price_zscore":   _safe(z),
        "price_anomaly":  abs(float(z or 0)) > 2.5,
        "max_drawdown_pct": max_dd,
    }
