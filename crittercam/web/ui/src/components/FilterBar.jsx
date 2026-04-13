// FilterBar is a "controlled" form — React state is the single source of truth
// for every input's value. Each input has:
//   value={...}    — what React renders into the field
//   onChange={...} — what happens when the user types/selects something
//
// Without value=, inputs are "uncontrolled": the DOM owns the value and React
// can't observe or reset it. Controlled inputs let the parent clear all fields
// with a single state update.

export default function FilterBar({
  browseMode, onBrowseModeChange,
  species, onSpeciesChange,
  speciesList,
  individual, onIndividualChange,
  individualList,
  dateFrom, onDateFromChange,
  dateTo, onDateToChange,
}) {
  const hasFilters = (browseMode === 'species' ? species : individual) || dateFrom || dateTo

  // switching modes clears both the species and individual filters
  const handleModeChange = value => {
    onBrowseModeChange(value)
    onSpeciesChange('')
    onIndividualChange('')
  }

  const handleClear = () => {
    onSpeciesChange('')
    onIndividualChange('')
    onDateFromChange('')
    onDateToChange('')
  }

  return (
    <div className="filter-bar">
      <label className="filter-field">
        <span className="filter-label">browse by</span>
        <select value={browseMode} onChange={e => handleModeChange(e.target.value)}>
          <option value="species">species</option>
          <option value="individual">individual</option>
        </select>
      </label>

      <div className="filter-divider" />

      {browseMode === 'species' ? (
        <label className="filter-field">
          <span className="filter-label">species</span>
          <select value={species} onChange={e => onSpeciesChange(e.target.value)}>
            <option value="">all</option>
            {speciesList.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
      ) : (
        <label className="filter-field">
          <span className="filter-label">individual</span>
          <select value={individual} onChange={e => onIndividualChange(e.target.value)}>
            <option value="">all</option>
            {individualList.map(ind => (
              <option key={ind.id} value={String(ind.id)}>
                {ind.nickname || `#${ind.id}`}
              </option>
            ))}
          </select>
        </label>
      )}

      <label className="filter-field">
        <span className="filter-label">from</span>
        <input
          type="date"
          value={dateFrom}
          onChange={e => onDateFromChange(e.target.value)}
        />
      </label>

      <label className="filter-field">
        <span className="filter-label">to</span>
        <input
          type="date"
          value={dateTo}
          onChange={e => onDateToChange(e.target.value)}
        />
      </label>

      {hasFilters && (
        <button className="filter-clear" onClick={handleClear}>
          clear filters
        </button>
      )}
    </div>
  )
}
