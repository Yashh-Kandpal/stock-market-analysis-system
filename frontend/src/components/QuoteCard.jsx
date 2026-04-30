import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, RefreshCw } from 'lucide-react'
import { stocksApi } from '../api/client'
import Card from './Card'
import './QuoteCard.css'

export default function QuoteCard({ symbol, companyName, onSelect }) {
  const [quote, setQuote] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await stocksApi.getQuote(symbol)
      setQuote(data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to fetch')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [symbol])

  const change = parseFloat(quote?.change || 0)
  const changePct = parseFloat(quote?.change_percent || 0)
  const isUp = change >= 0

  return (
    <Card className={`quote-card ${onSelect ? 'clickable' : ''}`} onClick={onSelect ? () => onSelect(symbol) : undefined}>
      <div className="qc-header">
        <div>
          <div className="qc-symbol">{symbol}</div>
          {companyName && <div className="qc-name">{companyName}</div>}
        </div>
        <button className="qc-refresh" onClick={(e) => { e.stopPropagation(); load() }} title="Refresh">
          <RefreshCw size={14} className={loading ? 'spinning' : ''} />
        </button>
      </div>

      {loading && !quote && <div className="qc-skeleton" />}

      {error && <div className="qc-error">{error}</div>}

      {quote && (
        <div className="qc-body">
          <div className="qc-price">₹{parseFloat(quote.price).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
          <div className={`qc-change ${isUp ? 'up' : 'down'}`}>
            {isUp ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            <span>{isUp ? '+' : ''}{change.toFixed(2)} ({isUp ? '+' : ''}{changePct.toFixed(2)}%)</span>
          </div>
          <div className="qc-meta">
            <span>H: ₹{parseFloat(quote.high || 0).toFixed(2)}</span>
            <span>L: ₹{parseFloat(quote.low || 0).toFixed(2)}</span>
            <span>Vol: {parseInt(quote.volume || 0).toLocaleString('en-IN')}</span>
          </div>
        </div>
      )}
    </Card>
  )
}
