"""
Prophet forecasting model (Meta).
Handles trend + seasonality automatically.
Good for multi-week forecasts with uncertainty bands.
"""

import warnings
warnings.filterwarnings('ignore')
import logging
logging.getLogger('prophet').setLevel(logging.ERROR)
logging.getLogger('cmdstanpy').setLevel(logging.ERROR)

import numpy as np
import pandas as pd


def run_prophet(records: list[dict], forecast_days: int = 30) -> dict:
    """
    Fits Prophet on historical close prices.
    Returns forecast with trend decomposition.
    """
    try:
        from prophet import Prophet
    except ImportError:
        raise ImportError("prophet not installed. Run: pip install prophet")

    df = pd.DataFrame(records)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    df = df[df['close'] > 0]

    if len(df) < 60:
        raise ValueError("Need at least 60 data points for Prophet")

    # Prophet expects columns: ds (date) and y (value)
    prophet_df = pd.DataFrame({
        'ds': df['timestamp'].dt.tz_localize(None),
        'y':  np.log(df['close'].astype(float)),  # log scale for better fit
    })

    # Add Indian market seasonality markers
    model = Prophet(
        changepoint_prior_scale=0.05,   # flexibility of trend
        seasonality_prior_scale=10,
        daily_seasonality=False,
        weekly_seasonality=True,
        yearly_seasonality=True,
        interval_width=0.95,
    )

    # Add monthly seasonality (common in Indian markets — monthly expiry etc.)
    model.add_seasonality(name='monthly', period=30.5, fourier_order=5)

    model.fit(prophet_df)

    # Make future dataframe (business days only)
    future = model.make_future_dataframe(periods=forecast_days, freq='B')
    forecast = model.predict(future)

    # Convert back from log scale
    forecast['yhat']       = np.exp(forecast['yhat'])
    forecast['yhat_lower'] = np.exp(forecast['yhat_lower'])
    forecast['yhat_upper'] = np.exp(forecast['yhat_upper'])

    # Historical fitted values
    hist_len = len(prophet_df)
    historical = []
    for i, row in forecast.head(hist_len).iterrows():
        historical.append({
            "date":     str(row['ds'].date()),
            "actual":   round(float(np.exp(prophet_df.iloc[i]['y'])), 2),
            "fitted":   round(float(row['yhat']), 2),
        })

    # Future forecast only
    future_rows = forecast.tail(forecast_days)
    forecast_list = []
    for _, row in future_rows.iterrows():
        forecast_list.append({
            "date":      str(row['ds'].date()),
            "predicted": round(float(row['yhat']), 2),
            "lower_95":  round(float(row['yhat_lower']), 2),
            "upper_95":  round(float(row['yhat_upper']), 2),
            "trend":     round(float(np.exp(row['trend'])), 2),
        })

    # Trend direction
    trend_start = float(np.exp(forecast['trend'].iloc[hist_len - 30]))
    trend_end   = float(np.exp(forecast['trend'].iloc[-1]))
    trend_direction = "upward" if trend_end > trend_start else "downward"
    trend_change_pct = round((trend_end - trend_start) / trend_start * 100, 2)

    current_price = float(df['close'].iloc[-1])
    pred_price_30d = round(float(future_rows['yhat'].iloc[-1]), 2)

    return {
        "model":        "Prophet",
        "forecast_days": forecast_days,
        "historical":   historical[-90:],   # last 90 days context
        "forecast":     forecast_list,
        "trend": {
            "direction":   trend_direction,
            "change_pct":  trend_change_pct,
        },
        "summary": {
            "current_price":    round(current_price, 2),
            "predicted_30d":    pred_price_30d,
            "expected_return_pct": round((pred_price_30d - current_price) / current_price * 100, 2),
        },
    }
