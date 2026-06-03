import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, RefreshCw, AlertTriangle, ChevronDown, ChevronRight } from 'lucide-react'
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

// ─── helpers ──────────────────────────────────────────────────────────────────
const fmt = (v, d = 2) => (v == null ? '—' : Number(v).toFixed(d))
const fmtTs = ts => {
  const d = new Date(ts)
  return isNaN(d) ? ts : d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })
}

// ─── accordion panel wrapper ──────────────────────────────────────────────────
function AccordionPanel({ id, title, subtitle, badge, isOpen, onToggle, children, controls }) {
  return (
    <Card className={`analysis-panel accordion-panel ${isOpen ? 'open' : ''}`}>
      <div className="accordion-header" onClick={() => onToggle(id)}>
        <div className="accordion-left">
          <span className="accordion-icon">
            {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </span>
          <div>
            <div className="ap-title">{title}</div>
            {subtitle && <div className="ap-subtitle-small">{subtitle}</div>}
          </div>
        </div>
        <div className="accordion-right" onClick={e => e.stopPropagation()}>
          {badge && <span className="accordion-badge">{badge}</span>}
          {controls}
        </div>
      </div>
      {isOpen && <div className="accordion-body">{children}</div>}
    </Card>
  )
}

// ─── Moving Averages ──────────────────────────────────────────────────────────
function MovingAveragesPanel({ symbol, days, isOpen, onToggle }) {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(false)
  const [windows, setWindows] = useState('9,20,50,200')
  const [loaded, setLoaded] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setData(await analysisApi.movingAverages(symbol, days, windows))
      setLoaded(true)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [symbol, days, windows])

  useEffect(() => { if (isOpen && !loaded) load() }, [isOpen, loaded, load])
  useEffect(() => { setLoaded(false) }, [symbol, days])

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
    return Object.values(map).slice(-120)
  })()

  const MA_COLORS = { sma_9: '#a78bfa', sma_20: '#60a5fa', sma_50: '#34d399', sma_200: '#f97316', ema_9: '#c084fc', ema_20: '#93c5fd', ema_50: '#6ee7b7', ema_200: '#fdba74' }
  const activeKeys = Object.keys(MA_COLORS).filter(k => data?.series?.[k])

  return (
    <AccordionPanel id="ma" title="Moving Averages" subtitle="SMA & EMA with golden/death cross signals"
      isOpen={isOpen} onToggle={onToggle}
      badge={data?.signals?.length > 0 ? `${data.signals.length} signal${data.signals.length > 1 ? 's' : ''}` : null}
      controls={
        isOpen && (
          <div className="ap-win-input" onClick={e => e.stopPropagation()}>
            <input value={windows} onChange={e => setWindows(e.target.value)}
              placeholder="9,20,50,200" className="win-input" />
            <button className="ap-refresh-btn" onClick={load}><RefreshCw size={13} /></button>
          </div>
        )
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
    </AccordionPanel>
  )
}

