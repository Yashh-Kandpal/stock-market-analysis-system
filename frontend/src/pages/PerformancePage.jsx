import { useState, useEffect } from 'react'
import { Info, CheckCircle, XCircle, Clock } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, LineChart, Line, Legend
} from 'recharts'
import { performanceApi } from '../api/client'
import Card from '../components/Card'
import Loader from '../components/Loader'
import TimeframeSelector from '../components/TimeframeSelector'
import './PerformancePage.css'

const fmt = (v, d = 1) => (v == null ? '—' : Number(v).toFixed(d))

// Default labels/colors for known models — unknown models get fallbacks
const MODEL_LABELS = {
  arima:   'ARIMA',
  xgboost: 'XGBoost',
  linear:  'Linear Regression',
  prophet: 'Prophet',
  lstm:    'LSTM',
}
const MODEL_COLORS_LIST = [
  '#6c8ef7', '#34d399', '#f59e0b', '#a78bfa',
  '#f97316', '#ec4899', '#14b8a6', '#84cc16',
]
// Assign colors dynamically
const _colorCache = {}
let   _colorIndex = 0
function getModelColor(model) {
  if (!_colorCache[model]) {
    _colorCache[model] = MODEL_COLORS_LIST[_colorIndex % MODEL_COLORS_LIST.length]
    _colorIndex++
  }
  return _colorCache[model]
}
function getModelLabel(model) {
  return MODEL_LABELS[model] || model.toUpperCase()
}

// ── small components ──────────────────────────────────────────────────────────

function AccuracyBar({ value }) {
  if (value == null) return <span className="perf-na">—</span>
  const color = value >= 60 ? 'var(--green)' : value >= 52 ? 'var(--yellow)' : 'var(--red)'
  return (
    <div className="acc-bar-wrap">
      <div className="acc-bar" style={{ width: `${Math.min(value, 100)}%`, background: color }} />
      <span className="acc-label" style={{ color }}>{fmt(value)}%</span>
    </div>
  )
}

function StatusDot({ pending, correct }) {
  if (pending) return <span className="status-dot pending" title="Awaiting actual"><Clock size={12} /></span>
  if (correct) return <span className="status-dot correct" title="Correct"><CheckCircle size={12} /></span>
  return <span className="status-dot wrong" title="Incorrect"><XCircle size={12} /></span>
}

// ── Overall strip ─────────────────────────────────────────────────────────────

function OverallStrip({ data }) {
  const o = data?.overall
  if (!o) return null
  return (
    <div className="overall-strip">
      {[
        { label: 'Total Predictions', value: o.total_predictions },
        { label: 'Evaluated',         value: o.filled_predictions },
        { label: 'Overall Accuracy',  value: o.directional_accuracy_pct != null ? `${fmt(o.directional_accuracy_pct)}%` : '—', accent: true },
        { label: 'Avg Price Error',   value: o.avg_price_error_pct != null ? `${fmt(o.avg_price_error_pct)}%` : '—' },
        { label: 'Tracked Stocks',    value: data?.tracked_symbols?.length ?? '—' },
        { label: 'Pending',           value: o.pending_predictions, muted: true },
      ].map(({ label, value, accent, muted }) => (
        <div key={label} className="os-item">
          <span className="os-label">{label}</span>
          <span className={`os-value ${accent ? 'accent' : ''} ${muted ? 'muted' : ''}`}>{value ?? '—'}</span>
        </div>
      ))}
    </div>
  )
}

// ── Model comparison table ────────────────────────────────────────────────────

