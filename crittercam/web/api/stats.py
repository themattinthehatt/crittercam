"""Stats API endpoints — summary counts and analytics data."""

from collections import defaultdict

from fastapi import APIRouter

from crittercam.web.api import get_conn

router = APIRouter()


@router.get('/api/stats/summary')
def summary() -> dict:
    """Return top-level summary counts for the dashboard Home tab.

    Returns:
        dict with total_images, total_detections, and species_seen counts
    """
    conn = get_conn()

    total_images = conn.execute('SELECT COUNT(*) FROM media').fetchone()[0]

    total_detections = conn.execute(
        'SELECT COUNT(*) FROM detections WHERE is_active = 1'
    ).fetchone()[0]

    species_seen = conn.execute(
        "SELECT COUNT(DISTINCT label) FROM detections WHERE is_active = 1 AND LOWER(label) NOT LIKE '%blank%'"
    ).fetchone()[0]

    conn.close()

    return {
        'total_images': total_images,
        'total_detections': total_detections,
        'species_seen': species_seen,
    }


@router.get('/api/stats/detections_over_time')
def detections_over_time(
    deployment_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Return weekly detection counts per species for a time window.

    Only species with at least 50 total detections in the period are included.
    Weeks with no detections for a given species are filled with zero so that
    every species has a value for every week in the range.

    Args:
        deployment_id: restrict to detections from media in this deployment
        date_from: ISO date string (YYYY-MM-DD) — start of window; defaults to one year ago
        date_to: ISO date string (YYYY-MM-DD) — end of window (inclusive); defaults to now

    Returns:
        dict with:
          - 'weeks': sorted list of week strings (YYYY-WW)
          - 'species': list of species names included in the data
          - 'data': list of dicts, one per week, with species counts as keys
    """
    conn = get_conn()

    conditions = [
        'd.is_active = 1',
        'd.crop_path IS NOT NULL',
        "LOWER(d.label) NOT LIKE '%blank%'",
        "LOWER(d.label) NOT LIKE '%human%'",
        'i.captured_at IS NOT NULL',
    ]
    params: dict = {}

    if deployment_id is not None:
        conditions.append('i.deployment_id = :deployment_id')
        params['deployment_id'] = deployment_id

    if date_from:
        conditions.append('i.captured_at >= :date_from')
        params['date_from'] = date_from
    else:
        conditions.append("i.captured_at >= date('now', '-1 year')")

    if date_to:
        conditions.append("i.captured_at < date(:date_to, '+1 day')")
        params['date_to'] = date_to

    where = ' AND '.join(conditions)

    # aggregate detection counts by raw label and ISO week.
    # strftime('%Y-%W', ...) produces strings like '2025-03' that sort correctly.
    rows = conn.execute(
        f'''
        SELECT d.label, strftime('%Y-%W', i.captured_at) AS week, COUNT(*) AS count
        FROM detections d
        JOIN media i ON i.id = d.media_id
        WHERE {where}
        GROUP BY d.label, week
        ORDER BY week ASC
        ''',
        params,
    ).fetchall()

    conn.close()

    # pivot raw rows into {leaf_label: {week: count}}.
    # labels are stored as taxonomy paths; extract only the leaf segment.
    # multiple raw labels can share the same leaf (rare but possible), so we
    # accumulate counts rather than overwriting.
    by_species: dict = defaultdict(lambda: defaultdict(int))
    for row in rows:
        leaf = row['label'].split(';')[-1].lower()
        by_species[leaf][row['week']] += row['count']

    # filter to species with at least 100 total detections in the period
    qualifying = {
        species: weeks
        for species, weeks in by_species.items()
        if sum(weeks.values()) >= 50
    }

    all_weeks = sorted({week for weeks in qualifying.values() for week in weeks})
    species_list = sorted(qualifying.keys())

    # build wide-format rows: one dict per week with a key per species.
    # recharts expects this shape: [{week: '2025-03', 'red fox': 2, ...}, ...]
    data = [
        {'week': week, **{s: qualifying[s].get(week, 0) for s in species_list}}
        for week in all_weeks
    ]

    return {
        'weeks': all_weeks,
        'species': species_list,
        'data': data,
    }


@router.get('/api/stats/activity_by_hour')
def activity_by_hour(
    deployment_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Return hourly detection probability per species for a time window.

    Only species with at least 50 total detections in the period are included
    (same filter as detections_over_time). Each species' values across the 24
    one-hour bins sum to 1.0, so the chart shows when during the day each
    species is active relative to its own total.

    Args:
        deployment_id: restrict to detections from media in this deployment
        date_from: ISO date string (YYYY-MM-DD) — start of window; defaults to one year ago
        date_to: ISO date string (YYYY-MM-DD) — end of window (inclusive); defaults to now

    Returns:
        dict with:
          - 'species': sorted list of species names
          - 'data': list of 24 dicts (hours 00:00–23:00), probability per species
    """
    conn = get_conn()

    conditions = [
        'd.is_active = 1',
        'd.crop_path IS NOT NULL',
        "LOWER(d.label) NOT LIKE '%blank%'",
        "LOWER(d.label) NOT LIKE '%human%'",
        'i.captured_at IS NOT NULL',
    ]
    params: dict = {}

    if deployment_id is not None:
        conditions.append('i.deployment_id = :deployment_id')
        params['deployment_id'] = deployment_id

    if date_from:
        conditions.append('i.captured_at >= :date_from')
        params['date_from'] = date_from
    else:
        conditions.append("i.captured_at >= date('now', '-1 year')")

    if date_to:
        conditions.append("i.captured_at < date(:date_to, '+1 day')")
        params['date_to'] = date_to

    where = ' AND '.join(conditions)

    rows = conn.execute(
        f'''
        SELECT d.label, CAST(strftime('%H', i.captured_at) AS INTEGER) AS hour, COUNT(*) AS count
        FROM detections d
        JOIN media i ON i.id = d.media_id
        WHERE {where}
        GROUP BY d.label, hour
        ORDER BY hour ASC
        ''',
        params,
    ).fetchall()

    conn.close()

    by_species: dict = defaultdict(lambda: defaultdict(int))
    for row in rows:
        leaf = row['label'].split(';')[-1].lower()
        by_species[leaf][row['hour']] += row['count']

    qualifying = {
        sp: hours
        for sp, hours in by_species.items()
        if sum(hours.values()) >= 50
    }

    species_list = sorted(qualifying.keys())
    totals = {sp: sum(hours.values()) for sp, hours in qualifying.items()}

    data = []
    for h in range(24):
        row = {'hour': f'{h:02d}:00'}
        for sp in species_list:
            count = qualifying[sp].get(h, 0)
            row[sp] = round(count / totals[sp], 4) if totals[sp] > 0 else 0
        data.append(row)

    return {
        'species': species_list,
        'data': data,
    }
