"""Tests for crittercam.cli.cmd_ingest."""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crittercam.cli.cmd_ingest import cmd_ingest
from crittercam.config import Config
from crittercam.pipeline.ingest import IngestSummary


def _args(source, data_root=None):
    """Build a minimal Namespace for cmd_ingest."""
    return argparse.Namespace(source=Path(source), data_root=data_root)


class TestCmdIngest:
    """Test the cmd_ingest command handler."""

    def test_exits_when_source_does_not_exist(self, tmp_path, monkeypatch):
        # Arrange
        config_path = tmp_path / 'config.toml'
        monkeypatch.setattr('crittercam.cli.cmd_ingest.CONFIG_PATH', config_path)
        args = _args(source=tmp_path / 'nonexistent', data_root=tmp_path / 'data')

        # Act / Assert
        with pytest.raises(SystemExit) as exc_info:
            cmd_ingest(args)
        assert exc_info.value.code == 1

    def test_exits_when_no_config_and_no_data_root(self, tmp_path, monkeypatch):
        # Arrange — config file does not exist
        monkeypatch.setattr('crittercam.cli.cmd_ingest.CONFIG_PATH', tmp_path / 'missing.toml')
        args = _args(source=tmp_path, data_root=None)

        # Act / Assert
        with pytest.raises(SystemExit) as exc_info:
            cmd_ingest(args)
        assert exc_info.value.code == 1

    def test_uses_data_root_override(self, tmp_path, monkeypatch):
        # Arrange
        source = tmp_path / 'source'
        source.mkdir()
        data_root = tmp_path / 'data'
        args = _args(source=source, data_root=data_root)

        mock_summary = IngestSummary(ingested=0, skipped=0)
        with patch('crittercam.cli.cmd_ingest.connect') as mock_connect, \
                patch('crittercam.cli.cmd_ingest.ingest', return_value=mock_summary):
            mock_connect.return_value.__enter__ = MagicMock()
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)

            # Act
            cmd_ingest(args)

        # Assert — did not try to load config (would have raised)

    def test_prints_summary(self, tmp_path, capsys, monkeypatch):
        # Arrange
        source = tmp_path / 'source'
        source.mkdir()
        data_root = tmp_path / 'data'
        args = _args(source=source, data_root=data_root)

        mock_summary = IngestSummary(ingested=3, skipped=1)
        with patch('crittercam.cli.cmd_ingest.connect') as mock_connect, \
                patch('crittercam.cli.cmd_ingest.ingest', return_value=mock_summary):
            mock_connect.return_value.__enter__ = MagicMock()
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)
            cmd_ingest(args)

        out = capsys.readouterr().out
        assert '3 ingested' in out
        assert '1 skipped' in out

    def test_prints_errors(self, tmp_path, capsys, monkeypatch):
        # Arrange
        source = tmp_path / 'source'
        source.mkdir()
        args = _args(source=source, data_root=tmp_path / 'data')

        mock_summary = IngestSummary(ingested=0, skipped=0, errors={'bad.jpg': 'read error'})
        with patch('crittercam.cli.cmd_ingest.connect') as mock_connect, \
                patch('crittercam.cli.cmd_ingest.ingest', return_value=mock_summary):
            mock_connect.return_value.__enter__ = MagicMock()
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)
            cmd_ingest(args)

        out = capsys.readouterr().out
        assert 'bad.jpg' in out
        assert 'read error' in out
