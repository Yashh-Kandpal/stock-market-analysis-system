import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: `${BASE}/api`,
  timeout: 30000,
})

export const stocksApi = {
  getPopular: () => api.get('/stocks/popular').then(r => r.data),
  search: (q) => api.get('/stocks/search', { params: { q } }).then(r => r.data),
  getQuote: (symbol) => api.get(`/stocks/quote/${symbol}`).then(r => r.data),
  getIntraday: (symbol, interval = '5min', refresh = false) =>
    api.get(`/stocks/intraday/${symbol}`, { params: { interval, refresh } }).then(r => r.data),
  getDaily: (symbol, days = 30, refresh = false) =>
    api.get(`/stocks/daily/${symbol}`, { params: { days, refresh } }).then(r => r.data),
  getHistory: (symbol, interval = '1day', limit = 100) =>
    api.get(`/stocks/history/${symbol}`, { params: { interval, limit } }).then(r => r.data),
}

export const watchlistApi = {
  getAll: () => api.get('/watchlist/').then(r => r.data),
  add: (body) => api.post('/watchlist/', body).then(r => r.data),
  remove: (symbol) => api.delete(`/watchlist/${symbol}`).then(r => r.data),
  update: (symbol, body) => api.patch(`/watchlist/${symbol}`, body).then(r => r.data),
}

export default api

export const analysisApi = {
  summary:           (symbol, days = 90)                          => api.get(`/analysis/${symbol}/summary`,            { params: { days } }).then(r => r.data),
  movingAverages:    (symbol, days = 180, windows = '9,20,50,200') => api.get(`/analysis/${symbol}/moving-averages`,    { params: { days, windows } }).then(r => r.data),
  volatility:        (symbol, days = 180, window = 20)             => api.get(`/analysis/${symbol}/volatility`,         { params: { days, window } }).then(r => r.data),
  anomalies:         (symbol, days = 180, window = 20, threshold = 2.5) => api.get(`/analysis/${symbol}/anomalies`,    { params: { days, window, threshold } }).then(r => r.data),
  rsi:               (symbol, days = 180, period = 14)             => api.get(`/analysis/${symbol}/rsi`,               { params: { days, period } }).then(r => r.data),
  macd:              (symbol, days = 180)                          => api.get(`/analysis/${symbol}/macd`,              { params: { days } }).then(r => r.data),
  supportResistance: (symbol, days = 180)                          => api.get(`/analysis/${symbol}/support-resistance`, { params: { days } }).then(r => r.data),
  returns:           (symbol, days = 365)                          => api.get(`/analysis/${symbol}/returns`,            { params: { days } }).then(r => r.data),
  full:              (symbol, days = 180)                          => api.get(`/analysis/${symbol}/full`,               { params: { days } }).then(r => r.data),
}

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

export const performanceApi = {
  summary:     (days = 30) =>
    api.get('/performance/summary',       { params: { days } }).then(r => r.data),
  log:         (symbol, model, days = 30, limit = 50) =>
    api.get('/performance/log',           { params: { symbol, model, days, limit } }).then(r => r.data),
  bySymbol:    (symbol, days = 30) =>
    api.get(`/performance/symbol/${symbol}`, { params: { days } }).then(r => r.data),
  calibration: (days = 60) =>
    api.get('/performance/calibration',   { params: { days } }).then(r => r.data),
}