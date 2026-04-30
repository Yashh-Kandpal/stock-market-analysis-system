import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { stocksApi } from '../api/client'
import QuoteCard from '../components/QuoteCard'
import Loader from '../components/Loader'
import './Dashboard.css'

export default function Dashboard() {
  const [stocks, setStocks] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    stocksApi.getPopular()
      .then(setStocks)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loader text="Loading popular stocks..." />

  return (
    <div className="dashboard">
      <div className="page-header">
        <h1>Indian Markets</h1>
        <p className="page-sub">Live prices from BSE — click any stock to explore charts and data.</p>
      </div>

      <div className="quote-grid">
        {stocks.map(s => (
          <QuoteCard
            key={s.symbol}
            symbol={s.symbol}
            companyName={s.company_name}
            onSelect={(sym) => navigate(`/stock/${encodeURIComponent(sym)}`)}
          />
        ))}
      </div>
    </div>
  )
}
