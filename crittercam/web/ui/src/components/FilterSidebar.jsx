// FilterSidebar uses controlled inputs throughout — every input has a value=
// prop (what React renders) and an onChange= prop (how React hears changes).
// This makes React state the single source of truth: the parent always knows
// the current filter values and can reset them with a single state update.
//
// When any field changes, onChange is called with the full filter state so
// the parent doesn't need to merge partial updates itself.
export default function FilterSidebar({
  browseMode,
  species,
  selectedSpecies,
  individuals,
  selectedIndividual,
  dateFrom,
  dateTo,
  onChange,
}) {
  const activeFilter = browseMode === 'species' ? selectedSpecies : selectedIndividual
  const hasFilters = activeFilter || dateFrom || dateTo

  const handleChange = (field, value) => {
    onChange({ browseMode, selectedSpecies, selectedIndividual, dateFrom, dateTo, [field]: value })
  }

  // switching modes clears both entity filters so stale values don't carry over
  const handleModeChange = value => {
    onChange({ browseMode: value, selectedSpecies: '', selectedIndividual: '', dateFrom, dateTo })
  }

  const handleClear = () => {
    onChange({ browseMode, selectedSpecies: '', selectedIndividual: '', dateFrom: '', dateTo: '' })
  }

  return (
    <div className="filter-sidebar">
      <label className="filter-field">
        <span className="filter-label">browse by</span>
        <select value={browseMode} onChange={e => handleModeChange(e.target.value)}>
          <option value="species">species</option>
          <option value="individual">individual</option>
        </select>
      </label>

      {browseMode === 'species' ? (
        <label className="filter-field">
          <span className="filter-label">species</span>
          <select
            value={selectedSpecies}
            onChange={e => handleChange('selectedSpecies', e.target.value)}
          >
            <option value="">all</option>
            {species.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
      ) : (
        <label className="filter-field">
          <span className="filter-label">individual</span>
          <select
            value={selectedIndividual}
            onChange={e => handleChange('selectedIndividual', e.target.value)}
          >
            <option value="">all</option>
            {individuals.map(ind => (
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
          onChange={e => handleChange('dateFrom', e.target.value)}
        />
      </label>

      <label className="filter-field">
        <span className="filter-label">to</span>
        <input
          type="date"
          value={dateTo}
          onChange={e => handleChange('dateTo', e.target.value)}
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
