"""Tests for crittercam.cli.cmd_identify."""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crittercam.cli.cmd_identify import cmd_identify
from crittercam.config import Config
from crittercam.pipeline.identify import IdentifySummary


def _args(
    data_root=None,
    species=None,
    threshold=0.75,
    retry_errors=False,
    reidentify_all=False,
):
    """Build a minimal Namespace for cmd_identify."""
    return argparse.Namespace(
        data_root=data_root,
        species=species,
        threshold=threshold,
        retry_errors=retry_errors,
        reidentify_all=reidentify_all,
    )


@pytest.fixture
def mock_identify_stack(tmp_path, monkeypatch):
    """Patch heavy dependencies so cmd_identify can run without a real model or DB."""
    config = Config(data_root=tmp_path / 'data', country=None, admin1_region=None)
    monkeypatch.setattr('crittercam.cli.cmd_identify.CONFIG_PATH', tmp_path / 'config.toml')

    mock_conn = MagicMock()
    mock_summary = IdentifySummary(embedded=0, identified=0)

    with patch('crittercam.cli.cmd_identify.load', return_value=config), \
            patch('crittercam.cli.cmd_identify.connect', return_value=mock_conn), \
            patch('crittercam.identifier.megadescriptor.MegaDescriptorAdapter'), \
            patch('crittercam.pipeline.identify.enqueue_pending', return_value=0), \
            patch('crittercam.pipeline.identify.identify_pending', return_value=mock_summary), \
            patch('crittercam.pipeline.identify.reidentify_all', return_value=0), \
            patch('crittercam.cli.cmd_identify.reset_errors', return_value=0):
        yield {
            'config': config,
            'conn': mock_conn,
            'summary': mock_summary,
        }


# ---------------------------------------------------------------------------
# TestCmdIdentifyConfig
# ---------------------------------------------------------------------------

class TestCmdIdentifyConfig:
    """Test config loading and data root handling."""

    def test_exits_when_no_config(self, tmp_path, monkeypatch):
        # Arrange — config file does not exist
        monkeypatch.setattr('crittercam.cli.cmd_identify.CONFIG_PATH', tmp_path / 'missing.toml')

        with pytest.raises(SystemExit) as exc_info:
            cmd_identify(_args())
        assert exc_info.value.code == 1

    def test_data_root_override_applied(self, mock_identify_stack, tmp_path):
        # Arrange
        override = tmp_path / 'override'

        # Act
        cmd_identify(_args(data_root=override))

        # Assert
        assert mock_identify_stack['config'].data_root == override

    def test_data_root_not_overridden_when_not_given(self, mock_identify_stack):
        # Arrange
        original = mock_identify_stack['config'].data_root

        # Act
        cmd_identify(_args(data_root=None))

        # Assert
        assert mock_identify_stack['config'].data_root == original


# ---------------------------------------------------------------------------
# TestCmdIdentifyResetFlags
# ---------------------------------------------------------------------------

class TestCmdIdentifyResetFlags:
    """Test --retry-errors and --reidentify-all flags."""

    def test_retry_errors_calls_reset_errors(self, mock_identify_stack):
        # Arrange / Act
        with patch('crittercam.cli.cmd_identify.reset_errors', return_value=2) as mock_reset:
            cmd_identify(_args(retry_errors=True))

        # Assert
        mock_reset.assert_called_once_with(mock_identify_stack['conn'], job_type='embedding')

    def test_reidentify_all_calls_reidentify_all(self, mock_identify_stack):
        # Act
        with patch('crittercam.pipeline.identify.reidentify_all', return_value=3) as mock_reid:
            cmd_identify(_args(reidentify_all=True))

        # Assert
        mock_reid.assert_called_once()

    def test_reidentify_all_passes_species_filter(self, mock_identify_stack):
        # Act
        with patch('crittercam.pipeline.identify.reidentify_all', return_value=1) as mock_reid:
            cmd_identify(_args(reidentify_all=True, species=['felis catus']))

        # Assert
        _, kwargs = mock_reid.call_args
        assert kwargs.get('species') == ['felis catus']

    def test_reidentify_all_takes_precedence_over_retry_errors(self, mock_identify_stack):
        # Act
        with patch('crittercam.pipeline.identify.reidentify_all', return_value=1) as mock_reid, \
                patch('crittercam.cli.cmd_identify.reset_errors', return_value=0) as mock_err:
            cmd_identify(_args(reidentify_all=True, retry_errors=True))

        # Assert
        mock_reid.assert_called_once()
        mock_err.assert_not_called()

    def test_no_reset_called_by_default(self, mock_identify_stack):
        # Act
        with patch('crittercam.pipeline.identify.reidentify_all') as mock_reid, \
                patch('crittercam.cli.cmd_identify.reset_errors') as mock_err:
            cmd_identify(_args())

        # Assert
        mock_reid.assert_not_called()
        mock_err.assert_not_called()


# ---------------------------------------------------------------------------
# TestCmdIdentifyEnqueueAndRun
# ---------------------------------------------------------------------------

class TestCmdIdentifyEnqueueAndRun:
    """Test enqueue_pending and identify_pending are called correctly."""

    def test_enqueue_pending_called(self, mock_identify_stack):
        # Act
        with patch('crittercam.pipeline.identify.enqueue_pending', return_value=0) as mock_enq:
            cmd_identify(_args())

        # Assert
        mock_enq.assert_called_once()

    def test_enqueue_pending_receives_species_filter(self, mock_identify_stack):
        # Act
        with patch('crittercam.pipeline.identify.enqueue_pending', return_value=0) as mock_enq:
            cmd_identify(_args(species=['felis catus']))

        # Assert
        _, kwargs = mock_enq.call_args
        assert kwargs.get('species') == ['felis catus']

    def test_identify_pending_receives_threshold(self, mock_identify_stack):
        # Act
        with patch('crittercam.pipeline.identify.identify_pending',
                   return_value=IdentifySummary()) as mock_run:
            cmd_identify(_args(threshold=0.9))

        # Assert
        _, kwargs = mock_run.call_args
        assert kwargs.get('threshold') == pytest.approx(0.9)

    def test_identify_pending_receives_species_filter(self, mock_identify_stack):
        # Act
        with patch('crittercam.pipeline.identify.identify_pending',
                   return_value=IdentifySummary()) as mock_run:
            cmd_identify(_args(species=['felis catus']))

        # Assert
        _, kwargs = mock_run.call_args
        assert kwargs.get('species') == ['felis catus']

    def test_connection_closed_on_success(self, mock_identify_stack):
        # Act
        cmd_identify(_args())

        # Assert
        mock_identify_stack['conn'].close.assert_called_once()

    def test_connection_closed_on_error(self, mock_identify_stack):
        # Arrange — identify_pending raises unexpectedly
        with patch('crittercam.pipeline.identify.identify_pending', side_effect=RuntimeError('boom')):
            with pytest.raises(RuntimeError):
                cmd_identify(_args())

        # Assert — conn.close() still called via finally
        mock_identify_stack['conn'].close.assert_called_once()
