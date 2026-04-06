import { useState, useEffect } from 'react'

export default function DetectionViewer({ firstId }) {
  // currentId is the id of the detection we're currently showing.
  // It starts as whatever the parent passed in (the first detection's id).
  const [currentId, setCurrentId] = useState(firstId)

  // detection holds the full data for the current detection: label, confidence,
  // crop_url, prev_id, next_id. null means we're still loading.
  const [detection, setDetection] = useState(null)

  // This effect fetches the detection whenever currentId changes.
  // Notice [currentId] in the dependency array — unlike the empty [] in StatsBar,
  // this effect re-runs every time currentId gets a new value.
  // Sequence: button click → setCurrentId(next_id) → React re-renders →
  //           React sees currentId changed → runs this effect → fetch → setDetection → re-render
  useEffect(() => {
    setDetection(null)  // clear the old image while the new one loads

    fetch(`/api/detections/${currentId}`)
      .then(response => response.json())
      .then(data => setDetection(data))
  }, [currentId])

  if (detection === null) {
    return <div className="detection-viewer">Loading…</div>
  }

  return (
    <div className="detection-viewer">
      <img
        className="detection-crop"
        src={detection.crop_url}
        alt={detection.label}
      />
      <div className="detection-meta">
        <div className="detection-label">{detection.label}</div>
        <div className="detection-confidence">
          {(detection.confidence * 100).toFixed(1)}% confidence
        </div>
        <div className="detection-id">detection #{detection.id}</div>
      </div>
      <div className="detection-nav">
        {/* The button is disabled when prev_id is null (we're at the start).
            onClick calls setCurrentId, which triggers the effect above. */}
        <button
          onClick={() => setCurrentId(detection.prev_id)}
          disabled={detection.prev_id === null}
        >
          ← prev
        </button>
        <button
          onClick={() => setCurrentId(detection.next_id)}
          disabled={detection.next_id === null}
        >
          next →
        </button>
      </div>
    </div>
  )
}
