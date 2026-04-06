"""Stats API endpoints — summary counts and analytics data."""

from fastapi import APIRouter, HTTPException

import crittercam.config as config_module
import crittercam.pipeline.db as db

router = APIRouter()


@router.get('/api/stats/summary')
def summary() -> dict:
    """Return top-level summary counts for the dashboard Home tab.

    Returns:
        dict with total_images, total_detections, and species_seen counts
    """
    try:
        config = config_module.load()
    except FileNotFoundError:
        raise HTTPException(
            status_code=500, detail='crittercam config not found — run crittercam setup first'
        )

    conn = db.connect(config.db_path)

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
