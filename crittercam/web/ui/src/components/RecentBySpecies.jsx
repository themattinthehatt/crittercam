import { useState, useEffect } from 'react'
import { toggleFavorite, toggleFavoriteInList, deleteMedia } from '../api.js'
import DetectionCard from './DetectionCard'
import DetectionModal from './DetectionModal'

export default function RecentBySpecies() {
  const [detections, setDetections] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [selectedDetection, setSelectedDetection] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    setDetections(null)
    fetch('/api/detections/recent_by_species')
      .then(r => r.json())
      .then(data => setDetections(data))
  }, [refreshKey])

  useEffect(() => {
    if (selectedId === null) { setSelectedDetection(null); return }
    fetch(`/api/detections/${selectedId}`)
      .then(r => r.json())
      .then(data => setSelectedDetection(data))
  }, [selectedId])

  const handleDelete = () => {
    deleteMedia(selectedDetection.media_id).then(response => {
      if (response.ok) {
        setSelectedId(null)
        setRefreshKey(k => k + 1)
      }
    })
  }

  const idx = detections ? detections.findIndex(d => d.id === selectedId) : -1
  const hasPrev = idx > 0
  const hasNext = detections !== null && idx < detections.length - 1

  const handlePrev = () => { if (idx > 0) setSelectedId(detections[idx - 1].id) }
  const handleNext = () => { if (idx < detections.length - 1) setSelectedId(detections[idx + 1].id) }

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
            selected={selectedId === det.id}
            onClick={() => setSelectedId(det.id)}
            isFavorite={det.favorite === 1}
            onFavorite={() => toggleFavoriteInList(det, setDetections)}
          />
        ))}
      </div>

      {selectedDetection !== null && (
        <DetectionModal
          detection={selectedDetection}
          onClose={() => setSelectedId(null)}
          hasPrev={hasPrev}
          hasNext={hasNext}
          onPrev={handlePrev}
          onNext={handleNext}
          onDelete={handleDelete}
          isFavorite={selectedDetection.favorite === 1}
          onFavorite={() => toggleFavorite(
            selectedDetection,
            setSelectedDetection,
            newValue => setDetections(prev => prev.map(d =>
              d.id === selectedDetection.id ? { ...d, favorite: newValue } : d
            )),
          )}
        />
      )}
    </div>
  )
}
