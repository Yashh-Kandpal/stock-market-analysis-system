import { useState, useEffect } from 'react'
import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Legend
} from 'recharts'
import { stocksApi } from '../api/client'
import Loader from './Loader'
import './StockChart.css'

const INTERVALS = [
  { label: '5m', value: '5min', type: 'intraday' },
  { label: '15m', value: '15min', type: 'intraday' },
  { label: '30m', value: '30min', type: 'intraday' },
  { label: '1h', value: '60min', type: 'intraday' },
  { label: '1D', value: '1day', type: 'daily', days: 30 },
  { label: '3M', value: '3month', type: 'daily', days: 90 },
  { label: '1Y', value: '1year', type: 'daily', days: 365 },
]

function formatLabel(ts, type) {
  const d = new Date(ts)
  if (type === 'intraday') return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
  return d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div className="chart-tooltip">
      <div className="tt-time">{label}</div>
      <div className="tt-row"><span>Open</span><span>₹{d?.open?.toFixed(2)}</span></div>
      <div className="tt-row"><span>High</span><span className="up">₹{d?.high?.toFixed(2)}</span></div>
      <div className="tt-row"><span>Low</span><span className="down">₹{d?.low?.toFixed(2)}</span></div>
      <div className="tt-row"><span>Close</span><span>₹{d?.close?.toFixed(2)}</span></div>
      <div className="tt-row"><span>Volume</span><span>{parseInt(d?.volume || 0).toLocaleString('en-IN')}</span></div>
    </div>
  )
}

export default function StockChart({ symbol }) {
  const [selected, setSelected] = useState(INTERVALS[4]) // default 1D
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchData = async (iv) => {
    setLoading(true)
    setError(null)
    try {
      let res
      if (iv.type === 'intraday') {
        res = await stocksApi.getIntraday(symbol, iv.value)
      } else {
        res = await stocksApi.getDaily(symbol, iv.days || 30)
      }
      const chartData = res.data.map(d => ({
        ...d,
        label: formatLabel(d.timestamp, iv.type),
      }))
      setData(chartData)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load chart data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (symbol) fetchData(selected)
  }, [symbol, selected])

  const firstClose = data[0]?.close || 0
  const lastClose = data[data.length - 1]?.close || 0
  const lineColor = lastClose >= firstClose ? '#48bb78' : '#fc8181'

  return (
    <div className="stock-chart">
      <div className="chart-intervals">
        {INTERVALS.map(iv => (
          <button
            key={iv.value}
            className={`interval-btn ${selected.value === iv.value ? 'active' : ''}`}
            onClick={() => setSelected(iv)}
          >
            {iv.label}
          </button>
        ))}
        <button
          className="interval-btn refresh"
          onClick={() => fetchData({ ...selected, refresh: true })}
          title="Force refresh from API"
        >
          ↻
        </button>
      </div>

      {loading && <Loader text="Fetching market data..." />}
      {error && <div className="chart-error">{error}</div>}

      {!loading && !error && data.length > 0 && (
        <ResponsiveContainer width="100%" height={340}>
          <ComposedChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fill: 'var(--muted)', fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              yAxisId="price"
              domain={['auto', 'auto']}
              tick={{ fill: 'var(--muted)', fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={v => `₹${v.toLocaleString('en-IN')}`}
              width={80}
            />
            <YAxis
              yAxisId="volume"
              orientation="right"
              tick={{ fill: 'var(--muted)', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={v => `${(v / 1000).toFixed(0)}K`}
              width={50}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar yAxisId="volume" dataKey="volume" fill="var(--border)" opacity={0.5} radius={[2, 2, 0, 0]} />
            <Line
              yAxisId="price"
              type="monotone"
              dataKey="close"
              stroke={lineColor}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: lineColor }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}

      {!loading && !error && data.length === 0 && (
        <div className="chart-empty">No data available. Try refreshing.</div>
      )}
    </div>
  )
}
