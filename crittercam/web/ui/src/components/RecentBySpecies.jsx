import { useState, useEffect } from 'react'

export default function RecentBySpecies() {
  const [detections, setDetections] = useState(null)

  useEffect(() => {
    fetch('/api/detections/recent_by_species')
      .then(r => r.json())
      .then(data => setDetections(data))
  }, [])

  if (detections === null) {
    return <div>Loading…</div>
  }

  return (
    <div className="recent-by-species">
      <h2 className="section-heading">most recent by species</h2>
      <div className="detection-grid">
        {detections.map(det => (
          <div key={det.id} className="grid-cell">
            <img
              src={det.crop_url}
              alt={det.label}
              title={`${det.label} (${(det.confidence * 100).toFixed(1)}%)`}
            />
            <div className="grid-cell-label">{det.label}</div>
            <div className="grid-cell-date">{det.captured_at?.split(' ')[0]}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
