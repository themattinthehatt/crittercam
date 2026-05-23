export default function StatCard({ value, label }) {
  return (
    <div className="text-center">
      <div className="text-5xl font-bold leading-none">{value}</div>
      <div className="text-xs text-base-content/60 mt-1 uppercase tracking-widest">{label}</div>
    </div>
  )
}
