"""
XGBoost model for next-day direction prediction.
More powerful than LR — captures non-linear feature interactions.
Also includes a multi-day forward return prediction.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, classification_report
from ml.features import build_features, get_feature_names


def run_xgboost(records: list[dict]) -> dict:
    """
    Trains XGBoost classifier to predict next-day direction.
    Also predicts 5-day forward return using XGBoost regressor.
    Returns feature importance, metrics, and prediction.
    """
    try:
        from xgboost import XGBClassifier, XGBRegressor
    except ImportError:
        raise ImportError("xgboost not installed. Run: pip install xgboost")

    df = build_features(records)
    if len(df) < 60:
        raise ValueError("Need at least 60 data points")

    feat_cols = get_feature_names(df)
    X  = df[feat_cols].values
    yc = df['target_direction'].values
    yr = df['target_return'].values

    # Also build 5-day forward return target
    df['target_5d'] = df['close'].pct_change(5).shift(-5)
    df_clean = df.dropna(subset=['target_5d'])
    X5  = df_clean[feat_cols].values
    y5  = df_clean['target_5d'].values

    split  = int(len(X) * 0.8)
    X_train, X_test   = X[:split],  X[split:]
    yc_train, yc_test = yc[:split], yc[split:]
    yr_train, yr_test = yr[:split], yr[split:]

    split5 = int(len(X5) * 0.8)
    X5_train, X5_test = X5[:split5], X5[split5:]
    y5_train, y5_test = y5[:split5], y5[split5:]

    # ── XGBoost Classifier ────────────────────────────────────────────────
    clf = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric='logloss',
        random_state=42,
        verbosity=0,
    )
    clf.fit(
        X_train, yc_train,
        eval_set=[(X_test, yc_test)],
        verbose=False,
    )

    yc_pred = clf.predict(X_test)
    yc_prob = clf.predict_proba(X_test)[:, 1]
    direction_acc = float(accuracy_score(yc_test, yc_pred))

    # ── XGBoost Regressor (5-day return) ──────────────────────────────────
    reg = XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0,
    )
    reg.fit(X5_train, y5_train, verbose=False)
    y5_pred     = reg.predict(X5_test)
    reg_dir_acc = float(np.mean(np.sign(y5_pred) == np.sign(y5_test)))

    # ── Feature importance ────────────────────────────────────────────────
    importance = pd.Series(
        clf.feature_importances_, index=feat_cols
    ).sort_values(ascending=False)

    top_features = [
        {"feature": k, "importance": round(float(v), 4)}
        for k, v in importance.head(20).items()
    ]

    # ── Cross-validation ──────────────────────────────────────────────────
    tscv = TimeSeriesSplit(n_splits=5)
    cv_scores = []
    for train_idx, val_idx in tscv.split(X):
        clf_cv = XGBClassifier(
            n_estimators=100, max_depth=3, learning_rate=0.1,
            use_label_encoder=False, eval_metric='logloss',
            random_state=42, verbosity=0,
        )
        clf_cv.fit(X[train_idx], yc[train_idx], verbose=False)
        cv_scores.append(accuracy_score(yc[val_idx], clf_cv.predict(X[val_idx])))

    # ── Next-day prediction ───────────────────────────────────────────────
    latest_X        = X[-1:]
    next_direction  = int(clf.predict(latest_X)[0])
    next_prob_up    = float(clf.predict_proba(latest_X)[0][1])
    current_price   = float(df['close'].iloc[-1])

    # 5-day forward prediction
    latest_X5     = X5[-1:] if len(X5) > 0 else latest_X
    pred_5d_ret   = float(reg.predict(latest_X5)[0])
    pred_5d_price = round(current_price * (1 + pred_5d_ret), 2)

    # Prediction confidence buckets
    confidence = max(next_prob_up, 1 - next_prob_up)
    confidence_label = (
        "High"   if confidence > 0.65 else
        "Medium" if confidence > 0.55 else
        "Low"
    )

    return {
        "model": "XGBoost",
        "train_samples": split,
        "test_samples":  len(X_test),
        "metrics": {
            "direction_accuracy_pct":    round(direction_acc * 100, 2),
            "5d_direction_accuracy_pct": round(reg_dir_acc * 100, 2),
            "cv_accuracy_mean_pct":      round(float(np.mean(cv_scores)) * 100, 2),
            "cv_accuracy_std_pct":       round(float(np.std(cv_scores)) * 100, 2),
        },
        "prediction": {
            "current_price":      round(current_price, 2),
            "direction":          "UP" if next_direction == 1 else "DOWN",
            "prob_up_pct":        round(next_prob_up * 100, 1),
            "confidence_pct":     round(confidence * 100, 1),
            "confidence_label":   confidence_label,
            "pred_5d_return_pct": round(pred_5d_ret * 100, 2),
            "pred_5d_price":      pred_5d_price,
        },
        "top_features": top_features,
    }
