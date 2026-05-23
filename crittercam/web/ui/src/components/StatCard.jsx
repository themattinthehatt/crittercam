export default function StatCard({ value, label }) {
  return (
    <div className="stat">
      <div className="stat-number">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}
