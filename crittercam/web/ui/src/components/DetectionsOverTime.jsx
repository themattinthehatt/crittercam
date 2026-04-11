import { useState, useEffect } from 'react'
import {
  LineChart, Line,
  XAxis, YAxis,
  Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts'

// categorical color palette — cycles if there are more species than colors
const COLORS = [
  '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
]

export default function DetectionsOverTime() {
  const [result, setResult] = useState(null)

  useEffect(() => {
    fetch('/api/stats/detections_over_time')
      .then(r => r.json())
      .then(data => setResult(data))
  }, [])

  if (result === null) return <div>Loading…</div>

  if (result.species.length === 0) {
    return <p className="placeholder">no species with more than 10 detections in the past year</p>
  }

  return (
    <div className="detections-over-time">
      <h2 className="section-heading">detections per week — past year</h2>

      {/* ResponsiveContainer makes the chart fill its parent's width.
          The 100% width + fixed height is the standard Recharts pattern. */}
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={result.data} margin={{ top: 8, right: 24, bottom: 8, left: 0 }}>
          <XAxis
            dataKey="week"
            tick={{ fontSize: 11 }}
            interval="preserveStartEnd"
          />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip />
          <Legend />

          {/* one <Line> per species — dataKey matches the key in each data object */}
          {result.species.map((species, i) => (
            <Line
              key={species}
              type="monotone"
              dataKey={species}
              stroke={COLORS[i % COLORS.length]}
              dot={false}
              strokeWidth={1.5}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
