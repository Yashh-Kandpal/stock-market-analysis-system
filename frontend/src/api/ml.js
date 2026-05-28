// Append this to frontend/src/api/client.js

export const mlApi = {
  arima:           (symbol, days = 365, forecastDays = 14) =>
    api.get(`/ml/${symbol}/arima`,            { params: { days, forecast_days: forecastDays } }).then(r => r.data),
  linear:          (symbol, days = 365) =>
    api.get(`/ml/${symbol}/linear`,           { params: { days } }).then(r => r.data),
  xgboost:         (symbol, days = 365) =>
    api.get(`/ml/${symbol}/xgboost`,          { params: { days } }).then(r => r.data),
  isolationForest: (symbol, days = 365, contamination = 0.05) =>
    api.get(`/ml/${symbol}/isolation-forest`, { params: { days, contamination } }).then(r => r.data),
  prophet:         (symbol, days = 730, forecastDays = 30) =>
    api.get(`/ml/${symbol}/prophet`,          { params: { days, forecast_days: forecastDays } }).then(r => r.data),
  summary:         (symbol, days = 365) =>
    api.get(`/ml/${symbol}/summary`,          { params: { days } }).then(r => r.data),
  clearCache:      (symbol) =>
    api.delete(`/ml/${symbol}/cache`).then(r => r.data),
}
