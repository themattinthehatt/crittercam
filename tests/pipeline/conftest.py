"""Shared pytest fixtures."""

from pathlib import Path

import pytest
from PIL import Image

from crittercam.pipeline.db import connect, migrate


@pytest.fixture
def make_jpeg():
    """Return a factory that writes a minimal JPEG to a given path.

    The factory signature is:
        make_jpeg(path, size=(64, 64), exif_bytes=None) -> Path

    Args (of the returned factory):
        path: destination file path; parent directories are created if needed
        size: image dimensions in pixels
        exif_bytes: raw EXIF bytes to embed, or None for no EXIF

    Returns:
        the destination path
    """
    def factory(
        path: Path,
        size: tuple[int, int] = (64, 64),
        exif_bytes: bytes | None = None,
    ) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new('RGB', size, color=(128, 128, 128))
        if exif_bytes:
            img.save(path, format='JPEG', exif=exif_bytes)
        else:
            img.save(path, format='JPEG')
        return path

    return factory


@pytest.fixture
def db(tmp_path):
    """Open a migrated database connection for use in pipeline tests."""
    conn = connect(tmp_path / 'test.db')
    migrate(conn)
    yield conn
    conn.close()
