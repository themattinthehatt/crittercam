"""Phase 1 ingestion: copy new images from source into the archive."""

import hashlib
import logging
import shutil
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from crittercam.pipeline.exif import read_exif

logger = logging.getLogger(__name__)

_JPEG_SUFFIXES = {'.jpg', '.jpeg'}
_THUMBNAIL_MAX_SIZE = 320


@dataclass
class IngestSummary:
    """Summary of a completed ingestion run.

    Attributes:
        ingested: number of new images copied and recorded
        skipped: number of images already present in the archive (by hash)
        errors: filenames that could not be ingested, with reasons
    """

    ingested: int = 0
    skipped: int = 0
    errors: dict[str, str] = field(default_factory=dict)


def ingest(
    source_dir: Path,
    data_root: Path,
    conn: sqlite3.Connection,
) -> IngestSummary:
    """Ingest new images from source_dir into the archive.

    Walks source_dir recursively, hashes each JPEG, skips any already present
    in the database, and copies new files into data_root/images/YYYY/MM/DD/.
    All database writes are committed in a single bulk transaction.

    Args:
        source_dir: directory containing images to ingest (e.g. SD card)
        data_root: root of the crittercam data directory
        conn: open database connection

    Returns:
        IngestSummary with counts of ingested, skipped, and errored files
    """
    summary = IngestSummary()
    jpegs = _find_jpegs(source_dir)

    if not jpegs:
        logger.info('no JPEG files found in %s', source_dir)
        return summary

    existing_hashes = _load_existing_hashes(conn)
    rows_images = []
    rows_jobs = []

    for path in jpegs:
        try:
            file_hash = _hash_file(path)
        except OSError as exc:
            logger.error('could not read %s: %s', path, exc)
            summary.errors[path.name] = str(exc)
            continue

        if file_hash in existing_hashes:
            logger.debug('skipping %s (already ingested)', path.name)
            summary.skipped += 1
            continue

        metadata = read_exif(path)
        date = _capture_date(metadata, path)
        dest_rel = Path('images') / f'{date.year:04d}' / f'{date.month:02d}' / f'{date.day:02d}' / path.name
        dest_abs = data_root / dest_rel

        if dest_abs.exists():
            msg = f'destination already exists: {dest_rel}'
            logger.error('%s — skipping %s', msg, path.name)
            summary.errors[path.name] = msg
            continue

        dest_abs.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest_abs)
        logger.info('copied %s → %s', path.name, dest_rel)

        thumb_rel = _generate_thumbnail(dest_abs, dest_rel, data_root)

        now = datetime.now(timezone.utc).isoformat(timespec='seconds')
        rows_images.append({
            'path': dest_rel.as_posix(),
            'filename': path.name,
            'captured_at': metadata.captured_at.isoformat() if metadata.captured_at else None,
            'ingested_at': now,
            'file_hash': file_hash,
            'file_size': path.stat().st_size,
            'width': metadata.width,
            'height': metadata.height,
            'camera_make': metadata.camera_make,
            'camera_model': metadata.camera_model,
            'temperature_c': metadata.temperature_c,
            'thumb_path': thumb_rel.as_posix() if thumb_rel else None,
        })

    if not rows_images:
        return summary

    conn.execute('PRAGMA synchronous = OFF')
    conn.execute('PRAGMA journal_mode = MEMORY')

    try:
        with conn:
            image_ids = []
            for row in rows_images:
                cursor = conn.execute(
                    '''
                    INSERT INTO images (
                        path, filename, captured_at, ingested_at, file_hash,
                        file_size, width, height, camera_make, camera_model,
                        temperature_c, thumb_path
                    ) VALUES (
                        :path, :filename, :captured_at, :ingested_at, :file_hash,
                        :file_size, :width, :height, :camera_make, :camera_model,
                        :temperature_c, :thumb_path
                    )
                    ''',
                    row,
                )
                image_ids.append(cursor.lastrowid)
                summary.ingested += 1

            conn.executemany(
                '''
                INSERT INTO processing_jobs (image_id, job_type, status)
                VALUES (?, 'detection', 'pending')
                ''',
                [(image_id,) for image_id in image_ids],
            )
    finally:
        conn.execute('PRAGMA synchronous = FULL')
        conn.execute('PRAGMA journal_mode = WAL')

    logger.info(
        'ingestion complete: %d ingested, %d skipped, %d errors',
        summary.ingested,
        summary.skipped,
        len(summary.errors),
    )
    return summary


def _find_jpegs(source_dir: Path) -> list[Path]:
    """Recursively find all JPEG files in a directory.

    Args:
        source_dir: directory to search

    Returns:
        sorted list of JPEG file paths
    """
    return sorted(
        p for p in source_dir.rglob('*')
        if p.is_file() and p.suffix.lower() in _JPEG_SUFFIXES
    )


def _hash_file(path: Path) -> str:
    """Compute the SHA-256 hash of a file.

    Args:
        path: file to hash

    Returns:
        hex digest string
    """
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def _load_existing_hashes(conn: sqlite3.Connection) -> set[str]:
    """Load all file hashes currently in the images table.

    Args:
        conn: open database connection

    Returns:
        set of SHA-256 hex digest strings
    """
    rows = conn.execute('SELECT file_hash FROM images').fetchall()
    return {row['file_hash'] for row in rows}


def _generate_thumbnail(image_abs: Path, image_rel: Path, data_root: Path) -> Path | None:
    """Generate a thumbnail for a newly ingested image.

    Writes the thumbnail under data_root/derived/ mirroring the image path,
    e.g. derived/YYYY/MM/DD/<stem>_thumb.jpg.

    Args:
        image_abs: absolute path to the source image
        image_rel: path relative to data_root (e.g. images/YYYY/MM/DD/file.jpg)
        data_root: root of the crittercam data directory

    Returns:
        path to the thumbnail relative to data_root, or None on failure
    """
    try:
        date_part = image_rel.parent.relative_to('images')
        derived_dir = data_root / 'derived' / date_part
        derived_dir.mkdir(parents=True, exist_ok=True)
        thumb_abs = derived_dir / f'{image_rel.stem}_thumb.jpg'
        img = Image.open(image_abs).convert('RGB')
        img.thumbnail((_THUMBNAIL_MAX_SIZE, _THUMBNAIL_MAX_SIZE), Image.LANCZOS)
        img.save(thumb_abs, format='JPEG', quality=85)
        return thumb_abs.relative_to(data_root)
    except Exception as exc:
        logger.warning('thumbnail generation failed for %s: %s', image_abs.name, exc)
        return None


def _capture_date(metadata, path: Path) -> datetime:
    """Return the capture date for path organisation.

    Uses EXIF DateTimeOriginal if available, falling back to file mtime.

    Args:
        metadata: ImageMetadata extracted from the file
        path: path to the image file (used for mtime fallback)

    Returns:
        datetime to use for YYYY/MM/DD directory placement
    """
    if metadata.captured_at:
        return metadata.captured_at
    logger.warning('no EXIF timestamp for %s, falling back to file mtime', path.name)
    return datetime.fromtimestamp(path.stat().st_mtime)
