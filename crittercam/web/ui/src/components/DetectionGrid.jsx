import { useState, useEffect } from 'react'
import { toggleFavorite } from '../api.js'
import DetectionModal from './DetectionModal.jsx'
import FilterSidebar from './FilterSidebar.jsx'
import DetectionCard from './DetectionCard.jsx'
import Button from './Button.jsx'

export default function DetectionGrid() {
  const [page, setPage] = useState(1)
  const [result, setResult] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  // selectedDetection holds the full object for whichever grid cell is open.
  // DetectionModal is presentational — it receives this object directly
  // rather than fetching by ID itself.
  const [selectedDetection, setSelectedDetection] = useState(null)

  // when navigating across a page boundary, records which end of the
  // incoming page to auto-select once the fetch completes ('first' | 'last').
  const [pendingSelect, setPendingSelect] = useState(null)

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

  // fetch the full detection object whenever the selected grid cell changes.
  useEffect(() => {
    if (selectedId === null) { setSelectedDetection(null); return }
    fetch(`/api/detections/${selectedId}`)
      .then(r => r.json())
      .then(data => setSelectedDetection(data))
  }, [selectedId])

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

  // after a cross-page navigation, auto-select the first or last detection
  // once the new page's result arrives.
  useEffect(() => {
    if (result === null || pendingSelect === null) return
    const det = pendingSelect === 'first'
      ? result.detections[0]
      : result.detections[result.detections.length - 1]
    if (det) setSelectedId(det.id)
    setPendingSelect(null)
  }, [result, pendingSelect])

  // navigation within the modal — handles both within-page and cross-page moves.
  const idx = result ? result.detections.findIndex(d => d.id === selectedId) : -1
  const totalPages = result ? Math.ceil(result.total / result.page_size) : 0
  const hasPrev = idx > 0 || page > 1
  const hasNext = result !== null && (idx < result.detections.length - 1 || page < totalPages)

  const handlePrev = () => {
    if (idx > 0) {
      setSelectedId(result.detections[idx - 1].id)
    } else {
      setPendingSelect('last')
      setPage(p => p - 1)
    }
  }

  const handleNext = () => {
    if (idx < result.detections.length - 1) {
      setSelectedId(result.detections[idx + 1].id)
    } else {
      setPendingSelect('first')
      setPage(p => p + 1)
    }
  }

  // changing any filter resets to page 1 — if you're on page 3 of unfiltered
  // results, page 3 may not exist in the filtered set.
  // wrapping each setter ensures the page reset and filter change happen together.
  // FilterSidebar fires onChange with the full state object — unpack it here
  // and reset to page 1 on any filter change.
  const handleFilterChange = ({ browseMode: bm, selectedSpecies: sp, selectedIndividual: ind, dateFrom: df, dateTo: dt }) => {
    setBrowseMode(bm)
    setSpecies(sp)
    setIndividual(ind)
    setDateFrom(df)
    setDateTo(dt)
    setPage(1)
  }

  return (
    <div className="flex gap-6 items-start">
      <FilterSidebar
        browseMode={browseMode}
        species={speciesList}
        selectedSpecies={species}
        individuals={individualList}
        selectedIndividual={individual}
        dateFrom={dateFrom}
        dateTo={dateTo}
        onChange={handleFilterChange}
      />

      <div className="flex-1 min-w-0">
        {result === null ? (
          <div>Loading…</div>
        ) : (
          <>
            <div className="grid grid-cols-4 gap-3">
              {result.detections.map(detection => (
                <DetectionCard
                  key={detection.id}
                  cropUrl={detection.crop_url}
                  label={detection.label.split(';').pop()}
                  confidence={detection.confidence}
                  capturedAt={detection.captured_at}
                  selected={selectedId === detection.id}
                  onClick={() => setSelectedId(detection.id)}
                />
              ))}
            </div>

            <div className="flex items-center justify-center gap-4 mt-5">
              <Button
                label="← prev"
                variant="ghost"
                onClick={() => setPage(p => p - 1)}
                disabled={page === 1}
              />
              <span className="text-sm text-base-content/60">
                page {page} of {Math.ceil(result.total / result.page_size)}
              </span>
              <Button
                label="next →"
                variant="ghost"
                onClick={() => setPage(p => p + 1)}
                disabled={page === Math.ceil(result.total / result.page_size)}
              />
            </div>
          </>
        )}
      </div>

      {selectedDetection !== null && (
        <DetectionModal
          detection={selectedDetection}
          onClose={() => setSelectedId(null)}
          hasPrev={hasPrev}
          hasNext={hasNext}
          onPrev={handlePrev}
          onNext={handleNext}
          isFavorite={selectedDetection.favorite === 1}
          onFavorite={() => toggleFavorite(selectedDetection, setSelectedDetection)}
        />
      )}
    </div>
  )
}
