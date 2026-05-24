/**
 * Send the favorite value for a media item to the server.
 *
 * @param {number} mediaId
 * @param {number} newValue - 0 or 1
 */
export function patchFavorite(mediaId, newValue) {
  fetch(`/api/media/${mediaId}/favorite`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ favorite: newValue }),
  })
}

/**
 * Toggle the favorite flag on the currently open detection (modal context).
 *
 * Updates selectedDetection state optimistically. The optional onUpdate
 * callback receives the new value so the caller can also sync a list.
 *
 * @param {object} detection - the currently selected detection object
 * @param {function} setSelectedDetection - React state setter for selectedDetection
 * @param {function} [onUpdate] - called with the new favorite value (0 or 1)
 */
export function toggleFavorite(detection, setSelectedDetection, onUpdate) {
  const newValue = detection.favorite === 1 ? 0 : 1
  setSelectedDetection(prev => ({ ...prev, favorite: newValue }))
  onUpdate?.(newValue)
  patchFavorite(detection.media_id, newValue)
}

/**
 * Toggle the favorite flag on a detection inside a flat list.
 *
 * Updates the list state optimistically by id.
 *
 * @param {object} detection - the detection to toggle
 * @param {function} setList - React state setter for the detections array
 */
export function toggleFavoriteInList(detection, setList) {
  const newValue = detection.favorite === 1 ? 0 : 1
  setList(prev => prev.map(d => d.id === detection.id ? { ...d, favorite: newValue } : d))
  patchFavorite(detection.media_id, newValue)
}
