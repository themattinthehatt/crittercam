import { useState } from 'react'
import { StarIcon, TrashIcon, PencilIcon } from './icons.jsx'

// DetectionModal is a presentational component — it receives a fully-loaded
// detection object and renders it. The parent (DetectionGrid) owns the fetch.
// hasPrev/hasNext control whether nav arrows are rendered; onPrev/onNext are
// called when the user clicks them.
// speciesList and individualList are used only in edit mode; onSave is called
// with (species_leaf, individual_id) when the user confirms edits.
export default function DetectionModal({
  detection, onClose, hasPrev = false, hasNext = false, onPrev, onNext,
  isFavorite = false, onFavorite, onDelete,
  speciesList = [], individualList = [], onSave,
}) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editSpecies, setEditSpecies] = useState('')
  const [editIndividual, setEditIndividual] = useState(null)

  // label is stored as a semicolon-joined taxonomy path like
  // "animalia;chordata;mammalia;...;vulpes vulpes"; take only the last part.
  const label = detection.label.split(';').pop()

  const startEditing = () => {
    setEditSpecies(label)
    setEditIndividual(detection.individual_id)
    setShowDeleteConfirm(false)
    setIsEditing(true)
  }

  const handleCancel = () => setIsEditing(false)

  const handleSave = () => {
    onSave?.(editSpecies, editIndividual)
    setIsEditing(false)
  }

  return (
    // fixed overlay covers the full viewport above everything else.
    // clicking the backdrop (outside the panel) closes the modal.
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>

      {/* stopPropagation prevents clicks inside the panel from closing it */}
      <div
        className="bg-base-100 rounded-lg w-[90vw] h-[85vh] flex overflow-hidden"
        onClick={e => e.stopPropagation()}
      >

        {/* left column (~75%) — crop image centered in a dark letterbox.
            relative here so the nav arrows can be anchored to its edges. */}
        <div className="relative flex-[3] bg-base-300 flex items-center justify-center p-6">
          {detection.crop_url
            ? <img className="max-w-full max-h-full object-contain rounded" src={detection.crop_url} alt={label} />
            : <span className="text-sm text-base-content/40">no crop</span>
          }

          {/* prev/next arrows — only rendered when navigation is available.
              bg-black/30 keeps them visible against any image without being
              distracting; hover darkens slightly for feedback. */}
          {hasPrev && (
            <button
              className="absolute left-3 top-1/2 -translate-y-1/2 btn btn-circle bg-black/30 hover:bg-black/50 border-none text-white text-xl"
              onClick={e => { e.stopPropagation(); onPrev() }}
            >
              ‹
            </button>
          )}
          {hasNext && (
            <button
              className="absolute right-3 top-1/2 -translate-y-1/2 btn btn-circle bg-black/30 hover:bg-black/50 border-none text-white text-xl"
              onClick={e => { e.stopPropagation(); onNext() }}
            >
              ›
            </button>
          )}
        </div>

        {/* right column (~25%) — full frame + metadata, scrollable */}
        <div className="flex-1 flex flex-col border-l border-base-300 overflow-y-auto">

          {/* top bar: switches between three mutually exclusive states —
              normal (trash/star/pencil), delete confirmation, and edit mode. */}
          <div className="flex items-center justify-between p-3 min-h-[48px]">
            {showDeleteConfirm ? (
              <>
                <span className="text-sm text-error">Delete this observation?</span>
                <div className="flex items-center gap-2">
                  <button
                    className="btn btn-xs btn-ghost border border-base-content/20"
                    onClick={() => setShowDeleteConfirm(false)}
                  >
                    cancel
                  </button>
                  <button
                    className="btn btn-xs btn-error"
                    onClick={onDelete}
                  >
                    delete
                  </button>
                </div>
              </>
            ) : isEditing ? (
              <>
                <span className="text-sm text-base-content/60">editing</span>
                <div className="flex items-center gap-2">
                  <button
                    className="btn btn-xs btn-ghost border border-base-content/20"
                    onClick={handleCancel}
                  >
                    cancel
                  </button>
                  <button
                    className="btn btn-xs btn-primary"
                    onClick={handleSave}
                  >
                    save
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="flex items-center gap-2">
                  <button
                    className="btn btn-sm btn-ghost text-error"
                    onClick={() => setShowDeleteConfirm(true)}
                    title="Delete"
                  >
                    <TrashIcon className="size-5" />
                  </button>
                  <button
                    className="btn btn-sm btn-ghost text-base-content/60"
                    onClick={startEditing}
                    title="Edit"
                  >
                    <PencilIcon className="size-5" />
                  </button>
                  <button
                    className={`btn btn-sm btn-ghost ${isFavorite ? 'text-yellow-400' : 'text-base-content/40'}`}
                    onClick={onFavorite}
                    title={isFavorite ? 'Unfavorite' : 'Favorite'}
                  >
                    <StarIcon className={`size-5 ${isFavorite ? 'fill-current' : ''}`} />
                  </button>
                </div>
                <button className="btn btn-xs btn-ghost" onClick={onClose}>✕</button>
              </>
            )}
          </div>

          {/* full image with SVG bounding box drawn on top.
              The SVG sits absolutely over the img.
              viewBox="0 0 1 1" maps the coordinate space to [0,1] in both axes,
              matching the normalized bbox values stored in the database.
              preserveAspectRatio="none" stretches the SVG to fill the element
              exactly so the rect lines up with the image content.
              The relative wrapper must be a sibling of the padding div — not
              the same element — so that h-full on the SVG matches the image
              height exactly and not the padded container height. */}
          <div className="px-4 pb-4">
            <div className="relative">
              <img className="w-full block rounded" src={detection.image_url} alt="full frame" />
              {detection.bbox && (
                <svg viewBox="0 0 1 1" preserveAspectRatio="none" className="absolute top-0 left-0 w-full h-full">
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
          </div>

          {/* metadata — species and individual rows become dropdowns in edit mode */}
          <div className="px-4 pb-6 text-sm flex flex-col gap-1.5">
            <div className="flex gap-2 items-center">
              <span className="text-xs uppercase tracking-wide text-base-content/40 w-20 flex-shrink-0">species</span>
              {isEditing ? (
                <select
                  className="select select-xs select-bordered flex-1 capitalize"
                  value={editSpecies}
                  onChange={e => setEditSpecies(e.target.value)}
                >
                  {speciesList.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              ) : (
                <span className="capitalize pt-0.5">{label}</span>
              )}
            </div>
            <div className="flex gap-2">
              <span className="text-xs uppercase tracking-wide text-base-content/40 w-20 flex-shrink-0 pt-0.5">confidence</span>
              <span>{(detection.confidence * 100).toFixed(1)}%</span>
            </div>
            {detection.captured_at && (
              <div className="flex gap-2">
                <span className="text-xs uppercase tracking-wide text-base-content/40 w-20 flex-shrink-0 pt-0.5">captured</span>
                <span>{detection.captured_at}</span>
              </div>
            )}
            {detection.temperature_c !== null && (
              <div className="flex gap-2">
                <span className="text-xs uppercase tracking-wide text-base-content/40 w-20 flex-shrink-0 pt-0.5">temp</span>
                <span>{detection.temperature_c}°C</span>
              </div>
            )}
            {/* individual row: always visible in edit mode so the user can assign one;
                only visible in view mode when a value is already set. */}
            {(isEditing || detection.individual_id !== null) && (
              <div className="flex gap-2 mt-3 items-center">
                <span className="text-xs uppercase tracking-wide text-base-content/40 w-20 flex-shrink-0">individual</span>
                {isEditing ? (
                  <select
                    className="select select-xs select-bordered flex-1"
                    value={editIndividual ?? ''}
                    onChange={e => setEditIndividual(e.target.value === '' ? null : parseInt(e.target.value, 10))}
                  >
                    <option value="">— none —</option>
                    {individualList.map(ind => (
                      <option key={ind.id} value={ind.id}>
                        {ind.nickname ? `${ind.nickname} (id ${ind.id})` : `id ${ind.id}`}
                      </option>
                    ))}
                  </select>
                ) : (
                  <span>
                    {detection.nickname
                      ? `${detection.nickname} (id ${detection.individual_id})`
                      : `id ${detection.individual_id}`}
                  </span>
                )}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  )
}
