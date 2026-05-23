import {
  BarChart, Bar,
  LineChart, Line,
  XAxis, YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import ChartPanel from './ChartPanel'

export default {
  title: 'Domain/ChartPanel',
  component: ChartPanel,
  decorators: [
    Story => (
      <div style={{ width: '600px' }}>
        <Story />
      </div>
    ),
  ],
}

const WEEKLY_DATA = [
  { week: 'Jan 1', deer: 4, raccoon: 2 },
  { week: 'Jan 8', deer: 7, raccoon: 1 },
  { week: 'Jan 15', deer: 3, raccoon: 5 },
  { week: 'Jan 22', deer: 9, raccoon: 3 },
  { week: 'Jan 29', deer: 5, raccoon: 4 },
]

const SPECIES_DATA = [
  { species: 'deer', count: 42 },
  { species: 'raccoon', count: 27 },
  { species: 'fox', count: 14 },
  { species: 'opossum', count: 9 },
]

export const WithLineChart = {
  args: { title: 'detections per week' },
  render: args => (
    <ChartPanel {...args}>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={WEEKLY_DATA}>
          <XAxis dataKey="week" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip />
          <Line type="monotone" dataKey="deer" stroke="#1f77b4" dot={false} />
          <Line type="monotone" dataKey="raccoon" stroke="#ff7f0e" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </ChartPanel>
  ),
}

export const WithBarChart = {
  args: { title: 'detections by species' },
  render: args => (
    <ChartPanel {...args}>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={SPECIES_DATA} layout="vertical">
          <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
          <YAxis type="category" dataKey="species" tick={{ fontSize: 11 }} width={60} />
          <Tooltip />
          <Bar dataKey="count" fill="#1f77b4" />
        </BarChart>
      </ResponsiveContainer>
    </ChartPanel>
  ),
}
