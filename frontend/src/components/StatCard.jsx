import './StatCard.css'

const SIGNAL_COLORS = {
  bullish:          'green',
  bearish:          'red',
  overbought:       'red',
  oversold:         'green',
  neutral:          'muted',
  golden_cross:     'green',
  death_cross:      'red',
  above_upper_band: 'red',
  below_lower_band: 'green',
  within_bands:     'muted',
}

export default function StatCard({ label, value, unit = '', signal, hint, size = 'md' }) {
  const color = signal ? SIGNAL_COLORS[signal] || 'muted' : null

  return (
    <div className={`stat-card size-${size}`}>
      <div className="sc-label">{label}</div>
      <div className="sc-value">
        {value !== null && value !== undefined ? (
          <>
            <span>{typeof value === 'number' ? value.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : value}</span>
            {unit && <span className="sc-unit">{unit}</span>}
          </>
        ) : <span className="sc-na">—</span>}
      </div>
      {signal && (
        <div className={`sc-signal color-${color}`}>{signal.replace(/_/g, ' ')}</div>
      )}
      {hint && <div className="sc-hint">{hint}</div>}
    </div>
  )
}
