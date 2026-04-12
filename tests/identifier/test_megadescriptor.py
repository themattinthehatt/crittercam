"""Tests for crittercam.identifier.megadescriptor."""

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import numpy as np
import pytest

from crittercam.identifier.base import Embedding


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_feature_tensor(values: list[float]) -> MagicMock:
    """Return a mock tensor whose numpy() chain yields the given values as float32."""
    arr = np.array(values, dtype=np.float32)
    tensor = MagicMock()
    tensor.squeeze.return_value.cpu.return_value.numpy.return_value = arr
    return tensor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_timm_torch(tmp_path):
    """Stub out timm, torch, and PIL so no GPU or model weights are needed.

    Yields a dict with handles to the mock model instance and the feature
    tensor returned by the model's forward pass. Tests can override
    ``mocks['features']`` to control what embed() sees.
    """
    mock_model = MagicMock()
    mock_model.return_value = _make_feature_tensor([3.0, 4.0])  # norm = 5.0

    mock_timm = MagicMock()
    mock_timm.create_model.return_value = mock_model
    # model.to() and model.eval() must return the model itself to support chaining
    mock_model.to.return_value = mock_model
    mock_model.eval.return_value = mock_model
    mock_timm.data.resolve_model_data_config.return_value = {
        'input_size': (3, 384, 384),
        'mean': (0.485, 0.456, 0.406),
        'std': (0.229, 0.224, 0.225),
    }
    # create_transform returns a callable that produces a mock tensor
    mock_input_tensor = MagicMock()
    mock_input_tensor.unsqueeze.return_value.to.return_value = mock_input_tensor
    mock_timm.data.create_transform.return_value = MagicMock(return_value=mock_input_tensor)

    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = False
    mock_torch.no_grad.return_value.__enter__ = MagicMock(return_value=None)
    mock_torch.no_grad.return_value.__exit__ = MagicMock(return_value=False)

    mock_pil = MagicMock()
    mock_pil.Image.open.return_value.convert.return_value = MagicMock()

    stub_modules = {
        'timm': mock_timm,
        'timm.data': mock_timm.data,
        'torch': mock_torch,
    }

    with patch.dict('sys.modules', stub_modules), \
            patch('PIL.Image.open', mock_pil.Image.open):
        yield {
            'model': mock_model,
            'timm': mock_timm,
            'torch': mock_torch,
            'pil': mock_pil,
        }


@pytest.fixture
def adapter(mock_timm_torch):
    """Return an initialised MegaDescriptorAdapter with mocked dependencies."""
    from crittercam.identifier.megadescriptor import MegaDescriptorAdapter
    return MegaDescriptorAdapter()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMegaDescriptorAdapterInit:
    """Test MegaDescriptorAdapter.__init__."""

    def test_creates_model_with_correct_hub_id(self, mock_timm_torch):
        # Arrange / Act
        from crittercam.identifier.megadescriptor import MegaDescriptorAdapter, _DEFAULT_MODEL
        MegaDescriptorAdapter()

        # Assert
        mock_timm_torch['timm'].create_model.assert_called_once_with(
            _DEFAULT_MODEL, num_classes=0, pretrained=True,
        )

    def test_model_set_to_eval_mode(self, mock_timm_torch):
        # Arrange / Act
        from crittercam.identifier.megadescriptor import MegaDescriptorAdapter
        MegaDescriptorAdapter()

        # Assert
        mock_timm_torch['model'].eval.assert_called_once()

    def test_model_moved_to_device(self, mock_timm_torch):
        # Arrange — CUDA not available, so device should be cpu
        mock_timm_torch['torch'].cuda.is_available.return_value = False

        # Act
        from crittercam.identifier.megadescriptor import MegaDescriptorAdapter
        MegaDescriptorAdapter()

        # Assert
        mock_timm_torch['model'].to.assert_called_once_with('cpu')

    def test_uses_cuda_when_available(self, mock_timm_torch):
        # Arrange
        mock_timm_torch['torch'].cuda.is_available.return_value = True

        # Act
        from crittercam.identifier.megadescriptor import MegaDescriptorAdapter
        MegaDescriptorAdapter()

        # Assert
        mock_timm_torch['model'].to.assert_called_once_with('cuda')

    def test_explicit_device_overrides_autodetect(self, mock_timm_torch):
        # Arrange
        mock_timm_torch['torch'].cuda.is_available.return_value = True

        # Act
        from crittercam.identifier.megadescriptor import MegaDescriptorAdapter
        MegaDescriptorAdapter(device='cpu')

        # Assert
        mock_timm_torch['model'].to.assert_called_once_with('cpu')

    def test_creates_transform_from_model_config(self, mock_timm_torch):
        # Arrange / Act
        from crittercam.identifier.megadescriptor import MegaDescriptorAdapter
        MegaDescriptorAdapter()

        # Assert
        mock_timm_torch['timm'].data.resolve_model_data_config.assert_called_once()
        mock_timm_torch['timm'].data.create_transform.assert_called_once()


