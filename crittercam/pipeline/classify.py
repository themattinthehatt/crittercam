"""Phase 2 classification: run classifier on pending detection jobs and generate derived assets."""

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from crittercam.classifier.base import Classifier, Detection

logger = logging.getLogger(__name__)

_THUMBNAIL_MAX_SIZE = 320


@dataclass
class ClassifySummary:
    """Summary of a classify run.

    Attributes:
        classified: number of images successfully classified
        errors: mapping of filename to error message for failed images
    """

    classified: int = 0
    errors: dict[str, str] = field(default_factory=dict)


def reset_errors(conn: sqlite3.Connection) -> int:
    """Reset all errored detection jobs back to pending so they will be retried.

    Args:
        conn: open database connection

    Returns:
        number of jobs reset
    """
    cursor = conn.execute(
        "UPDATE processing_jobs SET status = 'pending', started_at = NULL, "
        "completed_at = NULL, error_msg = NULL "
        "WHERE job_type = 'detection' AND status = 'error'"
    )
    conn.commit()
    return cursor.rowcount


def reset_all(conn: sqlite3.Connection) -> int:
    """Reset all detection jobs (done and error) back to pending for a full rerun.

    Args:
        conn: open database connection

    Returns:
        number of jobs reset
    """
    cursor = conn.execute(
        "UPDATE processing_jobs SET status = 'pending', started_at = NULL, "
        "completed_at = NULL, error_msg = NULL "
        "WHERE job_type = 'detection' AND status IN ('done', 'error')"
    )
    conn.commit()
    return cursor.rowcount


def classify_pending(
    data_root: Path,
    conn: sqlite3.Connection,
    classifier: Classifier,
    crop_padding: float = 0.15,
) -> ClassifySummary:
    """Run classifier on all pending detection jobs and write results to the database.

    For each pending job: runs the classifier, deactivates any prior active detection
    rows for that image, inserts a new detection row, generates a thumbnail and crop
    (if a bbox is present), and marks the job done. On failure, marks the job as error.

    Idempotent: jobs already in 'done' or 'error' state are not reprocessed.

    Args:
        data_root: root directory for the image archive and derived assets
        conn: open database connection
        classifier: classifier implementing the Classifier protocol
        crop_padding: fractional padding added to each side of the detection bbox
            when generating crops, as a proportion of the bbox dimension;
            clamped to image boundary

    Returns:
        ClassifySummary with counts and per-file error details
    """
    summary = ClassifySummary()

    pending = conn.execute(
        '''
        SELECT pj.id AS job_id, pj.image_id, i.path, i.filename
        FROM processing_jobs pj
        JOIN images i ON i.id = pj.image_id
        WHERE pj.job_type = 'detection' AND pj.status = 'pending'
        ORDER BY pj.id
        '''
    ).fetchall()

    for job in pending:
        job_id = job['job_id']
        image_id = job['image_id']
        image_path = data_root / job['path']
        filename = job['filename']

        _mark_job(conn, job_id, status='running', started_at=_now())
        conn.commit()

        try:
            detections = classifier.classify(image_path)
            thumb_rel, crop_rel = _generate_derived_assets(
                image_path=image_path,
                image_rel_path=Path(job['path']),
                data_root=data_root,
                detection=detections[0] if detections else None,
                crop_padding=crop_padding,
            )
        except Exception as exc:
            msg = str(exc)
            logger.error('classify failed on %s: %s', filename, msg)
            _mark_job(conn, job_id, 'error', completed_at=_now(), error_msg=msg)
            conn.commit()
            summary.errors[filename] = msg
            continue

        now = _now()

        conn.execute(
            'UPDATE detections SET is_active = 0 WHERE image_id = :image_id AND is_active = 1',
            {'image_id': image_id},
        )

        if thumb_rel is not None:
            conn.execute(
                'UPDATE images SET thumb_path = :thumb_path WHERE id = :image_id',
                {'thumb_path': str(thumb_rel), 'image_id': image_id},
            )

        if detections:
            det = detections[0]
            bbox = det.bbox
            conn.execute(
                '''
                INSERT INTO detections
                    (image_id, label, confidence,
                     bbox_x, bbox_y, bbox_w, bbox_h,
                     crop_path, model_name, model_version, is_active, created_at)
                VALUES (:image_id, :label, :confidence,
                        :bbox_x, :bbox_y, :bbox_w, :bbox_h,
                        :crop_path, :model_name, :model_version, 1, :created_at)
                ''',
                {
                    'image_id': image_id,
                    'label': det.label,
                    'confidence': det.confidence,
                    'bbox_x': bbox[0] if bbox else None,
                    'bbox_y': bbox[1] if bbox else None,
                    'bbox_w': bbox[2] if bbox else None,
                    'bbox_h': bbox[3] if bbox else None,
                    'crop_path': str(crop_rel) if crop_rel else None,
                    'model_name': classifier.model_name,
                    'model_version': classifier.model_version,
                    'created_at': now,
                },
            )

        _mark_job(conn, job_id, 'done', completed_at=now)
        conn.commit()

        summary.classified += 1
        label = detections[0].label if detections else 'no prediction'
        logger.info('classified %s: %s', filename, label)

    return summary


