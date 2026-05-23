// FilterSidebar uses controlled inputs throughout — every input has a value=
// prop (what React renders) and an onChange= prop (how React hears changes).
// This makes React state the single source of truth: the parent always knows
// the current filter values and can reset them with a single state update.
//
// When any field changes, onChange is called with the full filter state so
// the parent doesn't need to merge partial updates itself.
export default function FilterSidebar({
  species,
  selectedSpecies,
  dateFrom,
  dateTo,
  onChange,
}) {
  const hasFilters = selectedSpecies || dateFrom || dateTo

  const handleChange = (field, value) => {
    onChange({ selectedSpecies, dateFrom, dateTo, [field]: value })
  }

  const handleClear = () => {
    onChange({ selectedSpecies: '', dateFrom: '', dateTo: '' })
  }

  return (
    <div className="filter-sidebar">
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
