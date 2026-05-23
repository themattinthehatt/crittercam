import { useState, useEffect } from 'react'
import {
  LineChart, Line,
  XAxis, YAxis,
  Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts'
import ChartPanel from './ChartPanel'

// same palette as DetectionsOverTime so species colors are consistent across charts
const COLORS = [
  '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
]

export default function ActivityByHour() {
  const [result, setResult] = useState(null)

  useEffect(() => {
    fetch('/api/stats/activity_by_hour')
      .then(r => r.json())
      .then(data => setResult(data))
  }, [])

  if (result === null) return <div>Loading…</div>

  if (result.species.length === 0) {
    return <p className="text-sm text-base-content/60">no species with at least 50 detections in the past year</p>
  }

  return (
    <ChartPanel title="activity by time of day — past year">
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={result.data} margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
          <XAxis
            dataKey="hour"
            tick={{ fontSize: 11, fill: 'currentColor' }}
            // interval=2 shows every third label: 00:00, 03:00, 06:00, ... 21:00
            interval={2}
          />
          <YAxis
            tick={{ fontSize: 11, fill: 'currentColor' }}
            tickFormatter={v => v.toFixed(2)}
            label={{
              value: 'probability',
              angle: -90,
              position: 'insideLeft',
              offset: -2,
              style: { fontSize: 11, fill: 'currentColor' },
            }}
          />
          <Tooltip formatter={v => v.toFixed(3)} />
          <Legend />

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
    </ChartPanel>
  )
}
