import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Star, TrendingUp } from 'lucide-react'
import { stocksApi, watchlistApi } from '../api/client'
import Card from '../components/Card'
import './SearchPage.css'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [adding, setAdding] = useState(null)
  const navigate = useNavigate()

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    setResults([])
    try {
      const data = await stocksApi.search(query.trim())
      setResults(data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  const addToWatchlist = async (item) => {
    setAdding(item.symbol)
    try {
      await watchlistApi.add({ symbol: item.symbol, company_name: item.name })
      alert(`${item.symbol} added to watchlist!`)
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to add')
    } finally {
      setAdding(null)
    }
  }

  return (
    <div className="search-page">
      <div className="page-header">
        <h1>Search Stocks</h1>
        <p className="page-sub">Search by company name or ticker symbol (e.g. RELIANCE, TCS, INFY)</p>
      </div>

      <form className="search-form" onSubmit={handleSearch}>
        <div className="search-input-wrap">
          <Search size={16} className="search-icon" />
          <input
            className="search-input"
            type="text"
            placeholder="Search symbol or company..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            autoFocus
          />
        </div>
        <button className="search-btn" type="submit" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {error && <div className="search-error">{error}</div>}

      {results.length > 0 && (
        <div className="search-results">
          {results.map(item => (
            <Card key={item.symbol} className="result-card">
              <div className="result-left">
                <div className="result-symbol">{item.symbol}</div>
                <div className="result-name">{item.name}</div>
                <div className="result-meta">
                  <span>{item.region}</span>
                  <span>{item.currency}</span>
                  <span>Score: {parseFloat(item.match_score || 0).toFixed(2)}</span>
                </div>
              </div>
              <div className="result-actions">
                <button
                  className="result-btn view"
                  onClick={() => navigate(`/stock/${encodeURIComponent(item.symbol)}`)}
                >
                  <TrendingUp size={14} /> View
                </button>
                <button
                  className="result-btn watch"
                  onClick={() => addToWatchlist(item)}
                  disabled={adding === item.symbol}
                >
                  <Star size={14} /> {adding === item.symbol ? '...' : 'Watch'}
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {!loading && results.length === 0 && query && (
        <div className="search-empty">No results found for "{query}". Try a different term.</div>
      )}
    </div>
  )
}
