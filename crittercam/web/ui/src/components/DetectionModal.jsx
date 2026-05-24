// DetectionModal is a presentational component — it receives a fully-loaded
// detection object and renders it. The parent (DetectionGrid) owns the fetch.
export default function DetectionModal({ detection, onClose }) {
  // label is stored as a semicolon-joined taxonomy path like
  // "animalia;chordata;mammalia;...;vulpes vulpes"; take only the last part.
  const label = detection.label.split(';').pop()

  return (
    // fixed overlay covers the full viewport above everything else.
    // clicking the backdrop (outside the panel) closes the modal.
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>

      {/* stopPropagation prevents clicks inside the panel from closing it */}
      <div
        className="bg-base-100 rounded-lg w-[90vw] h-[85vh] flex overflow-hidden"
        onClick={e => e.stopPropagation()}
      >

        {/* left column (~75%) — crop image, centered in a dark letterbox */}
        <div className="flex-[3] bg-base-300 flex items-center justify-center p-6">
          {detection.crop_url
            ? <img className="max-w-full max-h-full object-contain rounded" src={detection.crop_url} alt={label} />
            : <span className="text-sm text-base-content/40">no crop</span>
          }
        </div>

        {/* right column (~25%) — full frame + metadata, scrollable */}
        <div className="flex-1 flex flex-col border-l border-base-300 overflow-y-auto">

          <div className="flex justify-end p-3">
            <button className="btn btn-xs btn-ghost" onClick={onClose}>✕</button>
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

          {/* metadata */}
          <div className="px-4 pb-6 text-sm flex flex-col gap-1.5">
            <div className="flex gap-2">
              <span className="text-xs uppercase tracking-wide text-base-content/40 w-20 flex-shrink-0 pt-0.5">species</span>
              <span className="capitalize">{label}</span>
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
            {detection.individual_id !== null && (
              <div className="flex gap-2 mt-3">
                <span className="text-xs uppercase tracking-wide text-base-content/40 w-20 flex-shrink-0 pt-0.5">individual</span>
                <span>
                  {detection.nickname
                    ? `${detection.nickname} (id ${detection.individual_id})`
                    : `id ${detection.individual_id}`}
                </span>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  )
}
