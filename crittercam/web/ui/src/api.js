/**
 * Toggle the favorite flag on a media item.
 *
 * Updates local state optimistically so the UI responds immediately,
 * then syncs the new value to the server in the background.
 *
 * @param {object} detection - the currently selected detection object
 * @param {function} setSelectedDetection - React state setter for selectedDetection
 */
export function toggleFavorite(detection, setSelectedDetection) {
  const newValue = detection.favorite === 1 ? 0 : 1
  setSelectedDetection(prev => ({ ...prev, favorite: newValue }))
  fetch(`/api/media/${detection.media_id}/favorite`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ favorite: newValue }),
  })
}
