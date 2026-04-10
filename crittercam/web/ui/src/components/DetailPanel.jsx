import { useState, useEffect } from 'react'

export default function DetailPanel({ detectionId, onClose }) {
  const [detection, setDetection] = useState(null)

  // Re-fetch whenever detectionId changes — same pattern as DetectionGrid.
  // detectionId is in the dependency array so clicking a different thumbnail
  // triggers a new fetch without unmounting and remounting the component.
  useEffect(() => {
    setDetection(null)
    fetch(`/api/detections/${detectionId}`)
      .then(r => r.json())
      .then(data => setDetection(data))
  }, [detectionId])

  if (detection === null) {
    return <div className="detail-panel">Loading…</div>
  }

  // label is stored as a semicolon-joined taxonomy path like
  // "animalia;chordata;mammalia;...;vulpes vulpes"; take only the last part.
  const label = detection.label.split(';').pop()

  return (
    <div className="detail-panel">
      <button className="detail-close" onClick={onClose}>✕</button>

      {/* crop thumbnail */}
      <img className="detail-crop" src={detection.crop_url} alt={label} />

      {/* full image with SVG bounding box drawn on top */}
      <div className="detail-fullimage">
        <img src={detection.image_url} alt="full frame" />
        {detection.bbox && (
          // The SVG is positioned absolutely over the img. viewBox="0 0 1 1"
          // maps the coordinate space to [0, 1] in both axes, matching the
          // normalized bbox coordinates stored in the database.
          // preserveAspectRatio="none" stretches the SVG to fill the element
          // exactly, so the bbox lines up with the image content.
          <svg viewBox="0 0 1 1" preserveAspectRatio="none" className="bbox-overlay">
            <rect
              x={detection.bbox.x}
              y={detection.bbox.y}
              width={detection.bbox.w}
              height={detection.bbox.h}
              fill="none"
              stroke="#ff4444"
              strokeWidth="0.004"
            />
          </svg>
        )}
      </div>

      {/* metadata table */}
      <div className="detail-meta">
        <div className="meta-row">
          <span className="meta-label">species</span>
          <span className="meta-value">{label}</span>
        </div>
        <div className="meta-row">
          <span className="meta-label">confidence</span>
          <span className="meta-value">{(detection.confidence * 100).toFixed(1)}%</span>
        </div>
        {detection.captured_at && (
          <div className="meta-row">
            <span className="meta-label">captured</span>
            <span className="meta-value">{detection.captured_at}</span>
          </div>
        )}
        {detection.temperature_c !== null && (
          <div className="meta-row">
            <span className="meta-label">temp</span>
            <span className="meta-value">{detection.temperature_c}°C</span>
          </div>
        )}
      </div>
    </div>
  )
}
