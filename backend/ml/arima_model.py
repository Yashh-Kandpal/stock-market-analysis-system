"""
ARIMA forecasting model.
Uses auto-selection of (p,d,q) parameters via AIC minimisation.
Returns N-day price forecast with 95% confidence intervals.
"""

import numpy as np
import pandas as pd
import warnings
from itertools import product
from typing import Optional

warnings.filterwarnings('ignore')


def _select_arima_order(series: pd.Series, max_p: int = 3, max_q: int = 3) -> tuple:
    """
    Grid search over (p, d, q) to find order with lowest AIC.
    d is determined by ADF test (0 or 1).
    """
    from statsmodels.tsa.stattools import adfuller
    from statsmodels.tsa.arima.model import ARIMA

    # Determine d via ADF test
    adf_result = adfuller(series.dropna())
    d = 0 if adf_result[1] < 0.05 else 1  # stationary → d=0

    best_aic = np.inf
    best_order = (1, d, 1)

    for p, q in product(range(max_p + 1), range(max_q + 1)):
        if p == 0 and q == 0:
            continue
        try:
            model = ARIMA(series, order=(p, d, q))
            res   = model.fit()
            if res.aic < best_aic:
                best_aic   = res.aic
                best_order = (p, d, q)
        except Exception:
            continue

    return best_order


def run_arima(records: list[dict], forecast_days: int = 14) -> dict:
    """
    Fit ARIMA on historical close prices and forecast next N days.

    Returns:
        historical   : last 90 days of actual prices (for chart context)
        forecast     : list of {date, predicted, lower_95, upper_95}
        order        : (p,d,q) used
        aic          : model quality score
        metrics      : in-sample RMSE and MAE
    """
    from statsmodels.tsa.arima.model import ARIMA

    df = pd.DataFrame(records)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').set_index('timestamp')
    close = df['close'].astype(float)
    close = close[close > 0]

    if len(close) < 30:
        raise ValueError("Need at least 30 data points for ARIMA")

    # Use log prices for better stationarity
    log_close = np.log(close)

    # Auto-select order (limit to last 200 days for speed)
    train_series = log_close.tail(200)
    order = _select_arima_order(train_series)

    # Fit on full series
    model  = ARIMA(log_close, order=order)
    result = model.fit()

    # In-sample metrics on last 30 days
    fitted      = np.exp(result.fittedvalues)
    actual_last = close.tail(30)
    fitted_last = fitted.tail(30)
    rmse = float(np.sqrt(((actual_last - fitted_last) ** 2).mean()))
    mae  = float((actual_last - fitted_last).abs().mean())
    mape = float(((actual_last - fitted_last).abs() / actual_last).mean() * 100)

    # Forecast
    forecast_res = result.get_forecast(steps=forecast_days)
    forecast_mean = np.exp(forecast_res.predicted_mean)
    conf_int      = np.exp(forecast_res.conf_int(alpha=0.05))

    # Build forecast dates (skip weekends)
    last_date = close.index[-1]
    forecast_dates = []
    current = last_date
    while len(forecast_dates) < forecast_days:
        current = current + pd.Timedelta(days=1)
        if current.weekday() < 5:  # Mon-Fri
            forecast_dates.append(current)

    forecast_list = []
    for i, date in enumerate(forecast_dates):
        forecast_list.append({
            "date":       str(date.date()),
            "predicted":  round(float(forecast_mean.iloc[i]), 2),
            "lower_95":   round(float(conf_int.iloc[i, 0]), 2),
            "upper_95":   round(float(conf_int.iloc[i, 1]), 2),
        })

    # Historical context (last 90 days)
    historical = [
        {"date": str(ts.date()), "actual": round(float(v), 2)}
        for ts, v in close.tail(90).items()
    ]

    return {
        "model":      "ARIMA",
        "order":      list(order),
        "aic":        round(float(result.aic), 2),
        "metrics": {
            "rmse": round(rmse, 2),
            "mae":  round(mae, 2),
            "mape": round(mape, 2),
        },
        "historical":  historical,
        "forecast":    forecast_list,
        "last_actual": round(float(close.iloc[-1]), 2),
    }