def _generate_derived_assets(
    image_path: Path,
    image_rel_path: Path,
    data_root: Path,
    detection: Detection | None,
    crop_padding: float,
) -> tuple[Path | None, Path | None]:
    """Generate thumbnail and detection crop for an image.

    Args:
        image_path: absolute path to the source image
        image_rel_path: path relative to data_root (e.g. images/2026/03/15/IMG_001.jpg)
        data_root: root directory; derived assets are written under data_root/derived/
        detection: Detection object with bbox for crop generation, or None
        crop_padding: fractional bbox padding for crops

    Returns:
        tuple of (thumb_path_rel, crop_path_rel) relative to data_root;
        crop_path_rel is None when detection has no bbox
    """
    date_part = image_rel_path.parent.relative_to('images')
    stem = image_rel_path.stem
    derived_dir = data_root / 'derived' / date_part
    derived_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(image_path)
    img_w, img_h = img.size

    thumb_abs = derived_dir / f'{stem}_thumb.jpg'
    thumb = img.copy()
    thumb.thumbnail((_THUMBNAIL_MAX_SIZE, _THUMBNAIL_MAX_SIZE), Image.LANCZOS)
    thumb.save(thumb_abs, format='JPEG', quality=85)
    thumb_rel = thumb_abs.relative_to(data_root)

    crop_rel = None
    if detection is not None and detection.bbox is not None:
        x, y, w, h = detection.bbox
        pad_x = w * crop_padding
        pad_y = h * crop_padding
        x1 = max(0.0, x - pad_x) * img_w
        y1 = max(0.0, y - pad_y) * img_h
        x2 = min(1.0, x + w + pad_x) * img_w
        y2 = min(1.0, y + h + pad_y) * img_h
        crop = img.crop((x1, y1, x2, y2))
        crop_abs = derived_dir / f'{stem}_det001.jpg'
        crop.save(crop_abs, format='JPEG', quality=85)
        crop_rel = crop_abs.relative_to(data_root)

    return thumb_rel, crop_rel


def _now() -> str:
    """Return current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _mark_job(
    conn: sqlite3.Connection,
    job_id: int,
    status: str,
    started_at: str | None = None,
    completed_at: str | None = None,
    error_msg: str | None = None,
) -> None:
    """Update a processing_job row's status and timestamps.

    Args:
        conn: open database connection
        job_id: primary key of the job row
        status: new status value ('running', 'done', 'error')
        started_at: ISO 8601 timestamp to set, or None to leave unchanged
        completed_at: ISO 8601 timestamp to set, or None to leave unchanged
        error_msg: error message to set, or None to leave unchanged
    """
    conn.execute(
        '''
        UPDATE processing_jobs
        SET status       = :status,
            started_at   = COALESCE(:started_at, started_at),
            completed_at = COALESCE(:completed_at, completed_at),
            error_msg    = COALESCE(:error_msg, error_msg)
        WHERE id = :job_id
        ''',
        {'status': status, 'started_at': started_at, 'completed_at': completed_at,
         'error_msg': error_msg, 'job_id': job_id},
    )
