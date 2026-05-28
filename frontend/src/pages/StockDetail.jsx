import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Star, StarOff } from 'lucide-react'
import { stocksApi, watchlistApi } from '../api/client'
import StockChart from '../components/StockChart'
import OHLCTable from '../components/OHLCTable'
import Card from '../components/Card'
import Loader from '../components/Loader'
import './StockDetail.css'

export default function StockDetail() {
  const { symbol } = useParams()
  const navigate = useNavigate()
  const decoded = decodeURIComponent(symbol)

  const [quote, setQuote] = useState(null)
  const [history, setHistory] = useState([])
  const [watchlist, setWatchlist] = useState([])
  const [tab, setTab] = useState('chart')
  const [loading, setLoading] = useState(true)

  const isWatched = watchlist.some(w => w.symbol === decoded)

  useEffect(() => {
    const init = async () => {
      setLoading(true)
      try {
        const [q, h, wl] = await Promise.all([
          stocksApi.getQuote(decoded),
          stocksApi.getDaily(decoded, 30),
          watchlistApi.getAll(),
        ])
        setQuote(q)
        setHistory(Array.isArray(h?.data) ? h.data : [])
        setWatchlist(wl)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [decoded])

  const toggleWatchlist = async () => {
    try {
      if (isWatched) {
        await watchlistApi.remove(decoded)
        setWatchlist(w => w.filter(i => i.symbol !== decoded))
      } else {
        const added = await watchlistApi.add({ symbol: decoded })
        setWatchlist(w => [...w, added])
      }
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to update watchlist')
    }
  }

  if (loading) return <Loader text="Loading stock data..." />

  const change = parseFloat(quote?.change || 0)
  const changePct = parseFloat(quote?.change_percent || 0)
  const isUp = change >= 0

  return (
    <div className="stock-detail">
      <div className="sd-topbar">
        <button className="back-btn" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} /> Back
        </button>
        <button className={`watch-btn ${isWatched ? 'watched' : ''}`} onClick={toggleWatchlist}>
          {isWatched ? <><StarOff size={15} /> Unwatch</> : <><Star size={15} /> Watchlist</>}
        </button>
      </div>

      <div className="sd-hero">
        <div>
          <h1 className="sd-symbol">{decoded}</h1>
          <div className={`sd-change ${isUp ? 'up' : 'down'}`}>
            {quote ? (
              <>
                <span className="sd-price">₹{parseFloat(quote.price || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                <span>{isUp ? '+' : ''}{change.toFixed(2)} ({isUp ? '+' : ''}{changePct.toFixed(2)}%)</span>
              </>
            ) : <span>—</span>}
          </div>
        </div>
        {quote && (
          <div className="sd-ohlc-strip">
            <div className="strip-item"><span>Open</span><span>₹{parseFloat(quote.open || 0).toFixed(2)}</span></div>
            <div className="strip-item"><span>High</span><span className="up">₹{parseFloat(quote.high || 0).toFixed(2)}</span></div>
            <div className="strip-item"><span>Low</span><span className="down">₹{parseFloat(quote.low || 0).toFixed(2)}</span></div>
            <div className="strip-item"><span>Prev Close</span><span>₹{parseFloat(quote.previous_close || 0).toFixed(2)}</span></div>
            <div className="strip-item"><span>Volume</span><span>{parseInt(quote.volume || 0).toLocaleString('en-IN')}</span></div>
          </div>
        )}
      </div>

      <div className="sd-tabs">
        <button className={tab === 'chart' ? 'active' : ''} onClick={() => setTab('chart')}>Chart</button>
        <button className={tab === 'table' ? 'active' : ''} onClick={async () => {
          setTab('table')
          if (history.length === 0) {
            try {
                const h = await stocksApi.getDaily(decoded, 30)
                setHistory(Array.isArray(h?.data) ? h.data : [])
            } catch (e) { console.error(e) }
          }
        }}>Data Table</button>
        <button onClick={() => navigate(`/analysis/${encodeURIComponent(decoded)}`)}>
          Analysis
        </button>
        <button onClick={() => navigate(`/ml/${encodeURIComponent(decoded)}`)}>
          ML Predictions
        </button>
      </div>

      <Card>
        {tab === 'chart' && <StockChart symbol={decoded} />}
        {tab === 'table' && <OHLCTable data={history} />}
      </Card>
    </div>
  )
}
