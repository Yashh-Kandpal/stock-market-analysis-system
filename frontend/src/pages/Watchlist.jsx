import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Trash2, Star } from 'lucide-react'
import { watchlistApi } from '../api/client'
import QuoteCard from '../components/QuoteCard'
import Loader from '../components/Loader'
import './Watchlist.css'

export default function Watchlist() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    watchlistApi.getAll()
      .then(setItems)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const remove = async (symbol) => {
    try {
      await watchlistApi.remove(symbol)
      setItems(i => i.filter(s => s.symbol !== symbol))
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to remove')
    }
  }

  if (loading) return <Loader text="Loading watchlist..." />

  return (
    <div className="watchlist-page">
      <div className="page-header">
        <h1>Watchlist</h1>
        <p className="page-sub">Track your favourite Indian stocks. Add stocks from the search page.</p>
      </div>

      {items.length === 0 ? (
        <div className="wl-empty">
          <Star size={40} color="var(--border)" />
          <p>Your watchlist is empty.</p>
          <p>Search for stocks and add them to track here.</p>
          <button className="wl-cta" onClick={() => navigate('/search')}>Go to Search</button>
        </div>
      ) : (
        <div className="wl-grid">
          {items.map(item => (
            <div key={item.symbol} className="wl-item">
              <QuoteCard
                symbol={item.symbol}
                companyName={item.company_name}
                onSelect={(sym) => navigate(`/stock/${encodeURIComponent(sym)}`)}
              />
              <button className="wl-remove" onClick={() => remove(item.symbol)} title="Remove from watchlist">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
