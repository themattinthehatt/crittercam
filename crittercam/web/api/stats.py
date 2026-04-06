"""Stats API endpoints — summary counts and analytics data."""

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
        "SELECT COUNT(DISTINCT label) FROM detections WHERE is_active = 1 AND label != 'blank'"
    ).fetchone()[0]

    conn.close()

    return {
        'total_images': total_images,
        'total_detections': total_detections,
        'species_seen': species_seen,
    }
