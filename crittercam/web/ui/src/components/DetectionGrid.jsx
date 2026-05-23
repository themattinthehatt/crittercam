import { useState, useEffect } from 'react'
import DetailPanel from './DetailPanel.jsx'
import FilterSidebar from './FilterSidebar.jsx'
import DetectionCard from './DetectionCard.jsx'
import Button from './Button.jsx'

export default function DetectionGrid() {
  const [page, setPage] = useState(1)
  const [result, setResult] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  // selectedDetection holds the full object for whichever grid cell is open.
  // DetailPanel is now presentational — it receives this object directly
  // rather than fetching by ID itself.
  const [selectedDetection, setSelectedDetection] = useState(null)

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
    <div className="flex gap-6 items-start relative">
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
            <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(160px,1fr))]">
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
        <DetailPanel
          detection={selectedDetection}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  )
}
