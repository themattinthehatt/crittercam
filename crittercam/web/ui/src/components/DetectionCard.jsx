import Badge from './Badge'

// formatTimestamp converts an ISO string like '2026-03-14T02:17:00' to
// a readable form like 'Mar 14 · 2:17 AM'. Returns null if no value is given.
function formatTimestamp(iso) {
  if (!iso) return null
  const d = new Date(iso)
  const date = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
  return `${date} · ${time}`
}

// DetectionCard is a presentational component — it receives already-parsed data
// and renders it. label should be the leaf of the taxonomy string (e.g.
// 'white-tailed deer'), not the full semicolon-delimited path.
export default function DetectionCard({ cropUrl, label, confidence, capturedAt, onClick }) {
  const isBlank = label === 'blank'
  const timestamp = formatTimestamp(capturedAt)

  return (
    // The card is a flex column: image-container on top, timestamp below.
    // onClick is passed straight through to the wrapping div so the whole
    // card is clickable, just like a grid cell in DetectionGrid.
    <div className="detection-card" onClick={onClick}>
      {/* position: relative on the container lets the badge overlays use
          position: absolute to anchor themselves to its corners. */}
      <div className="detection-card__image-container">
        {cropUrl
          ? <img className="detection-card__image" src={cropUrl} alt={label} />
          : <div className="detection-card__image detection-card__image--placeholder" />
        }
        <span className="detection-card__overlay-left">
          <Badge label={label} variant={isBlank ? 'blank' : 'species'} />
        </span>
        {!isBlank && (
          <span className="detection-card__overlay-right">
            <Badge
              label={`${Math.round(confidence * 100)}%`}
              variant="confidence"
              confidence={confidence}
            />
          </span>
        )}
      </div>
      {timestamp && (
        <span className="detection-card__timestamp">{timestamp}</span>
      )}
    </div>
  )
}
