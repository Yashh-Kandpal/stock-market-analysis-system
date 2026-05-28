import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, RefreshCw, Info } from 'lucide-react'
import {
  ComposedChart, Line, Area, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Legend, AreaChart, Scatter
} from 'recharts'

import { mlApi } from '../api/client'
import Card from '../components/Card'
import Loader from '../components/Loader'
import StatCard from '../components/StatCard'
import TimeframeSelector from '../components/TimeframeSelector'
import PredictionBadge from '../components/PredictionBadge'
import './MLPage.css'

const fmt = (v, d = 2) => (v == null ? '—' : Number(v).toFixed(d))
const fmtDate = ts => {
  const d = new Date(ts)
  return isNaN(d) ? ts : d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })
}

const Panel = ({ title, subtitle, children, controls, loading, onRefresh }) => (
  <Card className="ml-panel">
    <div className="mp-header">
      <div>
        <h3 className="mp-title">{title}</h3>
        {subtitle && <p className="mp-subtitle">{subtitle}</p>}
      </div>
      <div className="mp-controls">
        {controls}
        {onRefresh && (
          <button className="mp-refresh" onClick={onRefresh} title="Refresh">
            <RefreshCw size={13} className={loading ? 'spinning' : ''} />
          </button>
        )}
      </div>
    </div>
    {loading ? <Loader text="Training model…" /> : children}
  </Card>
)

