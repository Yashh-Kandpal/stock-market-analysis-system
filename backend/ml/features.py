"""
Feature Engineering for ML models.

Takes raw OHLCV records (list of dicts from DB/yfinance) and produces
a fully-featured pandas DataFrame ready for model training/inference.

Features produced:
  Price-derived  : returns, log returns, price ratios
  Trend          : SMA/EMA ratios, crossover signals
  Momentum       : RSI, MACD, Rate of Change
  Volatility     : rolling std, ATR, Bollinger %B
  Volume         : volume Z-score, OBV, volume ratio
  Lag features   : yesterday's and 2-days-ago values of key features
  Target         : next-day return direction (1=up, 0=down) + magnitude
"""

import numpy as np
import pandas as pd
from typing import Optional


def build_features(records: list[dict]) -> pd.DataFrame:
    """
    Main entry point. Returns a DataFrame where each row = one trading day,
    columns = features, last two columns = target_direction + target_return.
    NaN rows (from rolling windows) are dropped.
    """
    df = _to_df(records)
    df = _price_features(df)
    df = _trend_features(df)
    df = _momentum_features(df)
    df = _volatility_features(df)
    df = _volume_features(df)
    df = _lag_features(df)
    df = _targets(df)
    df = df.replace([np.inf, -np.inf], np.nan)
    # Only drop rows where core features are missing, fill others with 0
    core_cols = ['return_1d', 'rsi_14', 'macd_hist', 'bb_pct_b', 'vol_ratio_20']
    df = df.dropna(subset=core_cols)
    df = df.fillna(0)
    return df


def build_inference_row(records: list[dict]) -> pd.Series:
    """
    Returns the LATEST row of features for prediction (no target columns).
    Used when making a prediction for today.
    """
    df = build_features(records)
    # drop targets for inference
    feat_cols = [c for c in df.columns if not c.startswith('target_')]
    return df[feat_cols].iloc[-1]


def feature_columns(records: list[dict]) -> list[str]:
    df = build_features(records)
    return [c for c in df.columns if not c.startswith('target_')]


# ─── internal helpers ─────────────────────────────────────────────────────────

def _to_df(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').set_index('timestamp')
    # Drop non-numeric columns
    for col in ['symbol', 'interval']:
        if col in df.columns:
            df = df.drop(columns=[col])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df[df['close'] > 0]
    return df


def _price_features(df: pd.DataFrame) -> pd.DataFrame:
    df['return_1d']     = df['close'].pct_change()
    df['log_return_1d'] = np.log(df['close'] / df['close'].shift(1))
    df['hl_ratio']      = (df['high'] - df['low']) / df['close']   # candle range %
    df['oc_ratio']      = (df['close'] - df['open']) / df['open']  # open-to-close %
    df['gap']           = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
    return df


def _trend_features(df: pd.DataFrame) -> pd.DataFrame:
    # Only compute MAs we have enough data for
    for w in [9, 20, 50]:          # removed 200 — needs 200+ rows
        df[f'sma_{w}']       = df['close'].rolling(w).mean()
        df[f'ema_{w}']       = df['close'].ewm(span=w, adjust=False).mean()
        df[f'sma_{w}_ratio'] = df['close'] / df[f'sma_{w}']

    df['sma_20_50_cross']  = (df['sma_20'] > df['sma_50']).astype(int)
    df['sma_50_200_cross'] = 0   # placeholder — not enough data
    df['sma20_slope']      = df['sma_20'].diff(5) / df['close']
    return df


def _momentum_features(df: pd.DataFrame) -> pd.DataFrame:
    # RSI
    delta = df['close'].diff()
    gain  = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss  = (-delta).clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    rs    = gain / loss.replace(0, np.nan)
    df['rsi_14'] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd']        = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist']   = df['macd'] - df['macd_signal']
    df['macd_cross']  = (df['macd'] > df['macd_signal']).astype(int)

    # Rate of Change
    df['roc_5']  = df['close'].pct_change(5)
    df['roc_10'] = df['close'].pct_change(10)
    df['roc_20'] = df['close'].pct_change(20)

    # Stochastic %K (14-day)
    low14  = df['low'].rolling(14).min()
    high14 = df['high'].rolling(14).max()
    df['stoch_k'] = (df['close'] - low14) / (high14 - low14 + 1e-9) * 100
    df['stoch_d'] = df['stoch_k'].rolling(3).mean()

    return df


def _volatility_features(df: pd.DataFrame) -> pd.DataFrame:
    # Rolling volatility (annualised)
    df['vol_20']  = df['log_return_1d'].rolling(20).std() * np.sqrt(252)
    df['vol_5']   = df['log_return_1d'].rolling(5).std()  * np.sqrt(252)
    df['vol_ratio'] = df['vol_5'] / df['vol_20']  # short vs long vol (vol regime)

    # Bollinger Bands
    sma20 = df['close'].rolling(20).mean()
    std20 = df['close'].rolling(20).std()
    df['bb_upper']  = sma20 + 2 * std20
    df['bb_lower']  = sma20 - 2 * std20
    df['bb_pct_b']  = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-9)
    df['bb_width']  = (df['bb_upper'] - df['bb_lower']) / sma20

    # ATR
    prev_close = df['close'].shift(1)
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - prev_close).abs(),
        (df['low']  - prev_close).abs(),
    ], axis=1).max(axis=1)
    df['atr_14']       = tr.rolling(14).mean()
    df['atr_14_ratio'] = df['atr_14'] / df['close']  # normalised ATR

    return df


def _volume_features(df: pd.DataFrame) -> pd.DataFrame:
    df['vol_sma_20']   = df['volume'].rolling(20).mean()
    df['vol_ratio_20'] = df['volume'] / df['vol_sma_20']  # relative volume

    # Volume Z-score
    vol_std = df['volume'].rolling(20).std()
    df['vol_zscore'] = (df['volume'] - df['vol_sma_20']) / vol_std.replace(0, np.nan)

    # On-Balance Volume (normalised by rolling mean)
    obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
    df['obv_ratio'] = obv / obv.rolling(20).mean()

    # Price-volume trend
    df['pvt'] = (df['return_1d'] * df['volume']).fillna(0).cumsum()
    df['pvt_ratio'] = df['pvt'] / df['pvt'].rolling(20).mean()

    return df


def _lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add 1-day and 2-day lagged versions of key features."""
    lag_cols = [
        'return_1d', 'rsi_14', 'macd_hist', 'bb_pct_b',
        'vol_ratio_20', 'vol_zscore', 'atr_14_ratio', 'roc_5',
    ]
    for col in lag_cols:
        if col in df.columns:
            df[f'{col}_lag1'] = df[col].shift(1)
            df[f'{col}_lag2'] = df[col].shift(2)
    return df


def _targets(df: pd.DataFrame) -> pd.DataFrame:
    """
    target_return    : next day's percentage return (regression target)
    target_direction : 1 if next day closes higher, 0 if lower (classification target)
    """
    df['target_return']    = df['close'].pct_change().shift(-1)
    df['target_direction'] = (df['target_return'] > 0).astype(int)
    return df


def get_feature_names(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if not c.startswith('target_') and
            c not in ['open', 'high', 'low', 'close', 'volume', 'symbol']]
