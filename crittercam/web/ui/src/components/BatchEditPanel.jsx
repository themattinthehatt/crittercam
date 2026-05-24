import { useState } from 'react'

// BatchEditPanel replaces the BatchActionBar while the user is editing a batch.
// Species '' = no change; individual 'no-change' = no change, 'none' = clear,
// a numeric string = assign to that individual.
// onSave is called with (speciesLeaf, editIndividual) using those sentinels;
// the parent resolves per-detection values before calling the API.
export default function BatchEditPanel({ count, speciesList, individualList, onSave, onCancel }) {
  const [editSpecies, setEditSpecies] = useState('')
  const [editIndividual, setEditIndividual] = useState('no-change')

  // save is only meaningful when at least one field will actually change
  const canSave = editSpecies !== '' || editIndividual !== 'no-change'

  return (
    <div className="flex items-center gap-3 bg-base-200 rounded px-3 py-2 mb-3">
      <span className="text-sm text-base-content/60 whitespace-nowrap flex-shrink-0">
        apply to {count} selected:
      </span>
      <span className="text-xs uppercase tracking-wide text-base-content/40 flex-shrink-0">Species</span>
      <select
        className="select select-xs select-bordered flex-1 capitalize"
        value={editSpecies}
        onChange={e => setEditSpecies(e.target.value)}
      >
        <option value="">— no change —</option>
        {speciesList.map(s => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>
      <span className="text-xs uppercase tracking-wide text-base-content/40 flex-shrink-0">Individual</span>
      <select
        className="select select-xs select-bordered flex-1"
        value={editIndividual}
        onChange={e => setEditIndividual(e.target.value)}
      >
        <option value="no-change">— no change —</option>
        <option value="none">— none —</option>
        {individualList.map(ind => (
          <option key={ind.id} value={String(ind.id)}>
            {ind.nickname ? `${ind.nickname} (id ${ind.id})` : `id ${ind.id}`}
          </option>
        ))}
      </select>
      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          className="btn btn-xs btn-ghost border border-base-content/20"
          onClick={onCancel}
        >
          cancel
        </button>
        <button
          className="btn btn-xs btn-primary"
          onClick={() => onSave(editSpecies, editIndividual)}
          disabled={!canSave}
        >
          save
        </button>
      </div>
    </div>
  )
}
