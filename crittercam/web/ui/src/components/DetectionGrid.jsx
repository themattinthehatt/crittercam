import { useState, useEffect } from 'react'

export default function DetectionGrid() {
  const [page, setPage] = useState(1)

  // result holds the full API response: { detections, total, page, page_size }
  const [result, setResult] = useState(null)

  // Re-fetch whenever page changes — same pattern as DetectionViewer with currentId.
  // When the user clicks a page button, setPage fires, React re-renders,
  // sees page changed in the dependency array, and re-runs this effect.
  useEffect(() => {
    setResult(null)  // clear while loading
    fetch(`/api/detections?page=${page}`)
      .then(response => response.json())
      .then(data => setResult(data))
  }, [page])

  if (result === null) {
    return <div className="detection-grid-container">Loading…</div>
  }

  const totalPages = Math.ceil(result.total / result.page_size)

  return (
    <div className="detection-grid-container">
      <div className="detection-grid">
        {result.detections.map(detection => (
          <div key={detection.id} className="grid-cell">
            <img
              src={detection.crop_url}
              alt={detection.label}
              title={`${detection.label} (${(detection.confidence * 100).toFixed(1)}%)`}
            />
            <div className="grid-cell-label">{detection.label}</div>
          </div>
        ))}
      </div>

      <div className="pagination">
        <button
          onClick={() => setPage(p => p - 1)}
          disabled={page === 1}
        >
          ← prev
        </button>

        <span className="pagination-info">
          page {page} of {totalPages}
        </span>

        <button
          onClick={() => setPage(p => p + 1)}
          disabled={page === totalPages}
        >
          next →
        </button>
      </div>
    </div>
  )
}
