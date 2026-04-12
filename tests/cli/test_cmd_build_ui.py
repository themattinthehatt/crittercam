"""Tests for crittercam.cli.cmd_build_ui."""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from crittercam.cli.cmd_build_ui import cmd_build_ui


class TestCmdBuildUi:
    """Test the cmd_build_ui function."""

    def _args(self) -> argparse.Namespace:
        """Build a minimal Namespace for cmd_build_ui."""
        return argparse.Namespace()

    def test_exits_when_ui_dir_missing(self, tmp_path, monkeypatch):
        # Arrange — point _UI_DIR at a non-existent directory
        monkeypatch.setattr('crittercam.cli.cmd_build_ui._UI_DIR', tmp_path / 'no_such_dir')

        with pytest.raises(SystemExit) as exc_info:
            cmd_build_ui(self._args())
        assert exc_info.value.code == 1

    def test_runs_npm_build(self, tmp_path, monkeypatch):
        # Arrange
        ui_dir = tmp_path / 'ui'
        ui_dir.mkdir()
        monkeypatch.setattr('crittercam.cli.cmd_build_ui._UI_DIR', ui_dir)

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch('subprocess.run', return_value=mock_result) as mock_run:
            cmd_build_ui(self._args())

        mock_run.assert_called_once_with(
            ['npm', 'run', 'build'],
            cwd=ui_dir,
        )

    def test_exits_on_npm_failure(self, tmp_path, monkeypatch):
        # Arrange
        ui_dir = tmp_path / 'ui'
        ui_dir.mkdir()
        monkeypatch.setattr('crittercam.cli.cmd_build_ui._UI_DIR', ui_dir)

        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch('subprocess.run', return_value=mock_result):
            with pytest.raises(SystemExit) as exc_info:
                cmd_build_ui(self._args())
        assert exc_info.value.code == 1
