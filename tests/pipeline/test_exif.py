"""Tests for crittercam.pipeline.exif."""

from datetime import datetime
from pathlib import Path

from crittercam.pipeline.exif import ImageMetadata, read_exif

BROWNING_IMAGE = Path(__file__).parent / 'assets' / 'BROWNING.JPG'


class TestReadExifBrowningImage:
    """Test read_exif against a real Browning trail cam image."""

    def test_captured_at_is_parsed(self):
        metadata = read_exif(BROWNING_IMAGE)
        assert isinstance(metadata.captured_at, datetime)

    def test_captured_at_value(self):
        metadata = read_exif(BROWNING_IMAGE)
        assert metadata.captured_at == datetime(2026, 3, 28, 13, 6, 8)

    def test_dimensions_are_present(self):
        metadata = read_exif(BROWNING_IMAGE)
        assert metadata.width == 4608
        assert metadata.height == 2592

    def test_camera_make(self):
        metadata = read_exif(BROWNING_IMAGE)
        assert metadata.camera_make == 'BROWNING'

    def test_camera_model(self):
        metadata = read_exif(BROWNING_IMAGE)
        assert metadata.camera_model == 'BTC-8EHP5U'

    def test_temperature_is_parsed(self):
        metadata = read_exif(BROWNING_IMAGE)
        assert metadata.temperature_c == 19.0


class TestReadExifNoExif:
    """Test read_exif on an image with no EXIF data."""

    def test_returns_all_none(self, tmp_path, make_jpeg):
        # Arrange
        path = make_jpeg(tmp_path / 'no_exif.jpg')

        # Act
        metadata = read_exif(path)

        # Assert
        assert metadata == ImageMetadata(
            captured_at=None,
            width=None,
            height=None,
            camera_make=None,
            camera_model=None,
            temperature_c=None,
        )


class TestReadExifMissingFile:
    """Test read_exif on a missing file."""

    def test_returns_all_none(self, tmp_path):
        # Arrange
        path = tmp_path / 'nonexistent.jpg'

        # Act
        metadata = read_exif(path)

        # Assert
        assert metadata == ImageMetadata(
            captured_at=None,
            width=None,
            height=None,
            camera_make=None,
            camera_model=None,
            temperature_c=None,
        )


class TestParseTemperature:
    """Test temperature parsing from UserComment strings."""

    def test_integer_temperature(self):
        from crittercam.pipeline.exif import _parse_temperature
        assert _parse_temperature(b'\x00\x00\x00\x00C[P] T[23C] S[1]') == 23.0

    def test_temperature_not_present(self):
        from crittercam.pipeline.exif import _parse_temperature
        assert _parse_temperature(b'\x00\x00\x00\x00C[P] S[1]') is None

    def test_none_input(self):
        from crittercam.pipeline.exif import _parse_temperature
        assert _parse_temperature(None) is None

    def test_string_input(self):
        from crittercam.pipeline.exif import _parse_temperature
        assert _parse_temperature('T[5C]') == 5.0
