import Button from './Button.jsx'

// FilterSidebar uses controlled inputs throughout — every input has a value=
// prop (what React renders) and an onChange= prop (how React hears changes).
// This makes React state the single source of truth: the parent always knows
// the current filter values and can reset them with a single state update.
//
// When any field changes, onChange is called with the full filter state so
// the parent doesn't need to merge partial updates itself.
//
// The sidebar is absolutely positioned to the left of its containing
// browse-layout div, outside the centered content area.
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
    <div className="absolute top-0 right-[calc(100%+1.5rem)] w-40 flex flex-col gap-4">
      <label className="flex flex-col gap-1">
        <span className="text-xs uppercase tracking-wide text-base-content/50">browse by</span>
        <select
          className="select select-sm select-bordered w-full"
          value={browseMode}
          onChange={e => handleModeChange(e.target.value)}
        >
          <option value="species">species</option>
          <option value="individual">individual</option>
          <option value="favorited">favorited</option>
        </select>
      </label>

      {browseMode !== 'favorited' && (browseMode === 'species' ? (
        <label className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wide text-base-content/50">species</span>
          <select
            className="select select-sm select-bordered w-full capitalize"
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
        <label className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wide text-base-content/50">individual</span>
          <select
            className="select select-sm select-bordered w-full"
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
      ))}

      <label className="flex flex-col gap-1">
        <span className="text-xs uppercase tracking-wide text-base-content/50">from</span>
        <input
          className="input input-sm input-bordered w-full"
          type="date"
          value={dateFrom}
          onChange={e => handleChange('dateFrom', e.target.value)}
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-xs uppercase tracking-wide text-base-content/50">to</span>
        <input
          className="input input-sm input-bordered w-full"
          type="date"
          value={dateTo}
          onChange={e => handleChange('dateTo', e.target.value)}
        />
      </label>

      {hasFilters && (
        <Button label="clear filters" variant="ghost" size="sm" onClick={handleClear} />
      )}
    </div>
  )
}
