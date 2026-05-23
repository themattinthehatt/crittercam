// DetailPanel is a presentational component — it receives a fully-loaded
// detection object and renders it. The parent (DetectionGrid) owns the fetch.
export default function DetailPanel({ detection, onClose }) {
  // label is stored as a semicolon-joined taxonomy path like
  // "animalia;chordata;mammalia;...;vulpes vulpes"; take only the last part.
  const label = detection.label.split(';').pop()

  return (
    <div className="w-[300px] flex-shrink-0 border-l border-base-300 pl-6 sticky top-4">
      <button className="float-right btn btn-xs btn-ghost" onClick={onClose}>✕</button>

      {/* crop thumbnail — omitted for blank frames */}
      {detection.crop_url && (
        <img className="w-full block rounded mb-3" src={detection.crop_url} alt={label} />
      )}

      {/* full image with SVG bounding box drawn on top.
          The SVG sits absolutely over the img.
          viewBox="0 0 1 1" maps the coordinate space to [0,1] in both axes,
          matching the normalized bbox values stored in the database.
          preserveAspectRatio="none" stretches the SVG to fill the element
          exactly so the rect lines up with the image content. */}
      <div className="relative mb-3">
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

      {/* metadata table */}
      <div className="text-sm flex flex-col gap-1.5">
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
  )
}
