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
export default function DetectionCard({ cropUrl, label, confidence, capturedAt, onClick, selected = false }) {
  const isBlank = label === 'blank'
  const timestamp = formatTimestamp(capturedAt)

  return (
    // The card is a flex column: image-container on top, timestamp below.
    // onClick is passed straight through to the wrapping div so the whole
    // card is clickable, just like a grid cell in DetectionGrid.
    <div className="flex flex-col gap-1.5 cursor-pointer" onClick={onClick}>
      {/* position: relative on the container lets the badge overlays use
          position: absolute to anchor themselves to its corners. */}
      <div className={`relative rounded overflow-hidden ${selected ? 'ring-2 ring-base-content/50' : ''}`}>
        {cropUrl
          ? <img className="w-full aspect-[3/2] object-contain block bg-base-300 hover:opacity-90 transition-opacity duration-100" src={cropUrl} alt={label} />
          : <div className="w-full aspect-[3/2] bg-base-200" />
        }
        <span className="absolute top-1.5 left-1.5">
          <Badge label={label} variant={isBlank ? 'blank' : 'species'} />
        </span>
        {!isBlank && (
          <span className="absolute top-1.5 right-1.5">
            <Badge
              label={`${Math.round(confidence * 100)}%`}
              variant="confidence"
              confidence={confidence}
            />
          </span>
        )}
      </div>
      {timestamp && (
        <span className="text-xs text-base-content/40 px-0.5">{timestamp}</span>
      )}
    </div>
  )
}
