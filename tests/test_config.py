"""Tests for crittercam.config."""

from pathlib import Path

import pytest

from crittercam.config import Config, load, save


class TestConfig:
    """Test the Config dataclass."""

    def test_db_path_is_under_data_root(self, tmp_path):
        # Arrange
        config = Config(data_root=tmp_path)

        # Act / Assert
        assert config.db_path == tmp_path / 'db' / 'crittercam.db'


class TestSave:
    """Test the save function."""

    def test_writes_config_file(self, tmp_path):
        # Arrange
        config = Config(data_root=Path('/data/wildlife'))
        config_path = tmp_path / 'config.toml'

        # Act
        save(config, config_path)

        # Assert
        assert config_path.exists()

    def test_creates_parent_directories(self, tmp_path):
        # Arrange
        config = Config(data_root=Path('/data/wildlife'))
        config_path = tmp_path / 'nested' / 'dir' / 'config.toml'

        # Act
        save(config, config_path)

        # Assert
        assert config_path.exists()

    def test_written_content_is_readable(self, tmp_path):
        # Arrange
        config = Config(data_root=Path('/data/wildlife'))
        config_path = tmp_path / 'config.toml'

        # Act
        save(config, config_path)
        loaded = load(config_path)

        # Assert
        assert loaded.data_root == Path('/data/wildlife')

    def test_saves_country_and_admin1_region(self, tmp_path):
        # Arrange
        config = Config(data_root=Path('/data/wildlife'), country='USA', admin1_region='CT')
        config_path = tmp_path / 'config.toml'

        # Act
        save(config, config_path)
        loaded = load(config_path)

        # Assert
        assert loaded.country == 'USA'
        assert loaded.admin1_region == 'CT'

    def test_omits_country_when_none(self, tmp_path):
        # Arrange
        config = Config(data_root=Path('/data/wildlife'))
        config_path = tmp_path / 'config.toml'

        # Act
        save(config, config_path)

        # Assert — file should not contain 'country' key
        assert 'country' not in config_path.read_text()


class TestLoad:
    """Test the load function."""

    def test_raises_when_file_missing(self, tmp_path):
        # Arrange
        config_path = tmp_path / 'config.toml'

        # Act / Assert
        with pytest.raises(FileNotFoundError):
            load(config_path)

    def test_loads_data_root(self, tmp_path):
        # Arrange
        config_path = tmp_path / 'config.toml'
        save(Config(data_root=Path('/data/wildlife')), config_path)

        # Act
        config = load(config_path)

        # Assert
        assert config.data_root == Path('/data/wildlife')

    def test_data_root_is_path_not_string(self, tmp_path):
        # Arrange
        config_path = tmp_path / 'config.toml'
        save(Config(data_root=Path('/data/wildlife')), config_path)

        # Act
        config = load(config_path)

        # Assert
        assert isinstance(config.data_root, Path)

    def test_country_defaults_to_none_when_absent(self, tmp_path):
        # Arrange — config written without country field
        config_path = tmp_path / 'config.toml'
        save(Config(data_root=Path('/data/wildlife')), config_path)

        # Act
        config = load(config_path)

        # Assert
        assert config.country is None
        assert config.admin1_region is None
