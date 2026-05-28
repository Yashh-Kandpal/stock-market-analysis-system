// Add this to the existing api/client.js
// Append analysisApi below the existing watchlistApi export

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