// ─── ARIMA Panel ──────────────────────────────────────────────────────────────
function ARIMAPanel({ symbol, days }) {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(false)
  const [fcDays, setFcDays] = useState(14)

  const load = async () => {
    setLoading(true)
    try { setData(await mlApi.arima(symbol, days, fcDays)) }
    catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [symbol, days, fcDays])

  const chartData = [
    ...(data?.historical || []).map(d => ({
      date: fmtDate(d.date), actual: d.actual, type: 'historical'
    })),
    ...(data?.forecast || []).map(d => ({
      date:       fmtDate(d.date),
      predicted:  d.predicted,
      lower:      d.lower_95,
      upper:      d.upper_95,
      type:       'forecast'
    })),
  ]

  const lastActual    = data?.historical?.[data.historical.length - 1]?.actual
  const firstForecast = data?.forecast?.[0]?.predicted
  const forecastUp    = firstForecast > lastActual

  return (
    <Panel title="ARIMA Price Forecast"
      subtitle={`Auto-selected order: ${data ? `(${data.order?.join(',')})` : '…'} · AIC: ${data?.aic ?? '…'}`}
      loading={loading}
      onRefresh={load}
      controls={
        <select className="mp-select" value={fcDays} onChange={e => setFcDays(+e.target.value)}>
          {[7, 14, 21, 30].map(d => <option key={d} value={d}>{d}d forecast</option>)}
        </select>
      }
    >
      {data && (
        <>
          <div className="mp-stat-row">
            <StatCard label="RMSE"  value={data.metrics?.rmse}  unit="₹" hint="Root mean sq error" />
            <StatCard label="MAE"   value={data.metrics?.mae}   unit="₹" hint="Mean absolute error" />
            <StatCard label="MAPE"  value={data.metrics?.mape}  unit="%" hint="Mean abs % error" />
            <div className="mp-pred-cell">
              <div className="mp-pred-label">Forecast trend</div>
              <PredictionBadge direction={forecastUp ? 'UP' : 'DOWN'} />
            </div>
          </div>

          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false}
                tickFormatter={v => `₹${v.toLocaleString('en-IN')}`} width={80} />
              <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }}
                formatter={(v, n) => [`₹${fmt(v)}`, n]} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {/* Confidence band */}
              <Area type="monotone" dataKey="upper" stroke="none" fill="#6c8ef730" name="95% CI" />
              <Area type="monotone" dataKey="lower" stroke="none" fill="var(--bg)"  name="" legendType="none" />
              <Line type="monotone" dataKey="actual"    stroke="#e2e8f0" dot={false} strokeWidth={2} name="Actual" connectNulls />
              <Line type="monotone" dataKey="predicted" stroke="#6c8ef7" dot={false} strokeWidth={2}
                strokeDasharray="5 3" name="Forecast" connectNulls />
            </ComposedChart>
          </ResponsiveContainer>

          <div className="forecast-table-wrap">
            <table className="forecast-table">
              <thead><tr><th>Date</th><th>Predicted</th><th>Lower 95%</th><th>Upper 95%</th></tr></thead>
              <tbody>
                {data.forecast?.slice(0, 7).map((r, i) => (
                  <tr key={i}>
                    <td>{fmtDate(r.date)}</td>
                    <td className={r.predicted >= (data.forecast[i - 1]?.predicted ?? data.last_actual) ? 'up' : 'down'}>
                      ₹{fmt(r.predicted)}
                    </td>
                    <td className="muted">₹{fmt(r.lower_95)}</td>
                    <td className="muted">₹{fmt(r.upper_95)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Panel>
  )
}

// ─── Linear Regression Panel ──────────────────────────────────────────────────
function LinearPanel({ symbol, days }) {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    mlApi.linear(symbol, days)
      .then(setData).catch(console.error).finally(() => setLoading(false))
  }, [symbol, days])

  return (
    <Panel title="Linear & Logistic Regression"
      subtitle="Ridge regression for return magnitude · Logistic for direction"
      loading={loading}
    >
      {data && (
        <>
          <div className="mp-pred-row">
            <PredictionBadge
              direction={data.prediction?.direction}
              confidence={data.prediction?.confidence_pct}
              label="tomorrow"
            />
            <div className="mp-pred-details">
              <div className="mp-detail">
                <span>Predicted return</span>
                <span className={data.prediction?.predicted_return_pct >= 0 ? 'up' : 'down'}>
                  {data.prediction?.predicted_return_pct >= 0 ? '+' : ''}{fmt(data.prediction?.predicted_return_pct, 3)}%
                </span>
              </div>
              <div className="mp-detail">
                <span>Predicted price</span>
                <span>₹{fmt(data.prediction?.predicted_price)}</span>
              </div>
              <div className="mp-detail">
                <span>Prob. up</span>
                <span>{fmt(data.prediction?.prob_up_pct)}%</span>
              </div>
            </div>
          </div>

          <div className="mp-stat-row">
            <StatCard label="Direction Accuracy" value={data.metrics?.direction_accuracy_pct} unit="%" hint="on test set" />
            <StatCard label="CV Accuracy"         value={data.metrics?.cv_accuracy_mean_pct}  unit="%" hint="5-fold time series CV" />
            <StatCard label="CV Std Dev"          value={data.metrics?.cv_accuracy_std_pct}   unit="%" hint="lower = more stable" />
            <StatCard label="Regression RMSE"     value={data.metrics?.regression_rmse}       unit="%" hint="next-day return error" />
          </div>

          <h4 className="mp-section-title">Top Predictive Features</h4>
          <div className="feature-bars">
            {data.top_features?.slice(0, 10).map((f, i) => {
              const maxImp = data.top_features[0]?.importance || 1
              return (
                <div key={i} className="feat-row">
                  <span className="feat-name">{f.feature}</span>
                  <div className="feat-bar-wrap">
                    <div className="feat-bar" style={{ width: `${(f.importance / maxImp) * 100}%` }} />
                  </div>
                  <span className="feat-val">{fmt(f.importance, 4)}</span>
                </div>
              )
            })}
          </div>
        </>
      )}
    </Panel>
  )
}

// ─── XGBoost Panel ────────────────────────────────────────────────────────────
function XGBoostPanel({ symbol, days }) {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    mlApi.xgboost(symbol, days)
      .then(setData).catch(console.error).finally(() => setLoading(false))
  }, [symbol, days])

  return (
    <Panel title="XGBoost"
      subtitle="Gradient boosted trees · Next-day + 5-day direction prediction"
      loading={loading}
    >
      {data && (
        <>
          <div className="mp-pred-row">
            <div className="pred-group">
              <div className="pred-group-label">Tomorrow</div>
              <PredictionBadge
                direction={data.prediction?.direction}
                confidence={data.prediction?.confidence_pct}
                label={data.prediction?.confidence_label}
              />
            </div>
            <div className="pred-group">
              <div className="pred-group-label">5-Day Outlook</div>
              <PredictionBadge
                direction={data.prediction?.pred_5d_return_pct >= 0 ? 'UP' : 'DOWN'}
                label={`${data.prediction?.pred_5d_return_pct >= 0 ? '+' : ''}${fmt(data.prediction?.pred_5d_return_pct)}%`}
              />
            </div>
            <div className="mp-pred-details">
              <div className="mp-detail"><span>5d target price</span><span>₹{fmt(data.prediction?.pred_5d_price)}</span></div>
              <div className="mp-detail"><span>Prob. up</span><span>{fmt(data.prediction?.prob_up_pct)}%</span></div>
            </div>
          </div>

          <div className="mp-stat-row">
            <StatCard label="Direction Accuracy"    value={data.metrics?.direction_accuracy_pct}    unit="%" hint="next-day, test set" />
            <StatCard label="5d Direction Accuracy" value={data.metrics?.['5d_direction_accuracy_pct']} unit="%" hint="5-day outlook" />
            <StatCard label="CV Accuracy"           value={data.metrics?.cv_accuracy_mean_pct}      unit="%" hint="5-fold CV" />
            <StatCard label="CV Std Dev"            value={data.metrics?.cv_accuracy_std_pct}       unit="%" />
          </div>

          <h4 className="mp-section-title">Feature Importance (XGBoost gain)</h4>
          <div className="feature-bars">
            {data.top_features?.slice(0, 12).map((f, i) => {
              const maxImp = data.top_features[0]?.importance || 1
              return (
                <div key={i} className="feat-row">
                  <span className="feat-name">{f.feature}</span>
                  <div className="feat-bar-wrap">
                    <div className="feat-bar xgb" style={{ width: `${(f.importance / maxImp) * 100}%` }} />
                  </div>
                  <span className="feat-val">{fmt(f.importance, 4)}</span>
                </div>
              )
            })}
          </div>
        </>
      )}
    </Panel>
  )
}

