"""EXIF metadata extraction from trail cam images."""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS

logger = logging.getLogger(__name__)

# Browning cameras encode ambient temperature in UserComment as e.g. T[23C]
_TEMPERATURE_RE = re.compile(r'T\[(\d+(?:\.\d+)?)C\]')

# EXIF tag IDs
_TAG_IDS = {name: tag_id for tag_id, name in TAGS.items()}
_TAG_DATETIME_ORIGINAL = _TAG_IDS['DateTimeOriginal']
_TAG_IMAGE_WIDTH = _TAG_IDS['ExifImageWidth']
_TAG_IMAGE_HEIGHT = _TAG_IDS['ExifImageHeight']
_TAG_MAKE = _TAG_IDS['Make']
_TAG_MODEL = _TAG_IDS['Model']
_TAG_USER_COMMENT = _TAG_IDS['UserComment']

_EXIF_DATETIME_FORMAT = '%Y:%m:%d %H:%M:%S'


@dataclass
class ImageMetadata:
    """EXIF metadata extracted from a single image.

    Attributes:
        captured_at: timestamp the shutter fired, from DateTimeOriginal; None if absent
        width: image width in pixels; None if absent
        height: image height in pixels; None if absent
        camera_make: camera manufacturer from EXIF Make; None if absent
        camera_model: camera model from EXIF Model; None if absent
        temperature_c: ambient temperature in Celsius parsed from UserComment; None if absent
    """

    captured_at: datetime | None
    width: int | None
    height: int | None
    camera_make: str | None
    camera_model: str | None
    temperature_c: float | None


def read_exif(image_path: Path) -> ImageMetadata:
    """Extract metadata from a JPEG image's EXIF data.

    Fields that are missing or unparseable are returned as None rather than
    raising an exception, so ingestion can proceed with partial metadata.

    Args:
        image_path: path to a JPEG image file

    Returns:
        ImageMetadata with fields populated where available
    """
    try:
        with Image.open(image_path) as img:
            raw = img._getexif() or {}
    except Exception:
        logger.warning('could not read EXIF from %s', image_path)
        return ImageMetadata(
            captured_at=None,
            width=None,
            height=None,
            camera_make=None,
            camera_model=None,
            temperature_c=None,
        )

    return ImageMetadata(
        captured_at=_parse_datetime(raw.get(_TAG_DATETIME_ORIGINAL)),
        width=raw.get(_TAG_IMAGE_WIDTH),
        height=raw.get(_TAG_IMAGE_HEIGHT),
        camera_make=_clean_str(raw.get(_TAG_MAKE)),
        camera_model=_clean_str(raw.get(_TAG_MODEL)),
        temperature_c=_parse_temperature(raw.get(_TAG_USER_COMMENT)),
    )


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse an EXIF datetime string into a datetime object.

    Args:
        value: EXIF datetime string in 'YYYY:MM:DD HH:MM:SS' format, or None

    Returns:
        datetime object, or None if value is absent or unparseable
    """
    if not value:
        return None
    try:
        return datetime.strptime(value, _EXIF_DATETIME_FORMAT)
    except ValueError:
        logger.warning('unparseable EXIF datetime: %r', value)
        return None


def _parse_temperature(user_comment: bytes | str | None) -> float | None:
    """Parse ambient temperature from a Browning camera UserComment field.

    Browning cameras encode temperature as T[<value>C] within the UserComment
    binary blob, e.g. b'\\x00...T[23C]...'.

    Args:
        user_comment: raw UserComment EXIF value, or None

    Returns:
        temperature in Celsius as a float, or None if not found
    """
    if not user_comment:
        return None
    if isinstance(user_comment, bytes):
        try:
            text = user_comment.decode('latin-1')
        except Exception:
            return None
    else:
        text = user_comment
    match = _TEMPERATURE_RE.search(text)
    if match:
        return float(match.group(1))
    return None


def _clean_str(value: str | None) -> str | None:
    """Strip whitespace and return None for empty strings.

    Args:
        value: raw string value from EXIF, or None

    Returns:
        stripped string, or None if absent or blank
    """
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None