class TestMegaDescriptorAdapterEmbed:
    """Test MegaDescriptorAdapter.embed."""

    def test_returns_embedding_instance(self, adapter, tmp_path, mock_timm_torch):
        # Arrange
        img_path = tmp_path / 'crop.jpg'
        img_path.touch()

        # Act
        result = adapter.embed(img_path)

        # Assert
        assert isinstance(result, Embedding)

    def test_vector_is_float32_numpy_array(self, adapter, tmp_path, mock_timm_torch):
        # Arrange
        img_path = tmp_path / 'crop.jpg'
        img_path.touch()

        # Act
        result = adapter.embed(img_path)

        # Assert
        assert isinstance(result.vector, np.ndarray)
        assert result.vector.dtype == np.float32

    def test_vector_is_unit_normalised(self, adapter, tmp_path, mock_timm_torch):
        # Arrange — mock returns [3.0, 4.0], norm = 5.0
        img_path = tmp_path / 'crop.jpg'
        img_path.touch()

        # Act
        result = adapter.embed(img_path)

        # Assert — should be normalised to [0.6, 0.8]
        assert np.linalg.norm(result.vector) == pytest.approx(1.0, abs=1e-6)
        np.testing.assert_allclose(result.vector, [0.6, 0.8], atol=1e-6)

    def test_zero_vector_not_normalised(self, mock_timm_torch, tmp_path):
        # Arrange — model returns all-zero features (edge case: no division by zero)
        mock_timm_torch['model'].return_value = _make_feature_tensor([0.0, 0.0])
        from crittercam.identifier.megadescriptor import MegaDescriptorAdapter
        adapter = MegaDescriptorAdapter()
        img_path = tmp_path / 'crop.jpg'
        img_path.touch()

        # Act
        result = adapter.embed(img_path)

        # Assert — vector remains zero, no exception raised
        np.testing.assert_array_equal(result.vector, [0.0, 0.0])

    def test_opens_image_as_rgb(self, adapter, tmp_path, mock_timm_torch):
        # Arrange
        img_path = tmp_path / 'crop.jpg'
        img_path.touch()

        # Act
        adapter.embed(img_path)

        # Assert
        mock_timm_torch['pil'].Image.open.assert_called_once_with(img_path)
        mock_timm_torch['pil'].Image.open.return_value.convert.assert_called_once_with('RGB')

    def test_runs_inference_under_no_grad(self, adapter, tmp_path, mock_timm_torch):
        # Arrange
        img_path = tmp_path / 'crop.jpg'
        img_path.touch()

        # Act
        adapter.embed(img_path)

        # Assert — no_grad context manager was entered
        mock_timm_torch['torch'].no_grad.assert_called_once()
        mock_timm_torch['torch'].no_grad.return_value.__enter__.assert_called_once()


class TestMegaDescriptorAdapterProvenance:
    """Test provenance attributes on the adapter (not on the result)."""

    def test_model_name_class_attribute(self):
        # provenance lives on the adapter, not on Embedding — read by the pipeline
        from crittercam.identifier.megadescriptor import MegaDescriptorAdapter
        assert MegaDescriptorAdapter.model_name == 'megadescriptor'

    def test_model_version_class_attribute(self):
        from crittercam.identifier.megadescriptor import MegaDescriptorAdapter
        assert MegaDescriptorAdapter.model_version == 'L-384'
