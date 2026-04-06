"""Detections API endpoints — filterable detection list and single-detection detail."""

from fastapi import APIRouter, HTTPException

import crittercam.config as config_module
import crittercam.pipeline.db as db

router = APIRouter()


@router.get('/api/detections/first')
def first_detection() -> dict:
    """Return the first active detection that has a crop image.

    Used in Step 4 to demonstrate image serving.

    Returns:
        dict with id, label, confidence, and crop_url

    Raises:
        HTTPException: 404 if no qualifying detection exists
    """
    try:
        config = config_module.load()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail='crittercam config not found — run crittercam setup first')

    conn = db.connect(config.db_path)

    row = conn.execute(
        '''
        SELECT id, label, confidence, crop_path
        FROM detections
        WHERE is_active = 1
          AND crop_path IS NOT NULL
          AND label != 'blank'
        ORDER BY id ASC
        LIMIT 1
        '''
    ).fetchone()

    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail='no detections found')

    return {
        'id': row['id'],
        'label': row['label'],
        'confidence': round(row['confidence'], 3),
        # the browser will request this URL to load the image
        'crop_url': f'/media/{row["crop_path"]}',
    }
