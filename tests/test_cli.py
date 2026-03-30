"""Tests for crittercam.cli."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from crittercam.config import Config, load
from crittercam.cli import cmd_setup


class TestCmdSetup:
    """Test the cmd_setup function."""

    def test_writes_config_and_creates_database(self, tmp_path, monkeypatch):
        # Arrange
        config_path = tmp_path / 'config.toml'
        data_root = tmp_path / 'data'
        monkeypatch.setattr('crittercam.cli.CONFIG_PATH', config_path)
        monkeypatch.setattr('crittercam.config.CONFIG_PATH', config_path)

        # Act — provide data_root then skip country
        with patch('builtins.input', side_effect=[str(data_root), '']):
            cmd_setup()

        # Assert — config written
        config = load(config_path)
        assert config.data_root == data_root

        # Assert — database created with schema
        assert config.db_path.exists()

    def test_database_has_expected_tables(self, tmp_path, monkeypatch):
        # Arrange
        config_path = tmp_path / 'config.toml'
        data_root = tmp_path / 'data'
        monkeypatch.setattr('crittercam.cli.CONFIG_PATH', config_path)
        monkeypatch.setattr('crittercam.config.CONFIG_PATH', config_path)

        # Act
        with patch('builtins.input', side_effect=[str(data_root), '']):
            cmd_setup()

        # Assert
        from crittercam.pipeline.db import connect
        conn = connect(load(config_path).db_path)
        tables = {
            row['name']
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {'images', 'detections', 'processing_jobs'}.issubset(tables)
        conn.close()

    def test_saves_country_and_admin1_region(self, tmp_path, monkeypatch):
        # Arrange
        config_path = tmp_path / 'config.toml'
        data_root = tmp_path / 'data'
        monkeypatch.setattr('crittercam.cli.CONFIG_PATH', config_path)
        monkeypatch.setattr('crittercam.config.CONFIG_PATH', config_path)

        # Act — provide data_root, country, admin1_region
        with patch('builtins.input', side_effect=[str(data_root), 'USA', 'CT']):
            cmd_setup()

        # Assert
        config = load(config_path)
        assert config.country == 'USA'
        assert config.admin1_region == 'CT'

    def test_invalid_country_reprompts(self, tmp_path, monkeypatch):
        # Arrange
        config_path = tmp_path / 'config.toml'
        data_root = tmp_path / 'data'
        monkeypatch.setattr('crittercam.cli.CONFIG_PATH', config_path)
        monkeypatch.setattr('crittercam.config.CONFIG_PATH', config_path)

        # Act — bad country first, then valid, then skip admin1
        with patch('builtins.input', side_effect=[str(data_root), 'XX', 'USA', '']):
            cmd_setup()

        # Assert — ended up with the valid code
        assert load(config_path).country == 'USA'

    def test_prompts_to_overwrite_when_config_exists(self, tmp_path, monkeypatch):
        # Arrange — write an existing config
        config_path = tmp_path / 'config.toml'
        data_root = tmp_path / 'data'
        monkeypatch.setattr('crittercam.cli.CONFIG_PATH', config_path)
        monkeypatch.setattr('crittercam.config.CONFIG_PATH', config_path)
        with patch('builtins.input', side_effect=[str(data_root), '']):
            cmd_setup()

        # Act — run setup again, decline overwrite
        with patch('builtins.input', return_value='n'):
            with pytest.raises(SystemExit) as exc_info:
                cmd_setup()

        # Assert — exited cleanly without overwriting
        assert exc_info.value.code == 0
        assert load(config_path).data_root == data_root

    def test_overwrites_config_when_confirmed(self, tmp_path, monkeypatch):
        # Arrange — write an existing config
        config_path = tmp_path / 'config.toml'
        data_root_old = tmp_path / 'old'
        data_root_new = tmp_path / 'new'
        monkeypatch.setattr('crittercam.cli.CONFIG_PATH', config_path)
        monkeypatch.setattr('crittercam.config.CONFIG_PATH', config_path)
        with patch('builtins.input', side_effect=[str(data_root_old), '']):
            cmd_setup()

        # Act — confirm overwrite, new data root, skip country
        with patch('builtins.input', side_effect=['y', str(data_root_new), '']):
            cmd_setup()

        # Assert
        assert load(config_path).data_root == data_root_new

    def test_exits_on_empty_data_root(self, tmp_path, monkeypatch):
        # Arrange
        config_path = tmp_path / 'config.toml'
        monkeypatch.setattr('crittercam.cli.CONFIG_PATH', config_path)
        monkeypatch.setattr('crittercam.config.CONFIG_PATH', config_path)

        # Act / Assert — empty data root triggers sys.exit(1) before country prompt
        with patch('builtins.input', return_value=''):
            with pytest.raises(SystemExit) as exc_info:
                cmd_setup()
        assert exc_info.value.code == 1
