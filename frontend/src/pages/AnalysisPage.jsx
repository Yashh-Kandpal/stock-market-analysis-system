import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, RefreshCw, AlertTriangle, TrendingUp, TrendingDown } from 'lucide-react'
import {
  LineChart, Line, BarChart, Bar, ComposedChart,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend, Area, AreaChart
} from 'recharts'

import { analysisApi } from '../api/client'
import Card from '../components/Card'
import Loader from '../components/Loader'
import StatCard from '../components/StatCard'
import TimeframeSelector from '../components/TimeframeSelector'
import './AnalysisPage.css'

// ─── tiny helpers ──────────────────────────────────────────────────────────
const fmt = (v, d = 2) => (v == null ? '—' : Number(v).toFixed(d))
const fmtTs = ts => {
  const d = new Date(ts)
  return isNaN(d) ? ts : d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })
}
const Panel = ({ title, children, controls }) => (
  <Card className="analysis-panel">
    <div className="ap-header">
      <h3 className="ap-title">{title}</h3>
      {controls && <div className="ap-controls">{controls}</div>}
    </div>
    {children}
  </Card>
)

// ─── sub-panels ────────────────────────────────────────────────────────────

function MovingAveragesPanel({ symbol, days }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [windows, setWindows] = useState('9,20,50,200')

  const load = useCallback(async () => {
    setLoading(true)
    try { setData(await analysisApi.movingAverages(symbol, days, windows)) }
    catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [symbol, days, windows])

  useEffect(() => { load() }, [load])

  // Merge all MA series by timestamp for a single chart dataset
  const chartData = (() => {
    if (!data?.series) return []
    const map = {}
    Object.entries(data.series).forEach(([key, arr]) => {
      arr.forEach(({ timestamp, value }) => {
        const ts = fmtTs(timestamp)
        if (!map[ts]) map[ts] = { ts }
        map[ts][key] = value
      })
    })
    return Object.values(map).slice(-120) // last 120 points for readability
  })()

  const MA_COLORS = { sma_9: '#a78bfa', sma_20: '#60a5fa', sma_50: '#34d399', sma_200: '#f97316', ema_9: '#c084fc', ema_20: '#93c5fd', ema_50: '#6ee7b7', ema_200: '#fdba74' }
  const activeKeys = Object.keys(MA_COLORS).filter(k => data?.series?.[k])

  return (
    <Panel title="Moving Averages"
      controls={
        <div className="ap-win-input">
          <input value={windows} onChange={e => setWindows(e.target.value)}
            placeholder="9,20,50,200" className="win-input" />
          <button className="ap-refresh-btn" onClick={load}><RefreshCw size={13} /></button>
        </div>
      }
    >
      {loading ? <Loader text="Computing MAs…" /> : (
        <>
          <div className="stat-row">
            {data?.latest && Object.entries(data.latest).map(([k, v]) => (
              <StatCard key={k} label={k.replace('_', ' ').toUpperCase()} value={v} unit="₹" size="sm" />
            ))}
          </div>

          {data?.signals?.length > 0 && (
            <div className="signal-badges">
              {data.signals.map((s, i) => (
                <div key={i} className={`signal-badge ${s.type.includes('golden') ? 'green' : 'red'}`}>
                  {s.type === 'golden_cross' ? '🟢' : '🔴'} {s.description} ({s.date})
                </div>
              ))}
            </div>
          )}

          {chartData.length > 0 && (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="ts" tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                <YAxis tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={v => `₹${v.toLocaleString('en-IN')}`} width={72} />
                <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }} />
                <Legend wrapperStyle={{ fontSize: 11, color: 'var(--muted)' }} />
                {activeKeys.map(k => (
                  <Line key={k} dataKey={k} stroke={MA_COLORS[k]} dot={false} strokeWidth={1.5} name={k.replace('_', ' ')} connectNulls />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </>
      )}
    </Panel>
  )
}

function VolatilityPanel({ symbol, days }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [window_, setWindow] = useState(20)

  useEffect(() => {
    setLoading(true)
    analysisApi.volatility(symbol, days, window_)
      .then(setData).catch(console.error).finally(() => setLoading(false))
  }, [symbol, days, window_])

  const bbData = data?.bollinger_bands?.slice(-120) || []

  return (
    <Panel title="Volatility & Bollinger Bands"
      controls={
        <select className="ap-select" value={window_} onChange={e => setWindow(+e.target.value)}>
          {[10, 14, 20, 30, 50].map(w => <option key={w} value={w}>Window {w}</option>)}
        </select>
      }
    >
      {loading ? <Loader text="Computing volatility…" /> : data && (
        <>
          <div className="stat-row">
            <StatCard label="Ann. Volatility" value={data.latest?.annualised_volatility_pct} unit="%" />
            <StatCard label="ATR" value={data.latest?.atr} unit="₹" hint={`${window_}-day avg true range`} />
            <StatCard label="BB Width" value={data.latest?.bandwidth} unit="%" hint="band squeeze indicator" />
            <StatCard label="Price Position" value={null}
              signal={data.interpretation?.position}
              hint={data.interpretation?.position?.replace(/_/g, ' ')} />
          </div>

          <h4 className="ap-subtitle">Bollinger Bands</h4>
          {bbData.length > 0 && (
            <ResponsiveContainer width="100%" height={240}>
              <ComposedChart data={bbData.map(d => ({ ...d, ts: fmtTs(d.timestamp) }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="ts" tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                <YAxis tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={v => `₹${v.toLocaleString('en-IN')}`} width={72} />
                <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }} />
                <Area type="monotone" dataKey="upper" stroke="#6c8ef7" fill="#6c8ef720" strokeWidth={1} name="Upper" />
                <Area type="monotone" dataKey="lower" stroke="#6c8ef7" fill="#6c8ef720" strokeWidth={1} name="Lower" />
                <Line type="monotone" dataKey="mid"   stroke="#6c8ef7" dot={false} strokeWidth={1} strokeDasharray="4 2" name="Mid" />
                <Line type="monotone" dataKey="close" stroke="#e2e8f0" dot={false} strokeWidth={2} name="Close" />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </>
      )}
    </Panel>
  )
}

function AnomalyPanel({ symbol, days }) {
  const [data, setData]         = useState(null)
  const [loading, setLoading]   = useState(false)
  const [threshold, setThreshold] = useState(2.5)

  useEffect(() => {
    setLoading(true)
    analysisApi.anomalies(symbol, days, 20, threshold)
      .then(setData).catch(console.error).finally(() => setLoading(false))
  }, [symbol, days, threshold])

  const zData = data?.zscore_series?.slice(-120) || []

  return (
    <Panel title="Z-Score Anomaly Detection"
      controls={
        <select className="ap-select" value={threshold} onChange={e => setThreshold(+e.target.value)}>
          {[1.5, 2.0, 2.5, 3.0, 3.5].map(t => <option key={t} value={t}>±{t}σ</option>)}
        </select>
      }
    >
      {loading ? <Loader text="Detecting anomalies…" /> : data && (
        <>
          <div className="stat-row">
            <StatCard label="Price Anomalies" value={data.summary.price_anomaly_count} hint={`|z| > ${threshold}σ`} />
            <StatCard label="Volume Anomalies" value={data.summary.volume_anomaly_count} hint={`|z| > ${threshold}σ`} />
            <StatCard label="Combined" value={data.summary.combined_count} hint="both price & volume" />
            <StatCard label="Total Candles" value={data.summary.total_candles} />
          </div>

          {zData.length > 0 && (
            <>
              <h4 className="ap-subtitle">Rolling Z-Score</h4>
              <ResponsiveContainer width="100%" height={200}>
                <ComposedChart data={zData.map(d => ({ ...d, ts: fmtTs(d.timestamp) }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="ts" tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                  <YAxis tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }} />
                  <ReferenceLine y={threshold}  stroke="var(--red)"   strokeDasharray="4 2" label={{ value: `+${threshold}σ`, fill: 'var(--red)', fontSize: 10 }} />
                  <ReferenceLine y={-threshold} stroke="var(--green)" strokeDasharray="4 2" label={{ value: `-${threshold}σ`, fill: 'var(--green)', fontSize: 10 }} />
                  <ReferenceLine y={0} stroke="var(--border)" />
                  <Line type="monotone" dataKey="price_z"  stroke="#60a5fa" dot={false} strokeWidth={1.5} name="Price Z" />
                  <Line type="monotone" dataKey="volume_z" stroke="#f59e0b" dot={false} strokeWidth={1}   name="Volume Z" />
                </ComposedChart>
              </ResponsiveContainer>
            </>
          )}

          {data.combined_anomalies?.length > 0 && (
            <div className="anomaly-list">
              <h4 className="ap-subtitle">
                <AlertTriangle size={13} style={{ color: 'var(--yellow)' }} /> Combined Anomalies
              </h4>
              <table className="anomaly-table">
                <thead><tr><th>Date</th><th>Close</th><th>Price Z</th><th>Volume Z</th><th>Significance</th></tr></thead>
                <tbody>
                  {data.combined_anomalies.slice(-15).map((a, i) => (
                    <tr key={i}>
                      <td>{fmtTs(a.timestamp)}</td>
                      <td>₹{fmt(a.close)}</td>
                      <td className={a.price_z > 0 ? 'up' : 'down'}>{fmt(a.price_z, 2)}σ</td>
                      <td className={a.volume_z > 0 ? 'up' : 'down'}>{fmt(a.volume_z, 2)}σ</td>
                      <td><span className={`badge ${a.significance}`}>{a.significance}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </Panel>
  )
}

function RSIMACDPanel({ symbol, days }) {
  const [rsiData, setRsi]   = useState(null)
  const [macdData, setMacd] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      analysisApi.rsi(symbol, days),
      analysisApi.macd(symbol, days),
    ]).then(([r, m]) => { setRsi(r); setMacd(m) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [symbol, days])

  const rsiChartData  = rsiData?.series?.slice(-120)  || []
  const macdChartData = macdData?.series?.slice(-120) || []

  return (
    <Panel title="RSI & MACD">
      {loading ? <Loader text="Computing momentum indicators…" /> : (
        <>
          {/* RSI */}
          {rsiData && (
            <>
              <div className="stat-row">
                <StatCard label={`RSI (${rsiData.period})`} value={rsiData.latest}
                  signal={rsiData.signal}
                  hint={`OB: ${rsiData.levels.overbought} / OS: ${rsiData.levels.oversold}`} />
                {macdData && (
                  <>
                    <StatCard label="MACD" value={macdData.latest?.macd} />
                    <StatCard label="Signal" value={macdData.latest?.signal} />
                    <StatCard label="Histogram" value={macdData.latest?.histogram}
                      signal={macdData.trend} />
                  </>
                )}
              </div>

              <h4 className="ap-subtitle">RSI</h4>
              <ResponsiveContainer width="100%" height={180}>
                <ComposedChart data={rsiChartData.map(d => ({ ...d, ts: fmtTs(d.timestamp) }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="ts" tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                  <YAxis domain={[0, 100]} tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }} />
                  <ReferenceLine y={70} stroke="var(--red)"   strokeDasharray="3 3" label={{ value: 'OB 70', fill: 'var(--red)',   fontSize: 9 }} />
                  <ReferenceLine y={30} stroke="var(--green)" strokeDasharray="3 3" label={{ value: 'OS 30', fill: 'var(--green)', fontSize: 9 }} />
                  <ReferenceLine y={50} stroke="var(--border)" />
                  <Line type="monotone" dataKey="value" stroke="#a78bfa" dot={false} strokeWidth={2} name="RSI" />
                </ComposedChart>
              </ResponsiveContainer>
            </>
          )}

          {/* MACD */}
          {macdData && (
            <>
              <h4 className="ap-subtitle" style={{ marginTop: 20 }}>MACD ({macdData.params.fast}/{macdData.params.slow}/{macdData.params.signal})</h4>
              <ResponsiveContainer width="100%" height={200}>
                <ComposedChart data={macdChartData.map(d => ({ ...d, ts: fmtTs(d.timestamp) }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="ts" tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                  <YAxis tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }} />
                  <ReferenceLine y={0} stroke="var(--border)" />
                  <Bar dataKey="histogram" name="Histogram"
                    fill="#6c8ef7" opacity={0.5}
                    label={false}
                    // color bars by sign
                    isAnimationActive={false}
                  />
                  <Line type="monotone" dataKey="macd"   stroke="#60a5fa" dot={false} strokeWidth={1.5} name="MACD" />
                  <Line type="monotone" dataKey="signal" stroke="#f97316" dot={false} strokeWidth={1.5} name="Signal" />
                </ComposedChart>
              </ResponsiveContainer>
            </>
          )}
        </>
      )}
    </Panel>
  )
}

function SupportResistancePanel({ symbol, days }) {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    analysisApi.supportResistance(symbol, days)
      .then(setData).catch(console.error).finally(() => setLoading(false))
  }, [symbol, days])

  if (loading) return <Panel title="Support & Resistance"><Loader text="Computing levels…" /></Panel>
  if (!data)   return null

  const pp = data.pivot_points
  const price = data.current_price

  return (
    <Panel title="Support & Resistance">
      <div className="sr-grid">
        <div className="sr-col">
          <div className="sr-col-title resist">Resistance</div>
          {[pp.r3, pp.r2, pp.r1].map((v, i) => (
            <div key={i} className={`sr-level resist ${price > v ? 'breached' : ''}`}>
              <span className="sr-label">R{3 - i}</span>
              <span className="sr-price">₹{fmt(v)}</span>
              {price > v && <span className="sr-tag">✓ above</span>}
            </div>
          ))}
        </div>

        <div className="sr-pivot">
          <div className="sr-pivot-label">Pivot</div>
          <div className="sr-pivot-price">₹{fmt(pp.pivot)}</div>
          <div className="sr-current">Current: ₹{fmt(price)}</div>
        </div>

        <div className="sr-col">
          <div className="sr-col-title support">Support</div>
          {[pp.s1, pp.s2, pp.s3].map((v, i) => (
            <div key={i} className={`sr-level support ${price < v ? 'breached' : ''}`}>
              <span className="sr-label">S{i + 1}</span>
              <span className="sr-price">₹{fmt(v)}</span>
              {price < v && <span className="sr-tag">✓ below</span>}
            </div>
          ))}
        </div>
      </div>
    </Panel>
  )
}

function ReturnsPanel({ symbol, days }) {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    analysisApi.returns(symbol, Math.min(days, 365))
      .then(setData).catch(console.error).finally(() => setLoading(false))
  }, [symbol, days])

  const ddData = data?.drawdown_series?.slice(-200) || []

  return (
    <Panel title="Returns & Risk">
      {loading ? <Loader text="Analysing returns…" /> : data && (
        <>
          <div className="stat-row">
            <StatCard label="Total Return"     value={data.total_return_pct}         unit="%" />
            <StatCard label="Ann. Return"      value={data.annualised_return_pct}    unit="%" />
            <StatCard label="Sharpe Ratio"     value={data.sharpe_ratio}             hint="rf = 6%" />
            <StatCard label="Max Drawdown"     value={data.max_drawdown_pct}         unit="%" />
            <StatCard label="Win Rate"         value={data.win_rate_pct}             unit="%" />
            <StatCard label="Daily Std Dev"    value={data.std_daily_return_pct}     unit="%" />
            <StatCard label="Skewness"         value={data.skewness}                 hint=">0 right-tailed" />
            <StatCard label="Kurtosis"         value={data.kurtosis}                 hint=">3 fat tails" />
          </div>

          <h4 className="ap-subtitle">Drawdown from Peak</h4>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={ddData.map(d => ({ ...d, ts: fmtTs(d.timestamp) }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="ts" tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={v => `${v.toFixed(0)}%`} />
              <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }} formatter={v => [`${fmt(v)}%`, 'Drawdown']} />
              <ReferenceLine y={0} stroke="var(--border)" />
              <Area type="monotone" dataKey="drawdown_pct" stroke="var(--red)" fill="rgba(252,129,129,0.15)" strokeWidth={1.5} name="Drawdown" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </>
      )}
    </Panel>
  )
}

// ─── main page ─────────────────────────────────────────────────────────────

export default function AnalysisPage() {
  const { symbol } = useParams()
  const navigate   = useNavigate()
  const decoded    = decodeURIComponent(symbol)
  const [days, setDays] = useState(180)

  return (
    <div className="analysis-page">
      <div className="ap-topbar">
        <button className="back-btn" onClick={() => navigate(`/stock/${symbol}`)}>
          <ArrowLeft size={16} /> {decoded}
        </button>
        <div className="ap-topbar-right">
          <span className="ap-label">Timeframe:</span>
          <TimeframeSelector value={days} onChange={setDays} />
        </div>
      </div>

      <div className="ap-page-header">
        <h1>Statistical Analysis</h1>
        <p className="page-sub">{decoded} · {days}-day lookback window</p>
      </div>

      <div className="analysis-grid">
        <div className="analysis-col-wide">
          <MovingAveragesPanel symbol={decoded} days={days} />
          <VolatilityPanel     symbol={decoded} days={days} />
          <RSIMACDPanel        symbol={decoded} days={days} />
          <AnomalyPanel        symbol={decoded} days={days} />
        </div>
        <div className="analysis-col-narrow">
          <SupportResistancePanel symbol={decoded} days={days} />
          <ReturnsPanel           symbol={decoded} days={days} />
        </div>
      </div>
    </div>
  )
}
