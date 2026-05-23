// DetailPanel is a presentational component — it receives a fully-loaded
// detection object and renders it. The parent (DetectionGrid) owns the fetch.
export default function DetailPanel({ detection, onClose }) {
  // label is stored as a semicolon-joined taxonomy path like
  // "animalia;chordata;mammalia;...;vulpes vulpes"; take only the last part.
  const label = detection.label.split(';').pop()

  return (
    <div className="detail-panel">
      <button className="detail-close" onClick={onClose}>✕</button>

      {/* crop thumbnail — omitted for blank frames */}
      {detection.crop_url && (
        <img className="detail-crop" src={detection.crop_url} alt={label} />
      )}

      {/* full image with SVG bounding box drawn on top.
          SVG sits absolutely over the img — see App.css .bbox-overlay.
          viewBox="0 0 1 1" maps the coordinate space to [0,1] in both axes,
          matching the normalized bbox values stored in the database.
          preserveAspectRatio="none" stretches the SVG to fill the element
          exactly so the rect lines up with the image content. */}
      <div className="detail-fullimage">
        <img src={detection.image_url} alt="full frame" />
        {detection.bbox && (
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
        {detection.individual_id !== null && (
          <div className="meta-row" style={{ marginTop: '0.75rem' }}>
            <span className="meta-label">individual</span>
            <span className="meta-value">
              {detection.nickname
                ? `${detection.nickname} (id ${detection.individual_id})`
                : `id ${detection.individual_id}`}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
