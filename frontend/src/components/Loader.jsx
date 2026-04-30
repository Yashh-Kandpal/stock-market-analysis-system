import './Loader.css'

export default function Loader({ text = 'Loading...' }) {
  return (
    <div className="loader-wrap">
      <div className="spinner" />
      <span className="loader-text">{text}</span>
    </div>
  )
}
