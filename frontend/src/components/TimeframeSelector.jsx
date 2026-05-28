import './TimeframeSelector.css'

const PRESETS = [
  { label: '1M',  days: 30 },
  { label: '3M',  days: 90 },
  { label: '6M',  days: 180 },
  { label: '1Y',  days: 365 },
  { label: '2Y',  days: 730 },
]

export default function TimeframeSelector({ value, onChange, options }) {
  const presets = options || PRESETS
  return (
    <div className="tf-selector">
      {presets.map(p => (
        <button
          key={p.days}
          className={`tf-btn ${value === p.days ? 'active' : ''}`}
          onClick={() => onChange(p.days)}
        >
          {p.label}
        </button>
      ))}
    </div>
  )
}