function ModelSummaryTable({ data, days }) {
  const models  = data?.models || []
  const byModel = data?.by_model || {}

  if (models.length === 0) {
    return (
      <Card className="perf-card">
        <div className="perf-card-header"><h3>Model Comparison</h3></div>
        <div className="perf-empty">
          No predictions logged yet. Visit the ML Predictions page for any stock to start tracking accuracy.
        </div>
      </Card>
    )
  }

  const chartData = models.map(m => ({
    model:    getModelLabel(m),
    accuracy: byModel[m]?.directional_accuracy_pct,
    color:    getModelColor(m),
  }))

  return (
    <Card className="perf-card">
      <div className="perf-card-header">
        <h3>Model Comparison</h3>
        <span className="perf-subtitle">Last {days} days · all tracked stocks</span>
      </div>

      <div className="model-table-wrap">
        <table className="model-table">
          <thead>
            <tr>
              <th>Model</th>
              <th>Predictions</th>
              <th>Directional Accuracy</th>
              <th>UP Accuracy</th>
              <th>DOWN Accuracy</th>
              <th>Avg Price Error</th>
              <th>Recent 10</th>
              <th>Best Stock</th>
              <th>Worst Stock</th>
            </tr>
          </thead>
          <tbody>
            {models.map(model => {
              const s = byModel[model] || {}
              return (
                <tr key={model}>
                  <td>
                    <div className="model-name-cell">
                      <span className="model-dot" style={{ background: getModelColor(model) }} />
                      {getModelLabel(model)}
                    </div>
                  </td>
                  <td className="center">
                    <span className="pred-count">{s.filled_predictions ?? '—'}</span>
                    {s.pending_predictions > 0 && (
                      <span className="pred-pending">+{s.pending_predictions} pending</span>
                    )}
                  </td>
                  <td><AccuracyBar value={s.directional_accuracy_pct} /></td>
                  <td><AccuracyBar value={s.up_accuracy_pct} /></td>
                  <td><AccuracyBar value={s.down_accuracy_pct} /></td>
                  <td className="center">{fmt(s.avg_price_error_pct)}%</td>
                  <td><AccuracyBar value={s.recent_10_accuracy_pct} /></td>
                  <td className="sym-cell">
                    {s.best_stock
                      ? <><span className="sym">{s.best_stock.replace('.NS','')}</span><span className="sym-acc green">{s.best_stock_acc}%</span></>
                      : '—'}
                  </td>
                  <td className="sym-cell">
                    {s.worst_stock
                      ? <><span className="sym">{s.worst_stock.replace('.NS','')}</span><span className="sym-acc red">{s.worst_stock_acc}%</span></>
                      : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="model" tick={{ fill: 'var(--muted)', fontSize: 11 }} tickLine={false} axisLine={false} />
          <YAxis domain={[40, 80]} tick={{ fill: 'var(--muted)', fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={v => `${v}%`} />
          <Tooltip
            contentStyle={{ background: 'var(--tooltip-bg)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }}
            formatter={v => [`${fmt(v)}%`, 'Accuracy']}
          />
          <ReferenceLine y={50} stroke="var(--muted)" strokeDasharray="4 2"
            label={{ value: 'Random (50%)', fill: 'var(--muted)', fontSize: 10 }} />
          <Bar dataKey="accuracy" radius={[4,4,0,0]} fill="var(--accent)"
            label={{ position: 'top', fill: 'var(--muted)', fontSize: 10, formatter: v => v ? `${fmt(v)}%` : '' }} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  )
}

// ── Calibration ───────────────────────────────────────────────────────────────

function CalibrationPanel({ days }) {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [selModel, setSelModel] = useState('')

  useEffect(() => {
    setLoading(true)
    performanceApi.calibration(days)
      .then(d => { setData(d); if (!selModel && d.models?.length) setSelModel(d.models[0]) })
      .catch(console.error).finally(() => setLoading(false))
  }, [days])

  const models   = data?.models || []
  const calibData = data?.calibration?.[selModel] || []
  const chartData = calibData.map(b => ({
    bucket: b.bucket, confidence: b.mid_confidence, actual: b.actual_accuracy_pct, count: b.count,
  }))

  return (
    <Card className="perf-card">
      <div className="perf-card-header">
        <h3>Confidence Calibration</h3>
        {models.length > 0 && (
          <select className="perf-select" value={selModel} onChange={e => setSelModel(e.target.value)}>
            {models.map(m => <option key={m} value={m}>{getModelLabel(m)}</option>)}
          </select>
        )}
      </div>
      {loading ? <Loader text="Loading calibration…" /> : (
        <>
          <div className="calibration-note">
            <Info size={12} />
            A well-calibrated model with 65% confidence should be correct ~65% of the time.
          </div>
          {chartData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="confidence" tick={{ fill: 'var(--muted)', fontSize: 11 }}
                    tickLine={false} axisLine={false} tickFormatter={v => `${v}%`} />
                  <YAxis domain={[40, 80]} tick={{ fill: 'var(--muted)', fontSize: 11 }}
                    tickLine={false} axisLine={false} tickFormatter={v => `${v}%`} />
                  <Tooltip contentStyle={{ background: 'var(--tooltip-bg)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }}
                    formatter={(v, n) => [`${fmt(v)}%`, n]} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="confidence" stroke="var(--border)"
                    strokeDasharray="4 2" dot={false} name="Perfect calibration" />
                  <Line type="monotone" dataKey="actual" stroke={getModelColor(selModel)}
                    strokeWidth={2} dot={{ fill: getModelColor(selModel), r: 4 }} name="Actual accuracy" />
                </LineChart>
              </ResponsiveContainer>
              <table className="calib-table">
                <thead><tr><th>Range</th><th>Actual Accuracy</th><th>Count</th><th>Status</th></tr></thead>
                <tbody>
                  {calibData.map((b, i) => (
                    <tr key={i}>
                      <td>{b.bucket}</td>
                      <td className={b.actual_accuracy_pct >= b.mid_confidence ? 'green' : 'red'}>
                        {fmt(b.actual_accuracy_pct)}%
                      </td>
                      <td>{b.count}</td>
                      <td>
                        <span className={`calib-badge ${b.well_calibrated ? 'good' : 'bad'}`}>
                          {b.well_calibrated ? '✓ Well calibrated'
                            : b.actual_accuracy_pct > b.mid_confidence ? '↑ Underconfident' : '↓ Overconfident'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : (
            <div className="perf-empty">Not enough data yet for calibration analysis.</div>
          )}
        </>
      )}
    </Card>
  )
}

// ── Prediction log ────────────────────────────────────────────────────────────

function PredictionLogPanel({ days }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [modelFilter, setModel] = useState('')
  const [activeModels, setActiveModels] = useState([])

  useEffect(() => {
    performanceApi.summary(days)
      .then(d => setActiveModels(d.models || []))
      .catch(console.error)
  }, [days])

  useEffect(() => {
    setLoading(true)
    performanceApi.log(null, modelFilter || null, days, 100)
      .then(setData).catch(console.error).finally(() => setLoading(false))
  }, [days, modelFilter])

  const rows = data?.rows || []

  return (
    <Card className="perf-card">
      <div className="perf-card-header">
        <h3>Prediction Log</h3>
        <select className="perf-select" value={modelFilter} onChange={e => setModel(e.target.value)}>
          <option value="">All models</option>
          {activeModels.map(m => <option key={m} value={m}>{getModelLabel(m)}</option>)}
        </select>
      </div>
      {loading ? <Loader text="Loading log…" /> : rows.length === 0 ? (
        <div className="perf-empty">
          No predictions logged yet. Visit the ML Predictions page for any stock to start tracking.
        </div>
      ) : (
        <div className="log-table-wrap">
          <table className="log-table">
            <thead>
              <tr>
                <th>Date</th><th>Stock</th><th>Model</th>
                <th>Predicted</th><th>Confidence</th>
                <th>Actual</th><th>Price Error</th><th>Result</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(row => (
                <tr key={row.id}>
                  <td className="log-date">{row.prediction_date}</td>
                  <td className="log-sym">{row.symbol?.replace('.NS','')}</td>
                  <td>
                    <span className="model-tag" style={{ borderColor: getModelColor(row.model) }}>
                      {getModelLabel(row.model)}
                    </span>
                  </td>
                  <td className={row.predicted_direction === 'UP' ? 'up' : 'down'}>
                    {row.predicted_direction === 'UP' ? '▲' : '▼'} {row.predicted_direction}
                  </td>
                  <td>{row.confidence_pct ? `${fmt(row.confidence_pct)}%` : '—'}</td>
                  <td className={row.actual_direction === 'UP' ? 'up' : row.actual_direction === 'DOWN' ? 'down' : 'muted'}>
                    {row.pending
                      ? <span className="pending-tag">Pending</span>
                      : row.actual_direction === 'UP' ? '▲ UP' : '▼ DOWN'}
                  </td>
                  <td className="muted">{row.price_error_pct != null ? `${fmt(row.price_error_pct)}%` : '—'}</td>
                  <td><StatusDot pending={row.pending} correct={row.was_correct} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function PerformancePage() {
  const [summary, setSummary]   = useState(null)
  const [loading, setLoading]   = useState(true)
  const [days, setDays]         = useState(30)

  useEffect(() => {
    setLoading(true)
    performanceApi.summary(days)
      .then(setSummary).catch(console.error).finally(() => setLoading(false))
  }, [days])

  return (
    <div className="performance-page">
      <div className="perf-topbar">
        <div>
          <h1>Model Performance</h1>
          <p className="page-sub">Live prediction accuracy tracked against NSE closing prices</p>
        </div>
        <TimeframeSelector value={days} onChange={setDays} options={[
          { label: '2W', days: 14 },
          { label: '1M', days: 30 },
          { label: '2M', days: 60 },
          { label: '3M', days: 90 },
        ]} />
      </div>

      <div className="perf-disclaimer">
        <Info size={13} />
        <span>
          Predictions are logged when the ML page is visited, before market open.
          Actuals are fetched automatically from Yahoo Finance after each trading day closes.
          Past accuracy does not guarantee future performance.
          This system is for academic research only and does not constitute financial advice.
        </span>
      </div>

      {loading
        ? <Loader text="Loading performance data…" />
        : <>
            <OverallStrip data={summary} />
            <ModelSummaryTable data={summary} days={days} />
            <CalibrationPanel days={days} />
            <PredictionLogPanel days={days} />
          </>
      }
    </div>
  )
}
