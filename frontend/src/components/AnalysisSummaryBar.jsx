import { useEffect, useState } from 'react'
import { analysisApi } from '../api/analysis'
import StatCard from './StatCard'
import './AnalysisSummaryBar.css'

export default function AnalysisSummaryBar({ symbol }) {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!symbol) return
    setLoading(true)
    analysisApi.summary(symbol, 90)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [symbol])

  if (loading) return <div className="asb-loading">Computing indicators…</div>
  if (!data)   return null

  return (
    <div className="asb-grid">
      <StatCard label="RSI (14)" value={data.rsi} signal={data.rsi_signal} />
      <StatCard label="Volatility" value={data.volatility_pct} unit="% ann." hint="annualised" />
      <StatCard label="Price Z-score" value={data.price_zscore}
        signal={data.price_anomaly ? 'bearish' : 'neutral'}
        hint={data.price_anomaly ? '⚠ anomaly detected' : 'within normal range'} />
      <StatCard label="Max Drawdown" value={data.max_drawdown_pct} unit="%" />
      {data.moving_averages?.sma_20 && (
        <StatCard label="SMA 20" value={data.moving_averages.sma_20} unit="₹" size="sm" />
      )}
      {data.moving_averages?.sma_50 && (
        <StatCard label="SMA 50" value={data.moving_averages.sma_50} unit="₹" size="sm" />
      )}
    </div>
  )
}
