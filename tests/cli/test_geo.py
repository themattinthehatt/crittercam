"""Tests for crittercam.cli._geo."""

from unittest.mock import patch

from crittercam.cli._geo import prompt_admin1_region, prompt_country


class TestPromptCountry:
    """Test the prompt_country function."""

    def test_returns_none_on_blank(self):
        with patch('builtins.input', return_value=''):
            assert prompt_country() is None

    def test_returns_valid_code(self):
        with patch('builtins.input', return_value='usa'):
            assert prompt_country() == 'USA'

    def test_reprompts_on_invalid_then_accepts_valid(self):
        with patch('builtins.input', side_effect=['XX', 'CAN']):
            assert prompt_country() == 'CAN'

    def test_reprompts_on_invalid_then_accepts_blank(self):
        with patch('builtins.input', side_effect=['ZZ', '']):
            assert prompt_country() is None


class TestPromptAdmin1Region:
    """Test the prompt_admin1_region function."""

    def test_returns_none_on_blank(self):
        with patch('builtins.input', return_value=''):
            assert prompt_admin1_region() is None

    def test_returns_valid_code(self):
        with patch('builtins.input', return_value='ct'):
            assert prompt_admin1_region() == 'CT'

    def test_reprompts_on_invalid_then_accepts_valid(self):
        with patch('builtins.input', side_effect=['!!', 'ON']):
            assert prompt_admin1_region() == 'ON'

    def test_reprompts_on_invalid_then_accepts_blank(self):
        with patch('builtins.input', side_effect=['!!', '']):
            assert prompt_admin1_region() is None