// ─── Volatility ───────────────────────────────────────────────────────────────
function VolatilityPanel({ symbol, days, isOpen, onToggle }) {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(false)
  const [window_, setWindow] = useState(20)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    if (!isOpen || loaded) return
    setLoading(true)
    analysisApi.volatility(symbol, days, window_)
      .then(d => { setData(d); setLoaded(true) })
      .catch(console.error).finally(() => setLoading(false))
  }, [isOpen, loaded, symbol, days, window_])
  useEffect(() => { setLoaded(false) }, [symbol, days])

  const bbData = data?.bollinger_bands?.slice(-120) || []

  return (
    <AccordionPanel id="vol" title="Volatility & Bollinger Bands"
      subtitle="Annualised volatility, ATR, Bollinger %B"
      isOpen={isOpen} onToggle={onToggle}
      badge={data?.latest ? `${fmt(data.latest.annualised_volatility_pct)}% vol` : null}
      controls={
        isOpen && (
          <select className="ap-select" value={window_}
            onChange={e => { setWindow(+e.target.value); setLoaded(false) }}
            onClick={e => e.stopPropagation()}>
            {[10, 14, 20, 30, 50].map(w => <option key={w} value={w}>Window {w}</option>)}
          </select>
        )
      }
    >
      {loading ? <Loader text="Computing volatility…" /> : data && (
        <>
          <div className="stat-row">
            <StatCard label="Ann. Volatility" value={data.latest?.annualised_volatility_pct} unit="%" />
            <StatCard label="ATR" value={data.latest?.atr} unit="₹" hint={`${window_}-day`} />
            <StatCard label="BB Width" value={data.latest?.bandwidth} unit="%" />
            <StatCard label="Price Position" value={null} signal={data.interpretation?.position}
              hint={data.interpretation?.position?.replace(/_/g, ' ')} />
          </div>
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
    </AccordionPanel>
  )
}

// ─── RSI & MACD ───────────────────────────────────────────────────────────────
function RSIMACDPanel({ symbol, days, isOpen, onToggle }) {
  const [rsiData, setRsi]   = useState(null)
  const [macdData, setMacd] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    if (!isOpen || loaded) return
    setLoading(true)
    Promise.all([analysisApi.rsi(symbol, days), analysisApi.macd(symbol, days)])
      .then(([r, m]) => { setRsi(r); setMacd(m); setLoaded(true) })
      .catch(console.error).finally(() => setLoading(false))
  }, [isOpen, loaded, symbol, days])
  useEffect(() => { setLoaded(false) }, [symbol, days])

  const rsiSignalColor = rsiData?.signal === 'overbought' ? 'red' : rsiData?.signal === 'oversold' ? 'green' : 'muted'

  return (
    <AccordionPanel id="rsimacd" title="RSI & MACD"
      subtitle="Momentum indicators — overbought/oversold signals & crossovers"
      isOpen={isOpen} onToggle={onToggle}
      badge={rsiData ? `RSI ${fmt(rsiData.latest, 0)}` : null}
    >
      {loading ? <Loader text="Computing momentum indicators…" /> : (
        <>
          {rsiData && (
            <>
              <div className="stat-row">
                <StatCard label={`RSI (${rsiData.period})`} value={rsiData.latest}
                  signal={rsiData.signal}
                  hint={`OB: ${rsiData.levels.overbought} / OS: ${rsiData.levels.oversold}`} />
                {macdData && (
                  <>
                    <StatCard label="MACD"      value={macdData.latest?.macd} />
                    <StatCard label="Signal"    value={macdData.latest?.signal} />
                    <StatCard label="Histogram" value={macdData.latest?.histogram} signal={macdData.trend} />
                  </>
                )}
              </div>
              <h4 className="ap-subtitle">RSI</h4>
              <ResponsiveContainer width="100%" height={180}>
                <ComposedChart data={rsiData.series?.slice(-120).map(d => ({ ...d, ts: fmtTs(d.timestamp) }))}>
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
          {macdData && (
            <>
              <h4 className="ap-subtitle" style={{ marginTop: 20 }}>
                MACD ({macdData.params?.fast}/{macdData.params?.slow}/{macdData.params?.signal})
              </h4>
              <ResponsiveContainer width="100%" height={200}>
                <ComposedChart data={macdData.series?.slice(-120).map(d => ({ ...d, ts: fmtTs(d.timestamp) }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="ts" tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                  <YAxis tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }} />
                  <ReferenceLine y={0} stroke="var(--border)" />
                  <Bar dataKey="histogram" fill="#6c8ef7" opacity={0.5} isAnimationActive={false} name="Histogram" />
                  <Line type="monotone" dataKey="macd"   stroke="#60a5fa" dot={false} strokeWidth={1.5} name="MACD" />
                  <Line type="monotone" dataKey="signal" stroke="#f97316" dot={false} strokeWidth={1.5} name="Signal" />
                </ComposedChart>
              </ResponsiveContainer>
            </>
          )}
        </>
      )}
    </AccordionPanel>
  )
}

// ─── Anomaly Detection ────────────────────────────────────────────────────────
function AnomalyPanel({ symbol, days, isOpen, onToggle }) {
  const [data, setData]         = useState(null)
  const [loading, setLoading]   = useState(false)
  const [threshold, setThreshold] = useState(2.5)
  const [loaded, setLoaded]     = useState(false)

  useEffect(() => {
    if (!isOpen || loaded) return
    setLoading(true)
    analysisApi.anomalies(symbol, days, 20, threshold)
      .then(d => { setData(d); setLoaded(true) })
      .catch(console.error).finally(() => setLoading(false))
  }, [isOpen, loaded, symbol, days, threshold])
  useEffect(() => { setLoaded(false) }, [symbol, days])

  return (
    <AccordionPanel id="anomaly" title="Z-Score Anomaly Detection"
      subtitle="Flags unusual price and volume candles"
      isOpen={isOpen} onToggle={onToggle}
      badge={data ? `${data.summary?.price_anomaly_count} anomalies` : null}
      controls={
        isOpen && (
          <select className="ap-select" value={threshold}
            onChange={e => { setThreshold(+e.target.value); setLoaded(false) }}
            onClick={e => e.stopPropagation()}>
            {[1.5, 2.0, 2.5, 3.0, 3.5].map(t => <option key={t} value={t}>±{t}σ</option>)}
          </select>
        )
      }
    >
      {loading ? <Loader text="Detecting anomalies…" /> : data && (
        <>
          <div className="stat-row">
            <StatCard label="Price Anomalies"  value={data.summary?.price_anomaly_count}  hint={`|z| > ${threshold}σ`} />
            <StatCard label="Volume Anomalies" value={data.summary?.volume_anomaly_count} hint={`|z| > ${threshold}σ`} />
            <StatCard label="Combined"         value={data.summary?.combined_count}       hint="both price & volume" />
            <StatCard label="Total Candles"    value={data.summary?.total_candles} />
          </div>
          {data.zscore_series?.length > 0 && (
            <ResponsiveContainer width="100%" height={200}>
              <ComposedChart data={data.zscore_series.slice(-120).map(d => ({ ...d, ts: fmtTs(d.timestamp) }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="ts" tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                <YAxis tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }} />
                <ReferenceLine y={threshold}  stroke="var(--red)"   strokeDasharray="4 2" label={{ value: `+${threshold}σ`, fill: 'var(--red)',   fontSize: 10 }} />
                <ReferenceLine y={-threshold} stroke="var(--green)" strokeDasharray="4 2" label={{ value: `-${threshold}σ`, fill: 'var(--green)', fontSize: 10 }} />
                <ReferenceLine y={0} stroke="var(--border)" />
                <Line type="monotone" dataKey="price_z"  stroke="#60a5fa" dot={false} strokeWidth={1.5} name="Price Z" />
                <Line type="monotone" dataKey="volume_z" stroke="#f59e0b" dot={false} strokeWidth={1}   name="Volume Z" />
              </ComposedChart>
            </ResponsiveContainer>
          )}
          {data.combined_anomalies?.length > 0 && (
            <div className="anomaly-list">
              <h4 className="ap-subtitle"><AlertTriangle size={13} style={{ color: 'var(--yellow)' }} /> Combined Anomalies</h4>
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
    </AccordionPanel>
  )
}

// ─── Support & Resistance ─────────────────────────────────────────────────────
function SupportResistancePanel({ symbol, days, isOpen, onToggle }) {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    if (!isOpen || loaded) return
    setLoading(true)
    analysisApi.supportResistance(symbol, days)
      .then(d => { setData(d); setLoaded(true) })
      .catch(console.error).finally(() => setLoading(false))
  }, [isOpen, loaded, symbol, days])
  useEffect(() => { setLoaded(false) }, [symbol, days])

  const pp = data?.pivot_points
  const price = data?.current_price

  return (
    <AccordionPanel id="sr" title="Support & Resistance"
      subtitle="Pivot points R1–R3 and S1–S3"
      isOpen={isOpen} onToggle={onToggle}
      badge={pp ? `Pivot ₹${fmt(pp.pivot)}` : null}
    >
      {loading ? <Loader text="Computing levels…" /> : data && pp && (
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
      )}
    </AccordionPanel>
  )
}

// ─── Returns & Risk ───────────────────────────────────────────────────────────
function ReturnsPanel({ symbol, days, isOpen, onToggle }) {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    if (!isOpen || loaded) return
    setLoading(true)
    analysisApi.returns(symbol, Math.min(days, 365))
      .then(d => { setData(d); setLoaded(true) })
      .catch(console.error).finally(() => setLoading(false))
  }, [isOpen, loaded, symbol, days])
  useEffect(() => { setLoaded(false) }, [symbol, days])

  return (
    <AccordionPanel id="returns" title="Returns & Risk"
      subtitle="Sharpe ratio, max drawdown, skewness, win rate"
      isOpen={isOpen} onToggle={onToggle}
      badge={data ? `Sharpe ${fmt(data.sharpe_ratio)}` : null}
    >
      {loading ? <Loader text="Analysing returns…" /> : data && (
        <>
          <div className="stat-row">
            <StatCard label="Total Return"      value={data.total_return_pct}          unit="%" />
            <StatCard label="Ann. Return"       value={data.annualised_return_pct}     unit="%" />
            <StatCard label="Sharpe Ratio"      value={data.sharpe_ratio}              hint="rf = 6%" />
            <StatCard label="Max Drawdown"      value={data.max_drawdown_pct}          unit="%" />
            <StatCard label="Win Rate"          value={data.win_rate_pct}              unit="%" />
            <StatCard label="Daily Std Dev"     value={data.std_daily_return_pct}      unit="%" />
            <StatCard label="Skewness"          value={data.skewness}                  hint=">0 right-tailed" />
            <StatCard label="Kurtosis"          value={data.kurtosis}                  hint=">3 fat tails" />
          </div>
          <h4 className="ap-subtitle">Drawdown from Peak</h4>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={data.drawdown_series?.slice(-200).map(d => ({ ...d, ts: fmtTs(d.timestamp) }))}>
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
    </AccordionPanel>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
const ALL_PANELS = ['ma', 'vol', 'rsimacd', 'anomaly', 'sr', 'returns']

export default function AnalysisPage() {
  const { symbol } = useParams()
  const navigate   = useNavigate()
  const decoded    = decodeURIComponent(symbol)
  const [days, setDays]       = useState(180)
  const [openPanels, setOpen] = useState(new Set())

  const toggle = (id) => {
    setOpen(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const expandAll   = () => setOpen(new Set(ALL_PANELS))
  const collapseAll = () => setOpen(new Set())

  return (
    <div className="analysis-page">
      <div className="ap-topbar">
        <button className="back-btn" onClick={() => navigate(`/stock/${symbol}`)}>
          <ArrowLeft size={16} /> {decoded}
        </button>
        <div className="ap-topbar-right">
          <span className="ap-label">Timeframe:</span>
          <TimeframeSelector value={days} onChange={setDays} options={[
            { label: '3M', days: 90 },
            { label: '6M', days: 180 },
            { label: '1Y', days: 365 },
            { label: '2Y', days: 730 },
          ]} />
        </div>
      </div>

      <div className="ap-page-header">
        <div className="ap-header-row">
          <div>
            <h1>Statistical Analysis</h1>
            <p className="page-sub">{decoded} · {days}-day lookback · Click any section to expand</p>
          </div>
          <div className="ap-expand-btns">
            <button className="ap-expand-btn" onClick={expandAll}>Expand all</button>
            <button className="ap-expand-btn" onClick={collapseAll}>Collapse all</button>
          </div>
        </div>
      </div>

      <div className="analysis-accordion">
        <MovingAveragesPanel    symbol={decoded} days={days} isOpen={openPanels.has('ma')}      onToggle={toggle} />
        <VolatilityPanel        symbol={decoded} days={days} isOpen={openPanels.has('vol')}     onToggle={toggle} />
        <RSIMACDPanel           symbol={decoded} days={days} isOpen={openPanels.has('rsimacd')} onToggle={toggle} />
        <AnomalyPanel           symbol={decoded} days={days} isOpen={openPanels.has('anomaly')} onToggle={toggle} />
        <SupportResistancePanel symbol={decoded} days={days} isOpen={openPanels.has('sr')}      onToggle={toggle} />
        <ReturnsPanel           symbol={decoded} days={days} isOpen={openPanels.has('returns')} onToggle={toggle} />
      </div>
    </div>
  )
}
