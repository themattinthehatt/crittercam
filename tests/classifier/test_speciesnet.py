"""Tests for crittercam.classifier.speciesnet."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crittercam.classifier.base import Detection

_MOCK_PIL_IMAGE = MagicMock(name='pil_image')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ensemble_result(
    prediction='coyote',
    prediction_score=0.91,
    detections=None,
    failures=None,
):
    """Build a minimal SpeciesNet ensemble output dict."""
    return {
        'filepath': '/img.jpg',
        'prediction': prediction,
        'prediction_score': prediction_score,
        'detections': detections if detections is not None else [],
        'failures': failures if failures is not None else [],
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_speciesnet():
    """Inject fake speciesnet stub modules so no package install is needed.

    Yields a dict of pre-configured mock instances (detector, classifier, ensemble)
    whose return values can be overridden per test.
    """
    mock_detector_inst = MagicMock()
    mock_detector_inst.predict.return_value = {'detections': []}

    mock_classifier_inst = MagicMock()
    mock_classifier_inst.predict.return_value = {'classifications': {}}

    mock_ensemble_inst = MagicMock()

    stub_modules = {
        'speciesnet': MagicMock(),
        'speciesnet.detector': MagicMock(SpeciesNetDetector=MagicMock(return_value=mock_detector_inst)),
        'speciesnet.classifier': MagicMock(SpeciesNetClassifier=MagicMock(return_value=mock_classifier_inst)),
        'speciesnet.ensemble': MagicMock(SpeciesNetEnsemble=MagicMock(return_value=mock_ensemble_inst)),
    }

    mock_pil_module = MagicMock()
    mock_pil_module.Image.open.return_value.convert.return_value = _MOCK_PIL_IMAGE

    with patch.dict('sys.modules', stub_modules), \
            patch('PIL.Image.open', mock_pil_module.Image.open):
        yield {
            'detector': mock_detector_inst,
            'classifier': mock_classifier_inst,
            'ensemble': mock_ensemble_inst,
        }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSpeciesNetAdapterClassify:
    """Test the SpeciesNetAdapter.classify method."""

    def test_returns_detection_for_animal(self, mock_speciesnet):
        # Arrange
        from crittercam.classifier.speciesnet import SpeciesNetAdapter
        mock_speciesnet['ensemble'].combine.return_value = [
            _make_ensemble_result(
                prediction='coyote',
                prediction_score=0.91,
                detections=[{'bbox': [0.1, 0.2, 0.3, 0.4], 'conf': 0.91, 'category': '1'}],
            )
        ]
        adapter = SpeciesNetAdapter()

        # Act
        result = adapter.classify(Path('/img.jpg'))

        # Assert
        assert len(result) == 1
        assert result[0].label == 'coyote'
        assert result[0].confidence == pytest.approx(0.91)

    def test_bbox_stored_as_xywh(self, mock_speciesnet):
        # Arrange
        from crittercam.classifier.speciesnet import SpeciesNetAdapter
        mock_speciesnet['ensemble'].combine.return_value = [
            _make_ensemble_result(
                prediction='deer',
                detections=[{'bbox': [0.1, 0.2, 0.3, 0.4], 'conf': 0.8, 'category': '1'}],
            )
        ]
        adapter = SpeciesNetAdapter()

        # Act
        result = adapter.classify(Path('/img.jpg'))

        # Assert — stored as (x, y, w, h) exactly as SpeciesNet returns it
        assert result[0].bbox == (0.1, 0.2, 0.3, 0.4)

    def test_blank_returns_detection_with_no_bbox(self, mock_speciesnet):
        # Arrange
        from crittercam.classifier.speciesnet import SpeciesNetAdapter
        mock_speciesnet['ensemble'].combine.return_value = [
            _make_ensemble_result(prediction='blank', prediction_score=0.99)
        ]
        adapter = SpeciesNetAdapter()

        # Act
        result = adapter.classify(Path('/img.jpg'))

        # Assert
        assert result[0].label == 'blank'
        assert result[0].bbox is None

    def test_label_normalized_to_lowercase(self, mock_speciesnet):
        # Arrange
        from crittercam.classifier.speciesnet import SpeciesNetAdapter
        mock_speciesnet['ensemble'].combine.return_value = [
            _make_ensemble_result(prediction='ANIMAL', prediction_score=0.7)
        ]
        adapter = SpeciesNetAdapter()

        # Act
        result = adapter.classify(Path('/img.jpg'))

        # Assert
        assert result[0].label == 'animal'

    def test_raises_on_component_failures(self, mock_speciesnet):
        # Arrange
        from crittercam.classifier.speciesnet import SpeciesNetAdapter
        mock_speciesnet['ensemble'].combine.return_value = [
            _make_ensemble_result(failures=['DETECTOR'])
        ]
        adapter = SpeciesNetAdapter()

        # Act / Assert
        with pytest.raises(RuntimeError, match='failures'):
            adapter.classify(Path('/img.jpg'))

    def test_returns_empty_list_when_no_prediction(self, mock_speciesnet):
        # Arrange
        from crittercam.classifier.speciesnet import SpeciesNetAdapter
        mock_speciesnet['ensemble'].combine.return_value = [
            _make_ensemble_result(prediction='')
        ]
        adapter = SpeciesNetAdapter()

        # Act
        result = adapter.classify(Path('/img.jpg'))

        # Assert
        assert result == []

    def test_no_bbox_when_detections_list_empty(self, mock_speciesnet):
        # Arrange
        from crittercam.classifier.speciesnet import SpeciesNetAdapter
        mock_speciesnet['ensemble'].combine.return_value = [
            _make_ensemble_result(prediction='raccoon', detections=[])
        ]
        adapter = SpeciesNetAdapter()

        # Act
        result = adapter.classify(Path('/img.jpg'))

        # Assert
        assert result[0].bbox is None

    def test_geolocation_passed_to_ensemble(self, mock_speciesnet):
        # Arrange
        from crittercam.classifier.speciesnet import SpeciesNetAdapter
        mock_speciesnet['ensemble'].combine.return_value = [
            _make_ensemble_result()
        ]
        adapter = SpeciesNetAdapter(country='USA', admin1_region='CT')

        # Act
        adapter.classify(Path('/img.jpg'))

        # Assert — geolocation dict forwarded to ensemble.combine
        call_kwargs = mock_speciesnet['ensemble'].combine.call_args.kwargs
        geo = call_kwargs['geolocation_results']['/img.jpg']
        assert geo['country'] == 'USA'
        assert geo['admin1_region'] == 'CT'
