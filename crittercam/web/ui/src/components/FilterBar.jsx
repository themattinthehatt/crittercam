// FilterBar is a "controlled" form — React state is the single source of truth
// for every input's value. Each input has:
//   value={...}    — what React renders into the field
//   onChange={...} — what happens when the user types/selects something
//
// Without value=, inputs are "uncontrolled": the DOM owns the value and React
// can't observe or reset it. Controlled inputs let the parent clear all fields
// with a single state update.

export default function FilterBar({
  species, onSpeciesChange,
  dateFrom, onDateFromChange,
  dateTo, onDateToChange,
  speciesList,
}) {
  const hasFilters = species || dateFrom || dateTo

  return (
    <div className="filter-bar">
      <label className="filter-field">
        <span className="filter-label">species</span>
        <select value={species} onChange={e => onSpeciesChange(e.target.value)}>
          <option value="">all</option>
          {speciesList.map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </label>

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
        <button
          className="filter-clear"
          onClick={() => {
            onSpeciesChange('')
            onDateFromChange('')
            onDateToChange('')
          }}
        >
          clear filters
        </button>
      )}
    </div>
  )
}
