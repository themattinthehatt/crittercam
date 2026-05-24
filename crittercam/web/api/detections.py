"""Detections API endpoints — filterable detection list and single-detection detail."""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from crittercam.web.api import get_conn

router = APIRouter()


PAGE_SIZE = 24


@router.get('/api/species')
def list_species() -> list[str]:
    """Return a sorted list of distinct species names present in active detections.

    Labels in the database are stored as semicolon-joined taxonomy paths
    (e.g. 'animalia;chordata;...;domeastic cat'). This endpoint returns only
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
          AND LOWER(label) NOT LIKE '%blank%'
        '''
    ).fetchall()
    conn.close()
    return sorted({row['label'].split(';')[-1] for row in rows})


@router.get('/api/individuals')
def list_individuals() -> list[dict]:
    """Return all individuals that have at least one active detection with a crop.

    Returns:
        list of dicts with id, species_leaf, and nickname (nullable), sorted by id
    """
    conn = get_conn()
    rows = conn.execute(
        '''
        SELECT DISTINCT ind.id, ind.species_leaf, ind.nickname
        FROM individuals ind
        JOIN detections d ON d.individual_id = ind.id
        WHERE d.is_active = 1
          AND d.crop_path IS NOT NULL
        ORDER BY ind.id
        '''
    ).fetchall()
    conn.close()
    return [
        {'id': row['id'], 'species_leaf': row['species_leaf'], 'nickname': row['nickname']}
        for row in rows
    ]


@router.get('/api/detections')
def list_detections(
    page: int = 1,
    page_size: int = PAGE_SIZE,
    species: str | None = None,
    individual_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    only_favorites: bool = False,
) -> dict:
    """Return a paginated, filterable list of active detections for the thumbnail grid.

    Args:
        page: 1-based page number
        page_size: number of detections per page (default 24)
        species: leaf species name to filter by (e.g. 'vulpes vulpes'); omit for all
        date_from: ISO date string (YYYY-MM-DD) — include detections on or after this date
        date_to: ISO date string (YYYY-MM-DD) — include detections on or before this date
        only_favorites: if True, restrict to detections whose media is marked favorite

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
        "LOWER(d.label) NOT LIKE '%blank%'",
        "LOWER(d.label) NOT LIKE '%human%'",
    ]
    params: dict = {}

    if species:
        # match labels that are exactly the species name, or end with ';species'
        conditions.append("(d.label = :species OR d.label LIKE '%;' || :species)")
        params['species'] = species

    if individual_id is not None:
        conditions.append('d.individual_id = :individual_id')
        params['individual_id'] = individual_id

    if date_from:
        conditions.append('i.captured_at >= :date_from')
        params['date_from'] = date_from

    if date_to:
        # date(:date_to, '+1 day') shifts the boundary to include all times on date_to
        conditions.append("i.captured_at < date(:date_to, '+1 day')")
        params['date_to'] = date_to

    if only_favorites:
        conditions.append('i.favorite = 1')

    where = ' AND '.join(conditions)

    total = conn.execute(
        f'''
        SELECT COUNT(*) FROM detections d
        JOIN media i ON i.id = d.media_id
        WHERE {where}
        ''',
        params,
    ).fetchone()[0]

    rows = conn.execute(
        f'''
        SELECT d.id, d.label, d.confidence, d.crop_path,
               d.individual_id, ind.nickname, i.captured_at,
               i.id AS media_id, i.favorite
        FROM detections d
        JOIN media i ON i.id = d.media_id
        LEFT JOIN individuals ind ON ind.id = d.individual_id
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
                'confidence': round(row['confidence'], 3) if row['confidence'] is not None else None,
                'crop_url': f'/media/{row["crop_path"]}',
                'individual_id': row['individual_id'],
                'nickname': row['nickname'],
                'captured_at': row['captured_at'],
                'media_id': row['media_id'],
                'favorite': row['favorite'],
            }
            for row in rows
        ],
        'total': total,
        'page': page,
        'page_size': page_size,
    }


@router.get('/api/detections/recent_by_species')
def recent_by_species() -> list[dict]:
    """Return the most recent active detection for each distinct species.

    Excludes blank frames and human detections. The subquery finds the highest
    detection id per label; the outer query joins back to retrieve the full row.
    Results are ordered by detection id descending (most recently detected species
    first).

    Returns:
        list of dicts, each with id, label, confidence, crop_url, captured_at
    """
    conn = get_conn()

    rows = conn.execute(
        '''
        SELECT d.id, d.label, d.confidence, d.crop_path,
               i.captured_at, i.id AS media_id, i.favorite
        FROM detections d
        JOIN media i ON i.id = d.media_id
        INNER JOIN (
            SELECT label, MAX(id) AS max_id
            FROM detections
            WHERE is_active = 1
              AND crop_path IS NOT NULL
              AND LOWER(label) NOT LIKE '%blank%'
              AND LOWER(label) NOT LIKE '%human%'
            GROUP BY label
        ) latest ON d.id = latest.max_id
        ORDER BY d.id DESC
        '''
    ).fetchall()

    conn.close()

    return [
        {
            'id': row['id'],
            'label': row['label'].split(';')[-1],
            'confidence': round(row['confidence'], 3) if row['confidence'] is not None else None,
            'crop_url': f'/media/{row["crop_path"]}',
            'captured_at': row['captured_at'],
            'media_id': row['media_id'],
            'favorite': row['favorite'],
        }
        for row in rows
    ]


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
               d.individual_id, ind.nickname,
               d.label_assigned_by,
               i.id AS media_id, i.path AS image_path,
               i.captured_at, i.temperature_c, i.favorite
        FROM detections d
        JOIN media i ON i.id = d.media_id
        LEFT JOIN individuals ind ON ind.id = d.individual_id
        WHERE d.id = :id
          AND d.is_active = 1
          AND d.crop_path IS NOT NULL
          AND LOWER(d.label) NOT LIKE '%blank%'
          AND LOWER(d.label) NOT LIKE '%human%'
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
          AND LOWER(label) NOT LIKE '%blank%'
          AND LOWER(label) NOT LIKE '%human%'
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
          AND LOWER(label) NOT LIKE '%blank%'
          AND LOWER(label) NOT LIKE '%human%'
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
        'confidence': round(row['confidence'], 3) if row['confidence'] is not None else None,
        'label_assigned_by': row['label_assigned_by'],
        'crop_url': f'/media/{row["crop_path"]}',
        'image_url': f'/media/{row["image_path"]}',
        'bbox': bbox,
        'captured_at': row['captured_at'],
        'temperature_c': row['temperature_c'],
        'individual_id': row['individual_id'],
        'nickname': row['nickname'],
        'media_id': row['media_id'],
        'favorite': row['favorite'],
        'prev_id': prev_row['id'] if prev_row else None,
        'next_id': next_row['id'] if next_row else None,
    }


class DetectionPatch(BaseModel):
    """Request body for the patch_detection endpoint."""

    species_leaf: str
    individual_id: int | None


@router.patch('/api/detections/{detection_id}')
def patch_detection(detection_id: int, payload: DetectionPatch) -> dict:
    """Update the species label and individual assignment on a detection.

    The caller supplies only the leaf species name (e.g. 'vulpes vulpes'); the
    endpoint resolves the canonical full taxonomy label by looking up an existing
    detection with that leaf so the stored format stays consistent.

    Args:
        detection_id: primary key of the detection row
        payload: species_leaf (leaf name) and individual_id (int or null)

    Returns:
        updated detection dict in the same shape as GET /api/detections/{id}

    Raises:
        HTTPException: 404 if the detection does not exist
        HTTPException: 422 if species_leaf does not match any known label
    """
    conn = get_conn()

    row = conn.execute(
        '''
        SELECT d.id FROM detections d
        WHERE d.id = :id AND d.is_active = 1
        ''',
        {'id': detection_id},
    ).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f'detection {detection_id} not found')

    # resolve the full taxonomy label from any existing detection with this leaf
    label_row = conn.execute(
        '''
        SELECT label FROM detections
        WHERE (label = :leaf OR label LIKE '%;' || :leaf)
          AND is_active = 1
        LIMIT 1
        ''',
        {'leaf': payload.species_leaf},
    ).fetchone()
    if label_row is None:
        conn.close()
        raise HTTPException(status_code=422, detail=f'unknown species: {payload.species_leaf}')

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        '''
        UPDATE detections
        SET label                  = :label,
            confidence             = NULL,
            label_assigned_by      = 'human',
            label_assigned_at      = :now,
            individual_id          = :individual_id,
            individual_assigned_by = 'human',
            individual_assigned_at = :now
        WHERE id = :id
        ''',
        {'label': label_row['label'], 'now': now, 'individual_id': payload.individual_id, 'id': detection_id},
    )
    conn.commit()
    conn.close()

    # return the full detection object so the caller can update UI state in one round-trip
    return get_detection(detection_id)


@router.delete('/api/media/{media_id}')
def delete_media(media_id: int) -> dict:
    """Delete a media item and all its associated detections and processing jobs.

    Detections and processing jobs are deleted first to satisfy foreign key
    constraints before the media row itself is removed.

    Args:
        media_id: primary key of the media row

    Returns:
        dict with deleted media_id

    Raises:
        HTTPException: 404 if the media item does not exist
    """
    conn = get_conn()

    row = conn.execute('SELECT id FROM media WHERE id = :id', {'id': media_id}).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f'media {media_id} not found')

    # record which individuals are referenced before deletion so we can check
    # for orphans afterward.
    individual_ids = [
        r['individual_id'] for r in conn.execute(
            'SELECT DISTINCT individual_id FROM detections WHERE media_id = :id AND individual_id IS NOT NULL',
            {'id': media_id},
        ).fetchall()
    ]

    # processing_jobs can reference either media (media_id) or detections
    # (detection_id); both must be cleared before their referents can be deleted.
    det_ids = [
        r['id'] for r in
        conn.execute('SELECT id FROM detections WHERE media_id = :id', {'id': media_id}).fetchall()
    ]
    for det_id in det_ids:
        conn.execute('DELETE FROM processing_jobs WHERE detection_id = :id', {'id': det_id})
    conn.execute('DELETE FROM processing_jobs WHERE media_id = :id', {'id': media_id})
    conn.execute('DELETE FROM detections WHERE media_id = :id', {'id': media_id})
    conn.execute('DELETE FROM media WHERE id = :id', {'id': media_id})

    # remove individuals whose last detection was just deleted
    for ind_id in individual_ids:
        remaining = conn.execute(
            'SELECT COUNT(*) FROM detections WHERE individual_id = :id',
            {'id': ind_id},
        ).fetchone()[0]
        if remaining == 0:
            conn.execute('DELETE FROM individuals WHERE id = :id', {'id': ind_id})

    conn.commit()
    conn.close()

    return {'deleted': media_id}


class FavoritePayload(BaseModel):
    """Request body for the set_favorite endpoint."""

    favorite: int


@router.patch('/api/media/{media_id}/favorite')
def set_favorite(media_id: int, payload: FavoritePayload) -> dict:
    """Set or clear the favorite flag on a media item.

    Args:
        media_id: primary key of the media row
        payload: dict with 'favorite' key (0 or 1)

    Returns:
        dict with media_id and updated favorite value

    Raises:
        HTTPException: 404 if the media item does not exist
    """
    conn = get_conn()

    row = conn.execute('SELECT id FROM media WHERE id = :id', {'id': media_id}).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f'media {media_id} not found')

    conn.execute(
        'UPDATE media SET favorite = :favorite WHERE id = :id',
        {'favorite': payload.favorite, 'id': media_id},
    )
    conn.commit()
    conn.close()

    return {'media_id': media_id, 'favorite': payload.favorite}
