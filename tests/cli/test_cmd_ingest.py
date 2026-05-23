"""Tests for crittercam.cli.cmd_ingest."""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crittercam.cli.cmd_ingest import _resolve_deployment, cmd_ingest
from crittercam.pipeline.exif import ImageMetadata
from crittercam.pipeline.ingest import IngestSummary


def _args(source, data_root=None, deployment_id=None):
    """Build a minimal Namespace for cmd_ingest."""
    return argparse.Namespace(source=Path(source), data_root=data_root, deployment_id=deployment_id)


def _mock_conn(rows=None):
    """Return a MagicMock connection whose execute().fetchone() returns the given value."""
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = rows
    return conn


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
        args = _args(source=source, data_root=tmp_path / 'data', deployment_id=1)

        mock_summary = IngestSummary(ingested=0, skipped=0)
        with patch('crittercam.cli.cmd_ingest.connect') as mock_connect, \
                patch('crittercam.cli.cmd_ingest.ingest', return_value=mock_summary), \
                patch('crittercam.cli.cmd_ingest._resolve_deployment', return_value=1):
            mock_connect.return_value = _mock_conn({'id': 1})
            cmd_ingest(args)

        # Assert — did not try to load config (would have raised)

    def test_prints_summary(self, tmp_path, capsys):
        # Arrange
        source = tmp_path / 'source'
        source.mkdir()
        args = _args(source=source, data_root=tmp_path / 'data', deployment_id=1)

        mock_summary = IngestSummary(ingested=3, skipped=1)
        with patch('crittercam.cli.cmd_ingest.connect') as mock_connect, \
                patch('crittercam.cli.cmd_ingest.ingest', return_value=mock_summary), \
                patch('crittercam.cli.cmd_ingest._resolve_deployment', return_value=1):
            mock_connect.return_value = _mock_conn({'id': 1})
            cmd_ingest(args)

        out = capsys.readouterr().out
        assert '3 ingested' in out
        assert '1 skipped' in out

    def test_prints_errors(self, tmp_path, capsys):
        # Arrange
        source = tmp_path / 'source'
        source.mkdir()
        args = _args(source=source, data_root=tmp_path / 'data', deployment_id=1)

        mock_summary = IngestSummary(ingested=0, skipped=0, errors={'bad.jpg': 'read error'})
        with patch('crittercam.cli.cmd_ingest.connect') as mock_connect, \
                patch('crittercam.cli.cmd_ingest.ingest', return_value=mock_summary), \
                patch('crittercam.cli.cmd_ingest._resolve_deployment', return_value=1):
            mock_connect.return_value = _mock_conn({'id': 1})
            cmd_ingest(args)

        out = capsys.readouterr().out
        assert 'bad.jpg' in out
        assert 'read error' in out


class TestResolveDeployment:
    """Test the _resolve_deployment helper."""

    def test_returns_id_when_valid_deployment_id_supplied(self):
        # Arrange
        conn = _mock_conn({'id': 3})

        # Act
        result = _resolve_deployment(conn, deployment_id=3)

        # Assert
        assert result == 3

    def test_returns_none_when_deployment_id_not_found(self, capsys):
        # Arrange
        conn = _mock_conn(None)

        # Act
        result = _resolve_deployment(conn, deployment_id=99)

        # Assert
        assert result is None
        assert 'Error' in capsys.readouterr().out

    def test_selects_existing_deployment_from_list(self):
        # Arrange — two deployments, user picks the first
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = [
            {'id': 1, 'deployment_name': 'cam_a', 'location_name': 'backyard',
             'camera_make': 'BROWNING', 'camera_model': 'BTC-8EHP5U'},
            {'id': 2, 'deployment_name': 'cam_b', 'location_name': 'front',
             'camera_make': 'BROWNING', 'camera_model': 'BTC-8EHP5U'},
        ]

        with patch('builtins.input', return_value='1'):
            result = _resolve_deployment(conn, deployment_id=None)

        assert result == 1

    def test_reprompts_on_invalid_input(self):
        # Arrange — user types garbage then a valid choice
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = [
            {'id': 1, 'deployment_name': 'cam_a', 'location_name': None,
             'camera_make': None, 'camera_model': None},
        ]

        with patch('builtins.input', side_effect=['abc', '0', '1']):
            result = _resolve_deployment(conn, deployment_id=None)

        assert result == 1

    def test_creates_new_deployment_when_selected(self):
        # Arrange — no existing deployments, user picks "create new"
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = []
        conn.execute.return_value.lastrowid = 5

        inputs = ['1', 'my_cam', 'forest', 'BROWNING', 'BTC-8EHP5U']
        with patch('builtins.input', side_effect=inputs):
            result = _resolve_deployment(conn, deployment_id=None)

        assert result == 5
        conn.commit.assert_called_once()

    def test_creates_new_deployment_prefills_camera_from_exif(self, tmp_path):
        # Arrange — source_dir has a JPEG; camera fields should be pre-filled
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = []
        conn.execute.return_value.lastrowid = 7

        (tmp_path / 'img.jpg').touch()

        detected = ImageMetadata(
            captured_at=None,
            width=None,
            height=None,
            camera_make='BROWNING',
            camera_model='BTC-8EHP5U',
            temperature_c=None,
        )
        # user accepts detected camera values by pressing enter
        inputs = ['1', 'my_cam', 'forest', '', '']
        with patch('crittercam.cli.cmd_ingest.read_exif', return_value=detected), \
                patch('builtins.input', side_effect=inputs):
            result = _resolve_deployment(conn, deployment_id=None, source_dir=tmp_path)

        assert result == 7
        conn.commit.assert_called_once()
        # verify the INSERT used the EXIF-detected values
        insert_call = conn.execute.call_args_list[-1]
        params = insert_call[0][1]
        assert params['camera_make'] == 'BROWNING'
        assert params['camera_model'] == 'BTC-8EHP5U'
