import { useState, useEffect } from 'react'

// A component is just a function that returns JSX (HTML-like syntax).
// React calls this function whenever it needs to render or re-render the component.

export default function StatsBar() {
  // useState declares a piece of state — data the component remembers between renders.
  // It returns [currentValue, setterFunction].
  // null means "not loaded yet"; once the fetch completes we'll replace it with real data.
  const [stats, setStats] = useState(null)

  // useEffect runs a side effect after the component renders.
  // The empty array [] as the second argument means "run this once, when the component
  // first appears on the page" — equivalent to an __init__ or on-mount hook.
  useEffect(() => {
    fetch('/api/stats/summary')
      .then(response => response.json())
      .then(data => {
        // Calling the setter triggers a re-render with the new value.
        // React will re-call this function with stats = data, and the JSX below
        // will now see real numbers instead of null.
        setStats(data)
      })
  }, [])

  // While the fetch is in flight, stats is still null — render a placeholder.
  if (stats === null) {
    return <div className="stats-bar">Loading…</div>
  }

  return (
    <div className="stats-bar">
      <Stat number={stats.total_images} label="images" />
      <Stat number={stats.total_detections} label="detections" />
      <Stat number={stats.species_seen} label="species" />
    </div>
  )
}

// A small helper component. Components can be composed freely — StatsBar renders
// three Stat components, passing data down via props (the function's argument object).
function Stat({ number, label }) {
  return (
    <div className="stat">
      <div className="stat-number">{number}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}
