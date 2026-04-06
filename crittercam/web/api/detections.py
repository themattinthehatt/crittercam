"""Detections API endpoints — filterable detection list and single-detection detail."""

from fastapi import APIRouter, HTTPException

from crittercam.web.api import get_conn

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
    conn = get_conn()

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
        'crop_url': f'/media/{row["crop_path"]}',
    }


@router.get('/api/detections/{detection_id}')
def get_detection(detection_id: int) -> dict:
    """Return a single detection by ID, with adjacent IDs for navigation.

    prev_id and next_id are the nearest active detections with crop images
    in either direction. They are null at the boundaries of the dataset.

    Args:
        detection_id: primary key of the detection row

    Returns:
        dict with id, label, confidence, crop_url, prev_id, next_id

    Raises:
        HTTPException: 404 if the detection does not exist
    """
    conn = get_conn()

    row = conn.execute(
        '''
        SELECT id, label, confidence, crop_path
        FROM detections
        WHERE id = :id
          AND is_active = 1
          AND crop_path IS NOT NULL
          AND label != 'blank'
        ''',
        {'id': detection_id},
    ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f'detection {detection_id} not found')

    # find the nearest detection with a lower id
    prev_row = conn.execute(
        '''
        SELECT id FROM detections
        WHERE id < :id
          AND is_active = 1
          AND crop_path IS NOT NULL
          AND label != 'blank'
        ORDER BY id DESC
        LIMIT 1
        ''',
        {'id': detection_id},
    ).fetchone()

    # find the nearest detection with a higher id
    next_row = conn.execute(
        '''
        SELECT id FROM detections
        WHERE id > :id
          AND is_active = 1
          AND crop_path IS NOT NULL
          AND label != 'blank'
        ORDER BY id ASC
        LIMIT 1
        ''',
        {'id': detection_id},
    ).fetchone()

    conn.close()

    return {
        'id': row['id'],
        'label': row['label'],
        'confidence': round(row['confidence'], 3),
        'crop_url': f'/media/{row["crop_path"]}',
        'prev_id': prev_row['id'] if prev_row else None,
        'next_id': next_row['id'] if next_row else None,
    }
