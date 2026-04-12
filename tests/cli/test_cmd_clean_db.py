"""Tests for crittercam.cli.cmd_clean_db."""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from crittercam.cli.cmd_clean_db import cmd_clean_db
from crittercam.config import Config
from crittercam.pipeline.clean import CleanSummary, CleanTarget


def _args(labels=None, dry_run=False):
    """Build a minimal Namespace for cmd_clean_db."""
    return argparse.Namespace(
        labels=labels if labels is not None else ['human', 'blank'],
        dry_run=dry_run,
    )


def _target(image_id=1, detection_id=1):
    """Build a minimal CleanTarget for use in tests."""
    return CleanTarget(
        detection_id=detection_id,
        crop_path='derived/2026/01/01/img_det001.jpg',
        image_id=image_id,
        image_path='images/2026/01/01/img.jpg',
        thumb_path='derived/2026/01/01/img_thumb.jpg',
    )


@pytest.fixture
def mock_stack(tmp_path, monkeypatch):
    """Patch config, DB connection, find_targets, and delete_targets."""
    config = Config(data_root=tmp_path / 'data')
    mock_conn = MagicMock()

    monkeypatch.setattr('crittercam.cli.cmd_clean_db.CONFIG_PATH', tmp_path / 'config.toml')

    with patch('crittercam.cli.cmd_clean_db.load', return_value=config), \
            patch('crittercam.cli.cmd_clean_db.connect', return_value=mock_conn), \
            patch('crittercam.cli.cmd_clean_db.find_targets') as mock_find, \
            patch('crittercam.cli.cmd_clean_db.delete_targets') as mock_delete:
        yield {
            'config': config,
            'conn': mock_conn,
            'find': mock_find,
            'delete': mock_delete,
        }


class TestCmdCleanDbConfig:
    """Test config loading behaviour in cmd_clean_db."""

    def test_exits_when_no_config(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setattr('crittercam.cli.cmd_clean_db.CONFIG_PATH', tmp_path / 'missing.toml')
        with patch('crittercam.cli.cmd_clean_db.load', side_effect=FileNotFoundError):
            with pytest.raises(SystemExit) as exc_info:
                cmd_clean_db(_args())
        assert exc_info.value.code == 1


class TestCmdCleanDbNoMatches:
    """Test behaviour when no matching detections are found."""

    def test_prints_no_matches_message(self, mock_stack, capsys):
        # Arrange
        mock_stack['find'].return_value = []

        # Act
        cmd_clean_db(_args(labels=['human']))

        # Assert
        assert 'No active detections' in capsys.readouterr().out

    def test_does_not_call_delete(self, mock_stack):
        # Arrange
        mock_stack['find'].return_value = []

        # Act
        cmd_clean_db(_args())

        # Assert
        mock_stack['delete'].assert_not_called()


class TestCmdCleanDbDryRun:
    """Test --dry-run behaviour."""

    def test_dry_run_prints_summary(self, mock_stack, capsys):
        # Arrange
        mock_stack['find'].return_value = [_target(image_id=1), _target(image_id=2, detection_id=2)]

        # Act
        cmd_clean_db(_args(dry_run=True))

        # Assert
        out = capsys.readouterr().out
        assert 'Found 2' in out
        assert 'Dry run' in out

    def test_dry_run_does_not_delete(self, mock_stack):
        # Arrange
        mock_stack['find'].return_value = [_target()]

        # Act
        cmd_clean_db(_args(dry_run=True))

        # Assert
        mock_stack['delete'].assert_not_called()


class TestCmdCleanDbConfirmation:
    """Test the interactive confirmation prompt."""

    def test_aborts_on_no(self, mock_stack, capsys):
        # Arrange
        mock_stack['find'].return_value = [_target()]

        # Act
        with patch('builtins.input', return_value='n'):
            cmd_clean_db(_args())

        # Assert
        mock_stack['delete'].assert_not_called()
        assert 'Aborted' in capsys.readouterr().out

    def test_aborts_on_empty_input(self, mock_stack):
        # Arrange
        mock_stack['find'].return_value = [_target()]

        # Act
        with patch('builtins.input', return_value=''):
            cmd_clean_db(_args())

        # Assert
        mock_stack['delete'].assert_not_called()

    def test_proceeds_on_yes(self, mock_stack):
        # Arrange
        mock_stack['find'].return_value = [_target()]
        mock_stack['delete'].return_value = CleanSummary(detections=1, images=1, raw_images_deleted=1, thumbnails_deleted=1, crops_deleted=1)

        # Act
        with patch('builtins.input', return_value='y'):
            cmd_clean_db(_args())

        # Assert
        mock_stack['delete'].assert_called_once()


class TestCmdCleanDbSummary:
    """Test output printed after a successful deletion."""

    def test_prints_deletion_summary(self, mock_stack, capsys):
        # Arrange
        mock_stack['find'].return_value = [_target()]
        mock_stack['delete'].return_value = CleanSummary(
            detections=1, images=1,
            raw_images_deleted=1, thumbnails_deleted=1, crops_deleted=1,
        )

        # Act
        with patch('builtins.input', return_value='y'):
            cmd_clean_db(_args())

        # Assert
        out = capsys.readouterr().out
        assert 'database' in out
        assert '1 detection' in out
        assert 'disk' in out
        assert '3 files' in out
        assert '1 raw' in out
        assert '1 thumbnails' in out
        assert '1 crops' in out

    def test_prints_warning_for_missing_files(self, mock_stack, capsys):
        # Arrange
        mock_stack['find'].return_value = [_target()]
        mock_stack['delete'].return_value = CleanSummary(
            detections=1, images=1,
            raw_images_deleted=1, thumbnails_deleted=1, crops_deleted=0, files_missing=1,
        )

        # Act
        with patch('builtins.input', return_value='y'):
            cmd_clean_db(_args())

        # Assert
        out = capsys.readouterr().out
        assert 'Warning' in out
        assert '1 expected file' in out

    def test_no_warning_when_no_missing_files(self, mock_stack, capsys):
        # Arrange
        mock_stack['find'].return_value = [_target()]
        mock_stack['delete'].return_value = CleanSummary(
            detections=1, images=1,
            raw_images_deleted=1, thumbnails_deleted=1, crops_deleted=1,
        )

        # Act
        with patch('builtins.input', return_value='y'):
            cmd_clean_db(_args())

        # Assert
        assert 'Warning' not in capsys.readouterr().out

    def test_labels_are_lowercased(self, mock_stack):
        # Arrange
        mock_stack['find'].return_value = []

        # Act
        cmd_clean_db(_args(labels=['Human', 'BLANK']))

        # Assert — find_targets called with lowercased labels
        mock_stack['find'].assert_called_once_with(mock_stack['conn'], ['human', 'blank'])
