import { TrashIcon, StarIcon, PencilIcon } from './icons.jsx'

// BatchActionBar appears above the detection grid whenever one or more cards
// are batch-selected. It shows a count, a clear button, and action icons.
// allFavorited drives the star appearance: solid yellow when every selected
// detection is already favorited (next click will unfavorite), outline otherwise.
// showDeleteConfirm switches the bar into a delete confirmation state.
export default function BatchActionBar({
  count, allFavorited,
  onClear, onDelete, onFavorite, onEdit,
  showDeleteConfirm = false, onDeleteConfirm, onDeleteCancel,
}) {
  if (showDeleteConfirm) {
    return (
      <div className="flex items-center justify-between bg-base-200 rounded px-3 py-2 mb-3">
        <span className="text-sm text-error">
          Delete {count} observation{count !== 1 ? 's' : ''}?
        </span>
        <div className="flex items-center gap-2">
          <button
            className="btn btn-xs btn-ghost border border-base-content/20"
            onClick={onDeleteCancel}
          >
            cancel
          </button>
          <button className="btn btn-xs btn-error" onClick={onDeleteConfirm}>
            delete
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-between bg-base-200 rounded px-3 py-2 mb-3">
      <div className="flex items-center gap-3">
        <span className="text-sm text-base-content/80">{count} selected</span>
        <button className="btn btn-xs btn-ghost text-base-content/50" onClick={onClear}>
          clear
        </button>
      </div>
      <div className="flex items-center gap-1">
        <button
          className="btn btn-sm btn-ghost text-error"
          onClick={onDelete}
          title="Delete selected"
        >
          <TrashIcon className="size-4" />
        </button>
        <button
          className={`btn btn-sm btn-ghost ${allFavorited ? 'text-yellow-400' : 'text-base-content/50'}`}
          onClick={onFavorite}
          title={allFavorited ? 'Unfavorite selected' : 'Favorite selected'}
        >
          <StarIcon className={`size-4 ${allFavorited ? 'fill-current' : ''}`} />
        </button>
        <button
          className="btn btn-sm btn-ghost text-base-content/50"
          onClick={onEdit}
          title="Edit selected"
        >
          <PencilIcon className="size-4" />
        </button>
      </div>
    </div>
  )
}
