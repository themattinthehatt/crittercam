"""Tests for crittercam.cli.cmd_serve."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from crittercam.cli.cmd_serve import cmd_build_ui, cmd_serve
from crittercam.config import Config


# ---------------------------------------------------------------------------
# cmd_serve
# ---------------------------------------------------------------------------

class TestCmdServe:
    """Test the cmd_serve function."""

    def _make_config(self, tmp_path: Path) -> Config:
        return Config(data_root=tmp_path / 'data')

    def test_exits_when_no_config(self, tmp_path, monkeypatch):
        # Arrange — config does not exist; load() raises FileNotFoundError
        monkeypatch.setattr('crittercam.cli.cmd_serve.CONFIG_PATH', tmp_path / 'missing.toml')
        with patch('crittercam.cli.cmd_serve.load', side_effect=FileNotFoundError):
            with pytest.raises(SystemExit) as exc_info:
                cmd_serve(port=8000)
        assert exc_info.value.code == 1

    def test_opens_browser_and_starts_uvicorn(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setattr('crittercam.cli.cmd_serve.CONFIG_PATH', tmp_path / 'config.toml')
        config = self._make_config(tmp_path)

        with patch('crittercam.cli.cmd_serve.load', return_value=config), \
                patch('crittercam.cli.cmd_serve.webbrowser.open') as mock_browser, \
                patch('uvicorn.run') as mock_uvicorn:
            cmd_serve(port=8000)

        mock_browser.assert_called_once_with('http://localhost:8000')
        mock_uvicorn.assert_called_once_with(
            'crittercam.web.server:app',
            host='0.0.0.0',
            port=8000,
            reload=False,
        )

    def test_respects_custom_port(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setattr('crittercam.cli.cmd_serve.CONFIG_PATH', tmp_path / 'config.toml')
        config = self._make_config(tmp_path)

        with patch('crittercam.cli.cmd_serve.load', return_value=config), \
                patch('crittercam.cli.cmd_serve.webbrowser.open') as mock_browser, \
                patch('uvicorn.run') as mock_uvicorn:
            cmd_serve(port=9000)

        mock_browser.assert_called_once_with('http://localhost:9000')
        mock_uvicorn.assert_called_once_with(
            'crittercam.web.server:app',
            host='0.0.0.0',
            port=9000,
            reload=False,
        )

    def test_warns_when_dist_missing(self, tmp_path, monkeypatch, capsys):
        # Arrange — no dist/ directory
        monkeypatch.setattr('crittercam.cli.cmd_serve.CONFIG_PATH', tmp_path / 'config.toml')
        config = self._make_config(tmp_path)

        # point _UI_DIR at a location without dist/
        monkeypatch.setattr('crittercam.cli.cmd_serve._UI_DIR', tmp_path / 'ui')

        with patch('crittercam.cli.cmd_serve.load', return_value=config), \
                patch('crittercam.cli.cmd_serve.webbrowser.open'), \
                patch('uvicorn.run'):
            cmd_serve(port=8000)

        captured = capsys.readouterr()
        assert 'Warning' in captured.out
        assert 'build-ui' in captured.out

    def test_no_warning_when_dist_present(self, tmp_path, monkeypatch, capsys):
        # Arrange — create a dist/ directory
        dist_dir = tmp_path / 'ui' / 'dist'
        dist_dir.mkdir(parents=True)
        monkeypatch.setattr('crittercam.cli.cmd_serve._UI_DIR', tmp_path / 'ui')
        monkeypatch.setattr('crittercam.cli.cmd_serve.CONFIG_PATH', tmp_path / 'config.toml')
        config = self._make_config(tmp_path)

        with patch('crittercam.cli.cmd_serve.load', return_value=config), \
                patch('crittercam.cli.cmd_serve.webbrowser.open'), \
                patch('uvicorn.run'):
            cmd_serve(port=8000)

        captured = capsys.readouterr()
        assert 'Warning' not in captured.out


# ---------------------------------------------------------------------------
# cmd_build_ui
# ---------------------------------------------------------------------------

class TestCmdBuildUi:
    """Test the cmd_build_ui function."""

    def test_exits_when_ui_dir_missing(self, tmp_path, monkeypatch):
        # Arrange — point _UI_DIR at a non-existent directory
        monkeypatch.setattr('crittercam.cli.cmd_serve._UI_DIR', tmp_path / 'no_such_dir')

        with pytest.raises(SystemExit) as exc_info:
            cmd_build_ui()
        assert exc_info.value.code == 1

    def test_runs_npm_build(self, tmp_path, monkeypatch):
        # Arrange — create a fake ui dir with a dist/ to simulate success
        ui_dir = tmp_path / 'ui'
        ui_dir.mkdir()
        dist_dir = ui_dir / 'dist'
        dist_dir.mkdir()
        monkeypatch.setattr('crittercam.cli.cmd_serve._UI_DIR', ui_dir)

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch('subprocess.run', return_value=mock_result) as mock_run:
            cmd_build_ui()

        mock_run.assert_called_once_with(
            ['npm', 'run', 'build'],
            cwd=ui_dir,
        )

    def test_exits_on_npm_failure(self, tmp_path, monkeypatch):
        # Arrange
        ui_dir = tmp_path / 'ui'
        ui_dir.mkdir()
        monkeypatch.setattr('crittercam.cli.cmd_serve._UI_DIR', ui_dir)

        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch('subprocess.run', return_value=mock_result):
            with pytest.raises(SystemExit) as exc_info:
                cmd_build_ui()
        assert exc_info.value.code == 1
