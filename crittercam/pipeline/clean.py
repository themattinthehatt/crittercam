"""Phase 3 cleanup: remove unwanted detections and their associated images and files."""

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CleanTarget:
    """A single active detection selected for deletion, with its parent image info.

    Attributes:
        detection_id: primary key of the active detection row
        crop_path: relative path to the detection crop, or None if absent
        image_id: primary key of the parent image row
        image_path: relative path to the raw image file
        thumb_path: relative path to the thumbnail, or None if absent
    """

    detection_id: int
    crop_path: str | None
    image_id: int
    image_path: str
    thumb_path: str | None


@dataclass
class CleanSummary:
    """Summary of a clean-db run.

    Attributes:
        detections: number of detection rows deleted (includes inactive rows)
        images: number of image rows deleted
        raw_images_deleted: number of raw image files deleted from disk
        thumbnails_deleted: number of thumbnail files deleted from disk
        crops_deleted: number of detection crop files deleted from disk
        files_missing: number of expected files not found on disk
    """

    detections: int = 0
    images: int = 0
    raw_images_deleted: int = 0
    thumbnails_deleted: int = 0
    crops_deleted: int = 0
    files_missing: int = 0


def find_targets(conn: sqlite3.Connection, labels: list[str]) -> list[CleanTarget]:
    """Find active detections whose label leaf matches any of the given labels.

    Labels in the database are stored as a semicolon-delimited taxonomy string
    (e.g. 'animalia;chordata;mammalia;...;homo sapiens'). Each provided label is
    matched against the final segment after the last semicolon, so the caller
    passes only the leaf name (e.g. 'human'). Labels without a hierarchy (e.g.
    'blank') are matched by exact equality.

    Only active detections (is_active = 1) are returned. Images where the current
    model run produced a matching label are selected; inactive rows for those images
    are cleaned up by delete_targets.

    Args:
        conn: open database connection
        labels: list of leaf label strings to match (e.g. ['human', 'blank'])

    Returns:
        list of CleanTarget, one per matching active detection, ordered by image id
    """
    if not labels:
        return []

    # match labels whose final semicolon-delimited segment equals the given leaf name
    params = {}
    conditions = []
    for i, label in enumerate(labels):
        params[f'labellike{i}'] = f'%;{label}'
        conditions.append(f'd.label LIKE :labellike{i}')
    where = ' OR '.join(conditions)

    rows = conn.execute(
        f'''
        SELECT d.id AS detection_id, d.crop_path,
               i.id AS image_id, i.path AS image_path, i.thumb_path
        FROM detections d
        JOIN images i ON i.id = d.image_id
        WHERE ({where}) AND d.is_active = 1
        ORDER BY i.id
        ''',
        params,
    ).fetchall()

    return [
        CleanTarget(
            detection_id=row['detection_id'],
            crop_path=row['crop_path'],
            image_id=row['image_id'],
            image_path=row['image_path'],
            thumb_path=row['thumb_path'],
        )
        for row in rows
    ]


def delete_targets(
    data_root: Path,
    conn: sqlite3.Connection,
    targets: list[CleanTarget],
) -> CleanSummary:
    """Delete detections, parent images, processing jobs, and all associated files.

    All detections for each target image are removed (not just the active ones), so
    inactive rows from prior model runs are also cleaned up. Deletion order respects
    FK constraints: processing_jobs first, then detections, then images.

    Files are deleted after the database transaction commits. Missing files are
    counted and reported rather than treated as errors.

    Args:
        data_root: root directory used to resolve relative paths
        conn: open database connection
        targets: list of CleanTarget as returned by find_targets

    Returns:
        CleanSummary with counts of rows and files deleted
    """
    if not targets:
        return CleanSummary()

    image_ids = [t.image_id for t in targets]
    img_params = {f'iid{i}': iid for i, iid in enumerate(image_ids)}
    img_placeholders = ', '.join(f':iid{i}' for i in range(len(image_ids)))

    # fetch all detections for these images (including inactive) for complete cleanup
    all_detections = conn.execute(
        f'SELECT id, crop_path FROM detections WHERE image_id IN ({img_placeholders})',
        img_params,
    ).fetchall()

    # delete from DB in FK order: processing_jobs → detections → images
    conn.execute(
        f'DELETE FROM processing_jobs WHERE image_id IN ({img_placeholders})',
        img_params,
    )
    if all_detections:
        det_params = {f'did{i}': det['id'] for i, det in enumerate(all_detections)}
        det_placeholders = ', '.join(f':did{i}' for i in range(len(all_detections)))
        conn.execute(
            f'DELETE FROM processing_jobs WHERE detection_id IN ({det_placeholders})',
            det_params,
        )
    conn.execute(f'DELETE FROM detections WHERE image_id IN ({img_placeholders})', img_params)
    conn.execute(f'DELETE FROM images WHERE id IN ({img_placeholders})', img_params)
    conn.commit()

    # delete files by type, tracking hits and misses
    summary = CleanSummary(detections=len(all_detections), images=len(image_ids))

    def _delete(path: Path) -> bool:
        """Delete a file and return True if it existed, False if it was missing."""
        if path.exists():
            path.unlink()
            return True
        logger.warning(f'expected file not found on disk: {path}')
        summary.files_missing += 1
        return False

    for det in all_detections:
        if det['crop_path']:
            if _delete(data_root / det['crop_path']):
                summary.crops_deleted += 1

    for target in targets:
        if target.thumb_path:
            if _delete(data_root / target.thumb_path):
                summary.thumbnails_deleted += 1
        if _delete(data_root / target.image_path):
            summary.raw_images_deleted += 1

    return summary
