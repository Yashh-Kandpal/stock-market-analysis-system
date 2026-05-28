"""
Linear Regression model for next-day return prediction.
Uses engineered technical features as inputs.
Also includes Ridge regression (L2 regularisation) for comparison.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge, LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error,
    accuracy_score, classification_report
)
from ml.features import build_features, get_feature_names


def run_linear_regression(records: list[dict]) -> dict:
    """
    Trains Linear Regression + Logistic Regression on technical features.

    Linear Regression  → predicts next-day return magnitude
    Logistic Regression → predicts next-day direction (Up/Down)

    Uses TimeSeriesSplit cross-validation (no data leakage).
    Returns metrics, feature importances, and next-day prediction.
    """
    df = build_features(records)
    if len(df) < 60:
        raise ValueError("Need at least 60 data points")

    feat_cols = get_feature_names(df)
    X = df[feat_cols].values
    y_reg  = df['target_return'].values      # regression target
    y_clf  = df['target_direction'].values   # classification target

    # Train/test split — last 20% for testing, always by time
    split  = int(len(X) * 0.8)
    X_train, X_test   = X[:split], X[split:]
    yr_train, yr_test = y_reg[:split],  y_reg[split:]
    yc_train, yc_test = y_clf[:split],  y_clf[split:]

    # Scale features (important for LR)
    scaler  = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    # ── Regression (return magnitude) ──────────────────────────────────────
    lr  = Ridge(alpha=1.0)
    lr.fit(X_train_s, yr_train)
    yr_pred = lr.predict(X_test_s)

    rmse = float(np.sqrt(mean_squared_error(yr_test, yr_pred)))
    mae  = float(mean_absolute_error(yr_test, yr_pred))

    # Direction accuracy from regression (sign of predicted return)
    reg_direction_acc = float(np.mean(np.sign(yr_pred) == np.sign(yr_test)))

    # ── Classification (direction) ─────────────────────────────────────────
    clf = LogisticRegression(max_iter=1000, C=1.0)
    clf.fit(X_train_s, yc_train)
    yc_pred = clf.predict(X_test_s)
    yc_prob = clf.predict_proba(X_test_s)[:, 1]

    direction_acc = float(accuracy_score(yc_test, yc_pred))

    # ── Feature importance (absolute coefficients from Ridge) ──────────────
    importance = pd.Series(
        np.abs(lr.coef_), index=feat_cols
    ).sort_values(ascending=False)

    top_features = [
        {"feature": k, "importance": round(float(v), 4)}
        for k, v in importance.head(15).items()
    ]

    # ── Next-day prediction ────────────────────────────────────────────────
    latest_X = scaler.transform(X[-1:])
    next_return     = float(lr.predict(latest_X)[0])
    next_direction  = int(clf.predict(latest_X)[0])
    next_prob_up    = float(clf.predict_proba(latest_X)[0][1])
    current_price   = float(df['close'].iloc[-1])
    predicted_price = round(current_price * (1 + next_return), 2)

    # ── Cross-validation accuracy ──────────────────────────────────────────
    tscv = TimeSeriesSplit(n_splits=5)
    cv_scores = []
    for train_idx, val_idx in tscv.split(X):
        Xtr = scaler.fit_transform(X[train_idx])
        Xva = scaler.transform(X[val_idx])
        clf_cv = LogisticRegression(max_iter=500, C=1.0)
        clf_cv.fit(Xtr, y_clf[train_idx])
        cv_scores.append(accuracy_score(y_clf[val_idx], clf_cv.predict(Xva)))

    return {
        "model": "Linear Regression + Logistic Regression",
        "train_samples": split,
        "test_samples":  len(X_test),
        "metrics": {
            "regression_rmse":        round(rmse * 100, 4),
            "regression_mae":         round(mae * 100, 4),
            "direction_accuracy_pct": round(direction_acc * 100, 2),
            "reg_direction_acc_pct":  round(reg_direction_acc * 100, 2),
            "cv_accuracy_mean_pct":   round(float(np.mean(cv_scores)) * 100, 2),
            "cv_accuracy_std_pct":    round(float(np.std(cv_scores)) * 100, 2),
        },
        "prediction": {
            "current_price":   round(current_price, 2),
            "predicted_price": predicted_price,
            "predicted_return_pct": round(next_return * 100, 3),
            "direction":       "UP" if next_direction == 1 else "DOWN",
            "confidence_pct":  round(max(next_prob_up, 1 - next_prob_up) * 100, 1),
            "prob_up_pct":     round(next_prob_up * 100, 1),
        },
        "top_features": top_features,
    }
