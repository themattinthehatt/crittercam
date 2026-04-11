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

    total_images = conn.execute('SELECT COUNT(*) FROM images').fetchone()[0]

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
def detections_over_time() -> dict:
    """Return weekly detection counts per species for the past year.

    Only species with more than 10 total detections in the period are included.
    Weeks with no detections for a given species are filled with zero so that
    every species has a value for every week in the range.

    Returns:
        dict with:
          - 'weeks': sorted list of week strings (YYYY-WW)
          - 'species': list of species names included in the data
          - 'data': list of dicts, one per week, with species counts as keys
    """
    conn = get_conn()

    # aggregate detection counts by raw label and ISO week.
    # strftime('%Y-%W', ...) produces strings like '2025-03' that sort correctly.
    rows = conn.execute(
        '''
        SELECT d.label, strftime('%Y-%W', i.captured_at) AS week, COUNT(*) AS count
        FROM detections d
        JOIN images i ON i.id = d.image_id
        WHERE d.is_active = 1
          AND d.crop_path IS NOT NULL
          AND LOWER(d.label) NOT LIKE '%blank%'
          AND LOWER(d.label) NOT LIKE '%human%'
          AND i.captured_at IS NOT NULL
          AND i.captured_at >= date('now', '-1 year')
        GROUP BY d.label, week
        ORDER BY week ASC
        '''
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

    # filter to species with more than 10 total detections in the period
    qualifying = {
        species: weeks
        for species, weeks in by_species.items()
        if sum(weeks.values()) > 10
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
