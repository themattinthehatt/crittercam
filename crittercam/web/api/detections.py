"""Detections API endpoints — filterable detection list and single-detection detail."""

from fastapi import APIRouter, HTTPException

from crittercam.web.api import get_conn

router = APIRouter()


PAGE_SIZE = 24


@router.get('/api/species')
def list_species() -> list[str]:
    """Return a sorted list of distinct species names present in active detections.

    Labels in the database are stored as semicolon-joined taxonomy paths
    (e.g. 'animalia;chordata;...;vulpes vulpes'). This endpoint returns only
    the leaf name (the last segment) for each distinct label.

    Returns:
        sorted list of species name strings
    """
    conn = get_conn()
    rows = conn.execute(
        '''
        SELECT DISTINCT label FROM detections
        WHERE is_active = 1
          AND crop_path IS NOT NULL
          AND label != 'blank'
        '''
    ).fetchall()
    conn.close()
    return sorted({row['label'].split(';')[-1] for row in rows})


@router.get('/api/detections')
def list_detections(
    page: int = 1,
    page_size: int = PAGE_SIZE,
    species: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Return a paginated, filterable list of active detections for the thumbnail grid.

    Args:
        page: 1-based page number
        page_size: number of detections per page (default 24)
        species: leaf species name to filter by (e.g. 'vulpes vulpes'); omit for all
        date_from: ISO date string (YYYY-MM-DD) — include detections on or after this date
        date_to: ISO date string (YYYY-MM-DD) — include detections on or before this date

    Returns:
        dict with 'detections' list, 'total' count, 'page', and 'page_size'
    """
    conn = get_conn()

    # build the WHERE clause from whichever filters were supplied.
    # conditions is a list of SQL fragments; params holds the bound values.
    # the f-string below only interpolates this list of hardcoded fragments —
    # user values are always passed through named parameters, never interpolated.
    conditions = [
        'd.is_active = 1',
        'd.crop_path IS NOT NULL',
        "d.label != 'blank'",
    ]
    params: dict = {}

    if species:
        # match labels that are exactly the species name, or end with ';species'
        conditions.append("(d.label = :species OR d.label LIKE '%;' || :species)")
        params['species'] = species

    if date_from:
        conditions.append('i.captured_at >= :date_from')
        params['date_from'] = date_from

    if date_to:
        # date(:date_to, '+1 day') shifts the boundary to include all times on date_to
        conditions.append("i.captured_at < date(:date_to, '+1 day')")
        params['date_to'] = date_to

    where = ' AND '.join(conditions)

    total = conn.execute(
        f'''
        SELECT COUNT(*) FROM detections d
        JOIN images i ON i.id = d.image_id
        WHERE {where}
        ''',
        params,
    ).fetchone()[0]

    rows = conn.execute(
        f'''
        SELECT d.id, d.label, d.confidence, d.crop_path
        FROM detections d
        JOIN images i ON i.id = d.image_id
        WHERE {where}
        ORDER BY d.id DESC
        LIMIT :limit OFFSET :offset
        ''',
        {**params, 'limit': page_size, 'offset': (page - 1) * page_size},
    ).fetchall()

    conn.close()

    return {
        'detections': [
            {
                'id': row['id'],
                'label': row['label'].split(';')[-1],
                'confidence': round(row['confidence'], 3),
                'crop_url': f'/media/{row["crop_path"]}',
            }
            for row in rows
        ],
        'total': total,
        'page': page,
        'page_size': page_size,
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
        SELECT d.id, d.label, d.confidence, d.crop_path,
               d.bbox_x, d.bbox_y, d.bbox_w, d.bbox_h,
               i.path AS image_path, i.captured_at, i.temperature_c
        FROM detections d
        JOIN images i ON i.id = d.image_id
        WHERE d.id = :id
          AND d.is_active = 1
          AND d.crop_path IS NOT NULL
          AND d.label != 'blank'
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

    has_bbox = row['bbox_x'] is not None
    bbox = {'x': row['bbox_x'], 'y': row['bbox_y'], 'w': row['bbox_w'], 'h': row['bbox_h']} if has_bbox else None

    return {
        'id': row['id'],
        'label': row['label'],
        'confidence': round(row['confidence'], 3),
        'crop_url': f'/media/{row["crop_path"]}',
        'image_url': f'/media/{row["image_path"]}',
        'bbox': bbox,
        'captured_at': row['captured_at'],
        'temperature_c': row['temperature_c'],
        'prev_id': prev_row['id'] if prev_row else None,
        'next_id': next_row['id'] if next_row else None,
    }
