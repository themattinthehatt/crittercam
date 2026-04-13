"""Tests for crittercam.cli.cmd_merge_individuals."""

import argparse
from unittest.mock import patch

import pytest

from crittercam.cli.cmd_merge_individuals import cmd_merge_individuals
from crittercam.config import Config


def _args(ids):
    """Build a minimal Namespace for cmd_merge_individuals."""
    return argparse.Namespace(ids=ids)


@pytest.fixture
def mock_merge_stack(tmp_path, monkeypatch):
    """Patch heavy dependencies so cmd_merge_individuals can run without a real DB."""
    config = Config(data_root=tmp_path / 'data', country=None, admin1_region=None)
    monkeypatch.setattr('crittercam.cli.cmd_merge_individuals.CONFIG_PATH', tmp_path / 'config.toml')

    mock_conn = __import__('unittest.mock', fromlist=['MagicMock']).MagicMock()

    with patch('crittercam.cli.cmd_merge_individuals.load', return_value=config), \
            patch('crittercam.cli.cmd_merge_individuals.connect', return_value=mock_conn), \
            patch('crittercam.pipeline.identify.merge_individuals', return_value=2):
        yield {'conn': mock_conn}


class TestCmdMergeIndividuals:
    """Test the cmd_merge_individuals function."""

    def test_exits_when_no_config(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setattr(
            'crittercam.cli.cmd_merge_individuals.CONFIG_PATH', tmp_path / 'missing.toml',
        )
        with pytest.raises(SystemExit) as exc_info:
            cmd_merge_individuals(_args([1, 2]))
        assert exc_info.value.code == 1

    def test_exits_for_single_id(self, mock_merge_stack):
        with pytest.raises(SystemExit) as exc_info:
            cmd_merge_individuals(_args([1]))
        assert exc_info.value.code == 1

    def test_calls_merge_individuals(self, mock_merge_stack):
        with patch('crittercam.pipeline.identify.merge_individuals', return_value=1) as mock_merge:
            cmd_merge_individuals(_args([1, 3, 5]))
        mock_merge.assert_called_once()

    def test_passes_ids_to_merge(self, mock_merge_stack):
        with patch('crittercam.pipeline.identify.merge_individuals', return_value=1) as mock_merge:
            cmd_merge_individuals(_args([2, 5, 8]))
        args, _ = mock_merge.call_args
        assert args[1] == [2, 5, 8]

    def test_exits_on_value_error(self, mock_merge_stack):
        with patch('crittercam.pipeline.identify.merge_individuals',
                   side_effect=ValueError('individual id(s) not found: [99]')):
            with pytest.raises(SystemExit) as exc_info:
                cmd_merge_individuals(_args([1, 99]))
        assert exc_info.value.code == 1

    def test_connection_closed_on_success(self, mock_merge_stack):
        with patch('crittercam.pipeline.identify.merge_individuals', return_value=1):
            cmd_merge_individuals(_args([1, 2]))
        mock_merge_stack['conn'].close.assert_called_once()

    def test_connection_closed_on_error(self, mock_merge_stack):
        with patch('crittercam.pipeline.identify.merge_individuals',
                   side_effect=ValueError('not found: [99]')):
            with pytest.raises(SystemExit):
                cmd_merge_individuals(_args([1, 99]))
        mock_merge_stack['conn'].close.assert_called_once()
