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
