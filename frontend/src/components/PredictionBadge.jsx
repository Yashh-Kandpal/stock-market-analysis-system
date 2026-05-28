import './PredictionBadge.css'

export default function PredictionBadge({ direction, confidence, label }) {
  const isUp = direction === 'UP'
  return (
    <div className={`pred-badge ${isUp ? 'up' : 'down'}`}>
      <span className="pred-arrow">{isUp ? '▲' : '▼'}</span>
      <span className="pred-dir">{direction}</span>
      {confidence && <span className="pred-conf">{confidence}% confidence</span>}
      {label && <span className="pred-label">{label}</span>}
    </div>
  )
}
