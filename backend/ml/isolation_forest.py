"""
Isolation Forest anomaly detection.
Detects unusual trading days based on the full feature set —
not just price or volume in isolation, but the combination of all indicators.
This is more powerful than Z-score which checks each metric independently.

From the project report: "Isolation Forests" for anomaly detection.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from ml.features import build_features, get_feature_names


def run_isolation_forest(
    records: list[dict],
    contamination: float = 0.05,   # expected % of anomalies (5%)
) -> dict:
    """
    Trains Isolation Forest on technical features to detect anomalous trading days.

    Unlike Z-score (which checks one metric at a time), Isolation Forest
    detects days that are unusual across MULTIPLE dimensions simultaneously —
    e.g. high volume + RSI spike + price gap + volatility jump all at once.

    Returns:
        anomalies   : list of detected anomalous days with their scores
        scores      : full series of anomaly scores for charting
        summary     : count and severity breakdown
        comparison  : how IF compares to pure price Z-score
    """
    df = build_features(records)
    if len(df) < 50:
        raise ValueError("Need at least 50 data points")

    feat_cols = get_feature_names(df)

    # Use a focused subset of features most relevant to anomaly detection
    anomaly_features = [
        'return_1d', 'log_return_1d', 'hl_ratio', 'oc_ratio', 'gap',
        'rsi_14', 'macd_hist', 'bb_pct_b', 'bb_width',
        'vol_ratio_20', 'vol_zscore', 'atr_14_ratio', 'vol_5',
        'roc_5', 'stoch_k',
    ]
    # Only use features that exist
    anomaly_features = [f for f in anomaly_features if f in df.columns]

    X = df[anomaly_features].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train Isolation Forest
    iso = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    labels = iso.fit_predict(X_scaled)   # -1 = anomaly, 1 = normal
    scores = iso.score_samples(X_scaled) # more negative = more anomalous

    df['if_label'] = labels
    df['if_score'] = scores

    # Normalise scores to 0-100 (0 = most anomalous)
    min_s, max_s = scores.min(), scores.max()
    df['anomaly_score'] = ((scores - min_s) / (max_s - min_s + 1e-9)) * 100

    # Detected anomalies
    anomaly_rows = df[df['if_label'] == -1].copy()

    # Severity: bottom 33% of anomaly scores = severe
    threshold_severe   = np.percentile(scores[labels == -1], 33) if len(scores[labels == -1]) > 0 else scores.min()
    anomaly_rows['severity'] = anomaly_rows['if_score'].apply(
        lambda s: 'severe' if s <= threshold_severe else 'moderate'
    )

    # What made each day anomalous — which features were most extreme
    def _top_drivers(row_idx: int) -> list[str]:
        row   = X_scaled[row_idx]
        abs_z = np.abs(row)
        top   = np.argsort(abs_z)[::-1][:3]
        return [anomaly_features[i] for i in top]

    anomaly_list = []
    for idx in anomaly_rows.index:
        pos = df.index.get_loc(idx)
        row = anomaly_rows.loc[idx]
        anomaly_list.append({
            "date":          str(idx.date()) if hasattr(idx, 'date') else str(idx),
            "close":         round(float(row.get('close', 0)), 2),
            "return_pct":    round(float(row.get('return_1d', 0)) * 100, 2),
            "volume_ratio":  round(float(row.get('vol_ratio_20', 0)), 2),
            "anomaly_score": round(float(row['anomaly_score']), 1),
            "severity":      row['severity'],
            "top_drivers":   _top_drivers(pos),
        })

    # Sort by most anomalous first
    anomaly_list.sort(key=lambda x: x['anomaly_score'])

    # Full score series for chart
    score_series = [
        {
            "date":          str(ts.date()) if hasattr(ts, 'date') else str(ts),
            "anomaly_score": round(float(df.loc[ts, 'anomaly_score']), 1),
            "is_anomaly":    bool(df.loc[ts, 'if_label'] == -1),
        }
        for ts in df.index
    ]

    # Compare with Z-score: how many anomalies overlap?
    price_z = (df['return_1d'] - df['return_1d'].rolling(20).mean()) / df['return_1d'].rolling(20).std()
    zscore_anomalies = set(df[price_z.abs() > 2.5].index)
    if_anomalies     = set(anomaly_rows.index)
    overlap          = len(zscore_anomalies & if_anomalies)
    if_only          = len(if_anomalies - zscore_anomalies)
    zscore_only      = len(zscore_anomalies - if_anomalies)

    return {
        "model":         "Isolation Forest",
        "contamination": contamination,
        "features_used": len(anomaly_features),
        "summary": {
            "total_days":      len(df),
            "anomaly_count":   int((labels == -1).sum()),
            "anomaly_pct":     round(float((labels == -1).mean() * 100), 1),
            "severe_count":    int(anomaly_rows[anomaly_rows['severity'] == 'severe'].shape[0]),
            "moderate_count":  int(anomaly_rows[anomaly_rows['severity'] == 'moderate'].shape[0]),
        },
        "vs_zscore": {
            "overlap_count":   overlap,
            "if_only_count":   if_only,
            "zscore_only_count": zscore_only,
            "note": f"IF found {if_only} anomalies that Z-score missed (multi-dimensional)",
        },
        "anomalies":    anomaly_list,
        "score_series": score_series,
    }
