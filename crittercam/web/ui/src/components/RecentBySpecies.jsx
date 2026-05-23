import { useState, useEffect } from 'react'
import DetectionCard from './DetectionCard'

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
          <DetectionCard
            key={det.id}
            cropUrl={det.crop_url}
            label={det.label}
            confidence={det.confidence}
            capturedAt={det.captured_at}
          />
        ))}
      </div>
    </div>
  )
}
