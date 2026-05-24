import Badge from './Badge'
import { StarIcon } from './icons.jsx'

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
export default function DetectionCard({ cropUrl, label, confidence, capturedAt, onClick, selected = false, isFavorite = false, onFavorite }) {
  const isBlank = label === 'blank'
  const timestamp = formatTimestamp(capturedAt)

  return (
    // bg-base-200 makes the card slightly darker than the page background.
    // overflow-hidden clips the image to the card's rounded corners.
    // onClick is passed straight through so the whole card is clickable.
    <div
      className={`bg-base-200 rounded overflow-hidden cursor-pointer ${selected ? 'ring-2 ring-base-content/50' : ''}`}
      onClick={onClick}
    >
      {/* pt-1 exposes a thin sliver of the card background above the image,
          visually anchoring the image inside the card. */}
      <div className="pt-1 px-1">
        {cropUrl
          ? <img className="w-full aspect-[3/2] object-contain block bg-base-300 hover:opacity-90 transition-opacity duration-100" src={cropUrl} alt={label} />
          : <div className="w-full aspect-[3/2] bg-base-300" />
        }
      </div>

      {/* info section: badges on one row, date on the next */}
      <div className="px-2 pt-1.5 pb-2">
        <div className="flex items-center justify-between gap-1">
          <Badge label={label} variant={isBlank ? 'blank' : 'species'} />
          {!isBlank && confidence != null && (
            <Badge
              label={`${Math.round(confidence * 100)}%`}
              variant="confidence"
              confidence={confidence}
            />
          )}
        </div>
        <div className="flex items-center justify-between mt-2">
          <span className="text-xs text-base-content/40">{timestamp ?? ''}</span>
          <button
            className={`p-0 bg-transparent border-none cursor-pointer ${isFavorite ? 'text-yellow-400' : 'text-base-content/20'}`}
            onClick={e => { e.stopPropagation(); onFavorite?.() }}
          >
            <StarIcon className={`size-3.5 ${isFavorite ? 'fill-current' : ''}`} />
          </button>
        </div>
      </div>
    </div>
  )
}
