"""Tests for crittercam.cli.cmd_classify."""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crittercam.cli.cmd_classify import cmd_classify
from crittercam.config import Config
from crittercam.pipeline.classify import ClassifySummary


def _args(
    data_root=None,
    country=None,
    admin1_region=None,
    crop_padding=0.15,
    retry_errors=False,
    reclassify_all=False,
):
    """Build a minimal Namespace for cmd_classify."""
    return argparse.Namespace(
        data_root=data_root,
        country=country,
        admin1_region=admin1_region,
        crop_padding=crop_padding,
        retry_errors=retry_errors,
        reclassify_all=reclassify_all,
    )


@pytest.fixture
def mock_classify_stack(tmp_path, monkeypatch):
    """Patch heavy dependencies so cmd_classify can run without a real model or DB."""
    config = Config(data_root=tmp_path / 'data', country=None, admin1_region=None)
    config_path = tmp_path / 'config.toml'
    monkeypatch.setattr('crittercam.cli.cmd_classify.CONFIG_PATH', config_path)

    mock_conn = MagicMock()
    mock_summary = ClassifySummary(classified=0)

    with patch('crittercam.cli.cmd_classify.load', return_value=config), \
            patch('crittercam.cli.cmd_classify.connect', return_value=mock_conn), \
            patch('crittercam.classifier.speciesnet.SpeciesNetAdapter') as mock_adapter_cls, \
            patch('crittercam.pipeline.classify.classify_pending', return_value=mock_summary), \
            patch('crittercam.pipeline.db.reset_errors', return_value=0), \
            patch('crittercam.pipeline.db.reset_all', return_value=0):
        yield {
            'config': config,
            'conn': mock_conn,
            'adapter_cls': mock_adapter_cls,
            'summary': mock_summary,
        }


class TestCmdClassifyGeoValidation:
    """Test country and admin1_region validation in cmd_classify."""

    def test_exits_on_invalid_country(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setattr('crittercam.cli.cmd_classify.CONFIG_PATH', tmp_path / 'cfg.toml')
        config = Config(data_root=tmp_path / 'data')
        args = _args(country='ZZZ')

        with patch('crittercam.cli.cmd_classify.load', return_value=config):
            with pytest.raises(SystemExit) as exc_info:
                cmd_classify(args)
        assert exc_info.value.code == 1

    def test_exits_on_invalid_admin1_region(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setattr('crittercam.cli.cmd_classify.CONFIG_PATH', tmp_path / 'cfg.toml')
        config = Config(data_root=tmp_path / 'data')
        args = _args(country='USA', admin1_region='!!!')

        with patch('crittercam.cli.cmd_classify.load', return_value=config):
            with pytest.raises(SystemExit) as exc_info:
                cmd_classify(args)
        assert exc_info.value.code == 1

    def test_valid_country_and_admin1_pass_through(self, mock_classify_stack):
        # Act — should not raise
        cmd_classify(_args(country='USA', admin1_region='CT'))

        # Assert — adapter constructed with correct geo args
        mock_classify_stack['adapter_cls'].assert_called_once_with(
            country='USA', admin1_region='CT',
        )

    def test_exits_when_no_config(self, tmp_path, monkeypatch):
        # Arrange — config file does not exist; load() will raise FileNotFoundError
        monkeypatch.setattr('crittercam.cli.cmd_classify.CONFIG_PATH', tmp_path / 'missing.toml')
        args = _args()

        with pytest.raises(SystemExit) as exc_info:
            cmd_classify(args)
        assert exc_info.value.code == 1

    def test_country_falls_back_to_config(self, mock_classify_stack):
        # Arrange — config has country set, args does not override
        mock_classify_stack['config'].country = 'CAN'
        args = _args(country=None)

        # Act
        cmd_classify(args)

        # Assert — adapter received country from config
        mock_classify_stack['adapter_cls'].assert_called_once_with(
            country='CAN', admin1_region=None,
        )


class TestCmdClassifyResetFlags:
    """Test --retry-errors and --reclassify-all flags."""

    def test_retry_errors_calls_reset_errors(self, mock_classify_stack):
        with patch('crittercam.pipeline.db.reset_errors', return_value=2) as mock_reset:
            cmd_classify(_args(retry_errors=True))
        mock_reset.assert_called_once()

    def test_reclassify_all_calls_reset_all(self, mock_classify_stack):
        with patch('crittercam.pipeline.db.reset_all', return_value=5) as mock_reset:
            cmd_classify(_args(reclassify_all=True))
        mock_reset.assert_called_once()

    def test_reclassify_all_takes_precedence_over_retry_errors(self, mock_classify_stack):
        with patch('crittercam.pipeline.db.reset_all', return_value=1) as mock_all, \
                patch('crittercam.pipeline.db.reset_errors', return_value=0) as mock_err:
            cmd_classify(_args(reclassify_all=True, retry_errors=True))
        mock_all.assert_called_once()
        mock_err.assert_not_called()