// ─── Isolation Forest Panel ───────────────────────────────────────────────────
function IsolationForestPanel({ symbol, days }) {
  const [data, setData]         = useState(null)
  const [loading, setLoading]   = useState(false)
  const [contamination, setCont] = useState(0.05)

  useEffect(() => {
    setLoading(true)
    mlApi.isolationForest(symbol, days, contamination)
      .then(setData).catch(console.error).finally(() => setLoading(false))
  }, [symbol, days, contamination])

  const scoreData = data?.score_series?.slice(-200) || []

  return (
    <Panel title="Isolation Forest Anomaly Detection"
      subtitle="Multi-dimensional anomaly detection across all technical indicators"
      loading={loading}
      controls={
        <select className="mp-select" value={contamination}
          onChange={e => setCont(parseFloat(e.target.value))}>
          {[0.03, 0.05, 0.08, 0.10, 0.15].map(c =>
            <option key={c} value={c}>{(c * 100).toFixed(0)}% anomalies</option>)}
        </select>
      }
    >
      {data && (
        <>
          <div className="mp-stat-row">
            <StatCard label="Anomalies Found"  value={data.summary?.anomaly_count} hint={`${data.summary?.anomaly_pct}% of days`} />
            <StatCard label="Severe"           value={data.summary?.severe_count}  />
            <StatCard label="Moderate"         value={data.summary?.moderate_count} />
            <StatCard label="IF-only Anomalies" value={data.vs_zscore?.if_only_count}
              hint="missed by Z-score" />
          </div>

          <div className="if-note">
            <Info size={12} />
            {data.vs_zscore?.note}
          </div>

          {scoreData.length > 0 && (
            <>
              <h4 className="mp-section-title">Anomaly Score Over Time</h4>
              <ResponsiveContainer width="100%" height={200}>
                <ComposedChart data={scoreData.map(d => ({ ...d, date: fmtDate(d.date) }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="date" tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                  <YAxis tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} domain={[0, 100]} />
                  <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }} />
                  <ReferenceLine y={50} stroke="var(--yellow)" strokeDasharray="4 2"
                    label={{ value: 'threshold', fill: 'var(--yellow)', fontSize: 9 }} />
                  <Area type="monotone" dataKey="anomaly_score" stroke="#6c8ef7"
                    fill="#6c8ef720" strokeWidth={1.5} name="Anomaly Score" dot={false} />
                  <Scatter dataKey="anomaly_score"
                    data={scoreData.filter(d => d.is_anomaly).map(d => ({ ...d, date: fmtDate(d.date) }))}
                    fill="var(--red)" name="Anomaly" />
                </ComposedChart>
              </ResponsiveContainer>
            </>
          )}

          {data.anomalies?.length > 0 && (
            <>
              <h4 className="mp-section-title">Most Significant Anomalies</h4>
              <table className="anomaly-table">
                <thead>
                  <tr><th>Date</th><th>Close</th><th>Return</th><th>Vol Ratio</th><th>Score</th><th>Severity</th><th>Drivers</th></tr>
                </thead>
                <tbody>
                  {data.anomalies.slice(0, 10).map((a, i) => (
                    <tr key={i}>
                      <td>{fmtDate(a.date)}</td>
                      <td>₹{fmt(a.close)}</td>
                      <td className={a.return_pct >= 0 ? 'up' : 'down'}>{a.return_pct >= 0 ? '+' : ''}{fmt(a.return_pct)}%</td>
                      <td>{fmt(a.volume_ratio)}x</td>
                      <td>{fmt(a.anomaly_score, 1)}</td>
                      <td><span className={`severity-badge ${a.severity}`}>{a.severity}</span></td>
                      <td className="drivers">{a.top_drivers?.join(', ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </>
      )}
    </Panel>
  )
}

// ─── Prophet Panel ────────────────────────────────────────────────────────────
function ProphetPanel({ symbol, days }) {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(false)
  const [fcDays, setFcDays] = useState(30)

  useEffect(() => {
    setLoading(true)
    mlApi.prophet(symbol, Math.max(days, 365), fcDays)
      .then(setData).catch(console.error).finally(() => setLoading(false))
  }, [symbol, days, fcDays])

  const chartData = [
    ...(data?.historical?.slice(-90) || []).map(d => ({
      date: fmtDate(d.date), actual: d.actual, fitted: d.fitted
    })),
    ...(data?.forecast || []).map(d => ({
      date: fmtDate(d.date), predicted: d.predicted,
      lower: d.lower_95, upper: d.upper_95
    })),
  ]

  return (
    <Panel title="Prophet Forecast"
      subtitle="Trend + weekly + yearly + monthly seasonality"
      loading={loading}
      controls={
        <select className="mp-select" value={fcDays} onChange={e => setFcDays(+e.target.value)}>
          {[14, 30, 60, 90].map(d => <option key={d} value={d}>{d}d forecast</option>)}
        </select>
      }
    >
      {data && (
        <>
          <div className="mp-stat-row">
            <StatCard label="Trend Direction"  value={null}
              signal={data.trend?.direction === 'upward' ? 'bullish' : 'bearish'}
              hint={data.trend?.direction} />
            <StatCard label="Trend Change"     value={data.trend?.change_pct}          unit="%" hint="over forecast window" />
            <StatCard label="30d Target"       value={data.summary?.predicted_30d}     unit="₹" />
            <StatCard label="Expected Return"  value={data.summary?.expected_return_pct} unit="%" />
          </div>

          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fill: 'var(--muted)', fontSize: 10 }} tickLine={false} axisLine={false}
                tickFormatter={v => `₹${v.toLocaleString('en-IN')}`} width={80} />
              <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }}
                formatter={(v, n) => [`₹${fmt(v)}`, n]} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area type="monotone" dataKey="upper" stroke="none" fill="#34d39920" name="95% CI" />
              <Area type="monotone" dataKey="lower" stroke="none" fill="var(--bg)" name="" legendType="none" />
              <Line type="monotone" dataKey="actual"    stroke="#e2e8f0" dot={false} strokeWidth={2} name="Actual" connectNulls />
              <Line type="monotone" dataKey="fitted"    stroke="#6c8ef7" dot={false} strokeWidth={1} strokeDasharray="2 2" name="Fitted" connectNulls />
              <Line type="monotone" dataKey="predicted" stroke="#34d399" dot={false} strokeWidth={2} strokeDasharray="5 3" name="Forecast" connectNulls />
            </ComposedChart>
          </ResponsiveContainer>
        </>
      )}
    </Panel>
  )
}

// ─── Main ML Page ─────────────────────────────────────────────────────────────
export default function MLPage() {
  const { symbol } = useParams()
  const navigate   = useNavigate()
  const decoded    = decodeURIComponent(symbol)
  const [days, setDays] = useState(365)

  const TF_OPTIONS = [
    { label: '6M', days: 180 },
    { label: '1Y', days: 365 },
    { label: '2Y', days: 730 },
  ]

  return (
    <div className="ml-page">
      <div className="ml-topbar">
        <button className="back-btn" onClick={() => navigate(`/stock/${symbol}`)}>
          <ArrowLeft size={16} /> {decoded}
        </button>
        <div className="ml-topbar-right">
          <span className="ml-tf-label">Training window:</span>
          <TimeframeSelector value={days} onChange={setDays} options={TF_OPTIONS} />
        </div>
      </div>

      <div className="ml-page-header">
        <h1>ML Predictions</h1>
        <p className="page-sub">{decoded} · {days}-day training window · Models retrain on each window change</p>
        <div className="ml-disclaimer">
          <Info size={12} /> Predictions are probabilistic estimates based on historical patterns.
          Not financial advice. Past performance does not guarantee future results.
        </div>
      </div>

      <div className="ml-grid">
        <div className="ml-col-wide">
          <ARIMAPanel          symbol={decoded} days={days} />
          <ProphetPanel        symbol={decoded} days={days} />
          <IsolationForestPanel symbol={decoded} days={days} />
        </div>
        <div className="ml-col-narrow">
          <LinearPanel  symbol={decoded} days={days} />
          <XGBoostPanel symbol={decoded} days={days} />
        </div>
      </div>
    </div>
  )
}
