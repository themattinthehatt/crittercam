import { useState, useEffect } from 'react'
import {
  LineChart, Line,
  XAxis, YAxis,
  Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts'
import ChartPanel from './ChartPanel'

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
    return <p className="text-sm text-base-content/60">no species with at least 50 detections in the past year</p>
  }

  // log(0) is undefined — replace zeros with null so those weeks render as gaps
  // rather than breaking the scale entirely
  const data = result.data.map(row => {
    const out = { week: row.week }
    for (const sp of result.species) out[sp] = row[sp] === 0 ? null : row[sp]
    return out
  })

  return (
    <ChartPanel title="detections per week — past year">
      {/* ResponsiveContainer makes the chart fill its parent's width.
          The 100% width + fixed height is the standard Recharts pattern. */}
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={data} margin={{ top: 8, right: 24, bottom: 8, left: 0 }}>
          <XAxis
            dataKey="week"
            tick={{ fontSize: 11, fill: 'currentColor' }}
            interval="preserveStartEnd"
          />
          {/* scale="log" with domain starting at 1 — zero values are clamped by Recharts
              to the domain minimum, so they render at the bottom rather than crashing */}
          <YAxis
            scale="log"
            domain={[1, 'auto']}
            tickFormatter={v => Number.isInteger(v) ? v : ''}
            tick={{ fontSize: 11, fill: 'currentColor' }}
            allowDecimals={false}
          />
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
    </ChartPanel>
  )
}
