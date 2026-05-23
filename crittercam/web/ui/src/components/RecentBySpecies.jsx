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
    <div className="mt-8">
      <h2 className="text-xs uppercase tracking-widest text-base-content/60 mb-3 font-normal">
        most recent by species
      </h2>
      <div className="grid grid-cols-4 gap-3">
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
