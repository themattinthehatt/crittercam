"""Tests for crittercam.pipeline.ingest."""

from datetime import datetime
from unittest.mock import patch

import pytest
from PIL import Image

from crittercam.pipeline.exif import ImageMetadata
from crittercam.pipeline.ingest import (
    _find_jpegs,
    _hash_file,
    ingest,
)


_DUMMY_METADATA = ImageMetadata(
    captured_at=datetime(2026, 3, 15, 9, 0, 0),
    width=64,
    height=64,
    camera_make='BROWNING',
    camera_model='BTC-8EHP5U',
    temperature_c=12.0,
)

_NO_TIMESTAMP_METADATA = ImageMetadata(
    captured_at=None,
    width=64,
    height=64,
    camera_make=None,
    camera_model=None,
    temperature_c=None,
)


class TestFindJpegs:
    """Test the _find_jpegs function."""

    def test_finds_jpg_files(self, tmp_path, make_jpeg):
        # Arrange
        make_jpeg(tmp_path / 'a.jpg')
        make_jpeg(tmp_path / 'b.JPG')

        # Act
        result = _find_jpegs(tmp_path)

        # Assert
        assert len(result) == 2

    def test_finds_jpegs_recursively(self, tmp_path, make_jpeg):
        # Arrange
        make_jpeg(tmp_path / 'sub' / 'a.jpg')

        # Act
        result = _find_jpegs(tmp_path)

        # Assert
        assert len(result) == 1

    def test_ignores_non_jpeg_files(self, tmp_path, make_jpeg):
        # Arrange
        (tmp_path / 'a.png').write_bytes(b'')
        (tmp_path / 'b.txt').write_bytes(b'')
        make_jpeg(tmp_path / 'c.jpg')

        # Act
        result = _find_jpegs(tmp_path)

        # Assert
        assert len(result) == 1

    def test_returns_empty_list_for_empty_directory(self, tmp_path):
        assert _find_jpegs(tmp_path) == []


class TestHashFile:
    """Test the _hash_file function."""

    def test_returns_hex_string(self, tmp_path):
        # Arrange
        path = tmp_path / 'f.jpg'
        path.write_bytes(b'hello')

        # Act
        result = _hash_file(path)

        # Assert
        assert isinstance(result, str)
        assert len(result) == 64

    def test_same_content_same_hash(self, tmp_path):
        # Arrange
        a = tmp_path / 'a.jpg'
        b = tmp_path / 'b.jpg'
        a.write_bytes(b'same')
        b.write_bytes(b'same')

        # Act / Assert
        assert _hash_file(a) == _hash_file(b)

    def test_different_content_different_hash(self, tmp_path):
        # Arrange
        a = tmp_path / 'a.jpg'
        b = tmp_path / 'b.jpg'
        a.write_bytes(b'aaa')
        b.write_bytes(b'bbb')

        # Act / Assert
        assert _hash_file(a) != _hash_file(b)


class TestIngest:
    """Test the ingest function."""

    def test_ingests_new_images(self, tmp_path, db, make_jpeg):
        # Arrange
        source = tmp_path / 'source'
        data_root = tmp_path / 'data'
        make_jpeg(source / 'IMG_001.jpg')

        # Act
        with patch('crittercam.pipeline.ingest.read_exif', return_value=_DUMMY_METADATA):
            summary = ingest(source, data_root, db)

        # Assert
        assert summary.ingested == 1
        assert summary.skipped == 0
        assert summary.errors == {}

    def test_image_row_written_to_db(self, tmp_path, db, make_jpeg):
        # Arrange
        source = tmp_path / 'source'
        data_root = tmp_path / 'data'
        make_jpeg(source / 'IMG_001.jpg')

        # Act
        with patch('crittercam.pipeline.ingest.read_exif', return_value=_DUMMY_METADATA):
            ingest(source, data_root, db)

        # Assert
        row = db.execute('SELECT * FROM images').fetchone()
        assert row['filename'] == 'IMG_001.jpg'
        assert row['camera_make'] == 'BROWNING'
        assert row['temperature_c'] == 12.0

    def test_file_copied_to_correct_destination(self, tmp_path, db, make_jpeg):
        # Arrange
        source = tmp_path / 'source'
        data_root = tmp_path / 'data'
        make_jpeg(source / 'IMG_001.jpg')

        # Act
        with patch('crittercam.pipeline.ingest.read_exif', return_value=_DUMMY_METADATA):
            ingest(source, data_root, db)

        # Assert
        expected = data_root / 'images' / '2026' / '03' / '15' / 'IMG_001.jpg'
        assert expected.exists()

    def test_processing_job_created(self, tmp_path, db, make_jpeg):
        # Arrange
        source = tmp_path / 'source'
        data_root = tmp_path / 'data'
        make_jpeg(source / 'IMG_001.jpg')

        # Act
        with patch('crittercam.pipeline.ingest.read_exif', return_value=_DUMMY_METADATA):
            ingest(source, data_root, db)

        # Assert
        job = db.execute('SELECT * FROM processing_jobs').fetchone()
        assert job['job_type'] == 'detection'
        assert job['status'] == 'pending'

    def test_duplicate_skipped_on_rerun(self, tmp_path, db, make_jpeg):
        # Arrange
        source = tmp_path / 'source'
        data_root = tmp_path / 'data'
        make_jpeg(source / 'IMG_001.jpg')

        # Act — ingest twice
        with patch('crittercam.pipeline.ingest.read_exif', return_value=_DUMMY_METADATA):
            ingest(source, data_root, db)
            summary = ingest(source, data_root, db)

        # Assert — second run skips the duplicate
        assert summary.ingested == 0
        assert summary.skipped == 1
        assert db.execute('SELECT COUNT(*) FROM images').fetchone()[0] == 1

    def test_mtime_fallback_when_no_exif_timestamp(self, tmp_path, db, make_jpeg):
        # Arrange
        source = tmp_path / 'source'
        data_root = tmp_path / 'data'
        make_jpeg(source / 'IMG_001.jpg')

        # Act
        with patch('crittercam.pipeline.ingest.read_exif', return_value=_NO_TIMESTAMP_METADATA):
            summary = ingest(source, data_root, db)

        # Assert — file was ingested (mtime used for path, not errored)
        assert summary.ingested == 1
        assert summary.errors == {}

    def test_destination_collision_recorded_as_error(self, tmp_path, db, make_jpeg):
        # Arrange — two source files with the same name and same capture date
        source_a = tmp_path / 'source_a'
        source_b = tmp_path / 'source_b'
        data_root = tmp_path / 'data'
        make_jpeg(source_a / 'IMG_001.jpg')
        # source_b has different content (different hash) but same filename + date
        source_b.mkdir(parents=True, exist_ok=True)
        Image.new('RGB', (64, 64), color=(255, 0, 0)).save(
            source_b / 'IMG_001.jpg', format='JPEG',
        )

        # Act — ingest source_a first, then source_b
        with patch('crittercam.pipeline.ingest.read_exif', return_value=_DUMMY_METADATA):
            ingest(source_a, data_root, db)
            summary = ingest(source_b, data_root, db)

        # Assert — collision detected, not silently overwritten
        assert 'IMG_001.jpg' in summary.errors
        assert db.execute('SELECT COUNT(*) FROM images').fetchone()[0] == 1

    def test_empty_source_directory(self, tmp_path, db):
        # Arrange
        source = tmp_path / 'source'
        source.mkdir()
        data_root = tmp_path / 'data'

        # Act
        summary = ingest(source, data_root, db)

        # Assert
        assert summary.ingested == 0
        assert summary.skipped == 0
        assert summary.errors == {}
