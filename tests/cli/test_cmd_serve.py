"""Tests for crittercam.cli.cmd_serve."""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from crittercam.cli.cmd_serve import cmd_serve
from crittercam.config import Config


def _serve_args(port: int = 8000) -> argparse.Namespace:
    """Build a minimal Namespace for cmd_serve."""
    return argparse.Namespace(port=port)


class TestCmdServe:
    """Test the cmd_serve function."""

    def _make_config(self, tmp_path: Path) -> Config:
        return Config(data_root=tmp_path / 'data')

    def test_exits_when_no_config(self, tmp_path, monkeypatch):
        # Arrange — config does not exist; load() raises FileNotFoundError
        monkeypatch.setattr('crittercam.cli.cmd_serve.CONFIG_PATH', tmp_path / 'missing.toml')
        with patch('crittercam.cli.cmd_serve.load', side_effect=FileNotFoundError):
            with pytest.raises(SystemExit) as exc_info:
                cmd_serve(_serve_args())
        assert exc_info.value.code == 1

    def test_opens_browser_and_starts_uvicorn(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setattr('crittercam.cli.cmd_serve.CONFIG_PATH', tmp_path / 'config.toml')
        config = self._make_config(tmp_path)

        with patch('crittercam.cli.cmd_serve.load', return_value=config), \
                patch('crittercam.cli.cmd_serve.webbrowser.open') as mock_browser, \
                patch('uvicorn.run') as mock_uvicorn:
            cmd_serve(_serve_args(port=8000))

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
            cmd_serve(_serve_args(port=9000))

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
        monkeypatch.setattr('crittercam.cli.cmd_serve._UI_DIR', tmp_path / 'ui')
        config = self._make_config(tmp_path)

        with patch('crittercam.cli.cmd_serve.load', return_value=config), \
                patch('crittercam.cli.cmd_serve.webbrowser.open'), \
                patch('uvicorn.run'):
            cmd_serve(_serve_args())

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
            cmd_serve(_serve_args())

        captured = capsys.readouterr()
        assert 'Warning' not in captured.out
