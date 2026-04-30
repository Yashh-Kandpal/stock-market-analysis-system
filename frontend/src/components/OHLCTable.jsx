import './OHLCTable.css'

export default function OHLCTable({ data = [] }) {
  if (!data.length) return <div className="ohlc-empty">No data to display.</div>

  const rows = [...data].reverse().slice(0, 20)

  return (
    <div className="ohlc-wrap">
      <table className="ohlc-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Open</th>
            <th>High</th>
            <th>Low</th>
            <th>Close</th>
            <th>Volume</th>
            <th>Chg%</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const prev = rows[i + 1]
            const chg = prev ? ((row.close - prev.close) / prev.close) * 100 : 0
            const isUp = chg >= 0
            return (
              <tr key={row.timestamp}>
                <td className="ts">{new Date(row.timestamp).toLocaleString('en-IN', {
                  month: 'short', day: 'numeric',
                  hour: '2-digit', minute: '2-digit'
                })}</td>
                <td>₹{row.open?.toFixed(2)}</td>
                <td className="up">₹{row.high?.toFixed(2)}</td>
                <td className="down">₹{row.low?.toFixed(2)}</td>
                <td className={isUp ? 'up' : 'down'}>₹{row.close?.toFixed(2)}</td>
                <td className="vol">{parseInt(row.volume || 0).toLocaleString('en-IN')}</td>
                <td className={isUp ? 'up' : 'down'}>
                  {isUp ? '+' : ''}{chg.toFixed(2)}%
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
