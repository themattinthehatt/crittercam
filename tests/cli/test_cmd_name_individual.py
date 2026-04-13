"""Tests for crittercam.cli.cmd_name_individual."""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from crittercam.cli.cmd_name_individual import cmd_name_individual
from crittercam.config import Config


def _args(individual_id, nickname):
    return argparse.Namespace(individual_id=individual_id, nickname=nickname)


@pytest.fixture
def mock_stack(tmp_path, monkeypatch):
    config = Config(data_root=tmp_path / 'data', country=None, admin1_region=None)
    monkeypatch.setattr('crittercam.cli.cmd_name_individual.CONFIG_PATH', tmp_path / 'config.toml')
    mock_conn = MagicMock()
    with patch('crittercam.cli.cmd_name_individual.load', return_value=config), \
            patch('crittercam.cli.cmd_name_individual.connect', return_value=mock_conn), \
            patch('crittercam.pipeline.identify.name_individual'):
        yield {'conn': mock_conn}


class TestCmdNameIndividual:
    """Test the cmd_name_individual function."""

    def test_exits_when_no_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            'crittercam.cli.cmd_name_individual.CONFIG_PATH', tmp_path / 'missing.toml',
        )
        with pytest.raises(SystemExit) as exc_info:
            cmd_name_individual(_args(1, 'fluffy'))
        assert exc_info.value.code == 1

    def test_calls_name_individual(self, mock_stack):
        with patch('crittercam.pipeline.identify.name_individual') as mock_fn:
            cmd_name_individual(_args(3, 'fluffy'))
        mock_fn.assert_called_once()

    def test_passes_id_and_nickname(self, mock_stack):
        with patch('crittercam.pipeline.identify.name_individual') as mock_fn:
            cmd_name_individual(_args(3, 'fluffy'))
        args, _ = mock_fn.call_args
        assert args[1] == 3
        assert args[2] == 'fluffy'

    def test_exits_on_value_error(self, mock_stack):
        with patch('crittercam.pipeline.identify.name_individual',
                   side_effect=ValueError('individual id not found: 99')):
            with pytest.raises(SystemExit) as exc_info:
                cmd_name_individual(_args(99, 'fluffy'))
        assert exc_info.value.code == 1

    def test_connection_closed_on_success(self, mock_stack):
        with patch('crittercam.pipeline.identify.name_individual'):
            cmd_name_individual(_args(1, 'fluffy'))
        mock_stack['conn'].close.assert_called_once()

    def test_connection_closed_on_error(self, mock_stack):
        with patch('crittercam.pipeline.identify.name_individual',
                   side_effect=ValueError('not found: 99')):
            with pytest.raises(SystemExit):
                cmd_name_individual(_args(99, 'fluffy'))
        mock_stack['conn'].close.assert_called_once()
