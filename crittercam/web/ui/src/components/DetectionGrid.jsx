import { useState, useEffect } from 'react'
import DetailPanel from './DetailPanel.jsx'
import FilterBar from './FilterBar.jsx'

export default function DetectionGrid() {
  const [page, setPage] = useState(1)
  const [result, setResult] = useState(null)
  const [selectedId, setSelectedId] = useState(null)

  // browse mode: 'species' | 'individual'
  const [browseMode, setBrowseMode] = useState('species')

  // filter state — empty string means "no filter applied"
  const [species, setSpecies] = useState('')
  const [individual, setIndividual] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  // dropdown lists — fetched once on mount
  const [speciesList, setSpeciesList] = useState([])
  const [individualList, setIndividualList] = useState([])

  useEffect(() => {
    fetch('/api/species')
      .then(r => r.json())
      .then(data => setSpeciesList(data))
    fetch('/api/individuals')
      .then(r => r.json())
      .then(data => setIndividualList(data))
  }, [])  // [] means run once when the component first mounts, never again

  // re-fetch whenever page or any filter changes.
  // URLSearchParams builds the query string cleanly: it only adds a key
  // when we append it, so omitted filters don't appear in the URL at all.
  useEffect(() => {
    setResult(null)
    setSelectedId(null)

    const params = new URLSearchParams({ page })
    if (browseMode === 'species' && species) params.append('species', species)
    if (browseMode === 'individual' && individual) params.append('individual_id', individual)
    if (dateFrom) params.append('date_from', dateFrom)
    if (dateTo) params.append('date_to', dateTo)

    fetch(`/api/detections?${params}`)
      .then(r => r.json())
      .then(data => setResult(data))
  }, [page, browseMode, species, individual, dateFrom, dateTo])

  // changing any filter resets to page 1 — if you're on page 3 of unfiltered
  // results, page 3 may not exist in the filtered set.
  // wrapping each setter ensures the page reset and filter change happen together.
  const handleBrowseModeChange = value => { setBrowseMode(value); setPage(1) }
  const handleSpeciesChange = value => { setSpecies(value); setPage(1) }
  const handleIndividualChange = value => { setIndividual(value); setPage(1) }
  const handleDateFromChange = value => { setDateFrom(value); setPage(1) }
  const handleDateToChange = value => { setDateTo(value); setPage(1) }

  return (
    <div className={`browse-layout${selectedId !== null ? ' browse-layout--open' : ''}`}>
      <div className="detection-grid-container">
        <FilterBar
          browseMode={browseMode} onBrowseModeChange={handleBrowseModeChange}
          species={species} onSpeciesChange={handleSpeciesChange}
          speciesList={speciesList}
          individual={individual} onIndividualChange={handleIndividualChange}
          individualList={individualList}
          dateFrom={dateFrom} onDateFromChange={handleDateFromChange}
          dateTo={dateTo} onDateToChange={handleDateToChange}
        />

        {result === null ? (
          <div>Loading…</div>
        ) : (
          <>
            <div className="detection-grid">
              {result.detections.map(detection => (
                <div
                  key={detection.id}
                  className={`grid-cell${selectedId === detection.id ? ' grid-cell--selected' : ''}`}
                  onClick={() => setSelectedId(detection.id)}
                >
                  <img
                    src={detection.crop_url}
                    alt={detection.label}
                    title={`${detection.label} (${(detection.confidence * 100).toFixed(1)}%)`}
                  />
                  <div className="grid-cell-label">
                    {detection.individual_id !== null
                      ? (detection.nickname || `#${detection.individual_id}`)
                      : detection.label}
                  </div>
                </div>
              ))}
            </div>

            <div className="pagination">
              <button onClick={() => setPage(p => p - 1)} disabled={page === 1}>
                ← prev
              </button>
              <span className="pagination-info">
                page {page} of {Math.ceil(result.total / result.page_size)}
              </span>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={page === Math.ceil(result.total / result.page_size)}
              >
                next →
              </button>
            </div>
          </>
        )}
      </div>

      {selectedId !== null && (
        <DetailPanel
          detectionId={selectedId}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  )
}
