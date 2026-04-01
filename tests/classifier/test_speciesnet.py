"""Tests for crittercam.classifier.speciesnet."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crittercam.classifier.base import Detection

_MOCK_PIL_IMAGE = MagicMock(name='pil_image')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_classifier_result(classes=None, scores=None, failures=None):
    """Build a minimal SpeciesNetClassifier output dict."""
    if failures:
        return {'filepath': '/img.jpg', 'failures': failures}
    return {
        'filepath': '/img.jpg',
        'classifications': {
            'classes': classes if classes is not None else [],
            'scores': scores if scores is not None else [],
        },
    }


def _make_detector_result(detections=None):
    """Build a minimal SpeciesNetDetector output dict."""
    return {'filepath': '/img.jpg', 'detections': detections if detections is not None else []}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_speciesnet():
    """Inject fake speciesnet stub modules so no package install is needed.

    Yields a dict of pre-configured mock instances (detector, classifier)
    whose return values can be overridden per test.
    """
    mock_detector_inst = MagicMock()
    mock_detector_inst.predict.return_value = _make_detector_result()

    mock_classifier_inst = MagicMock()
    mock_classifier_inst.predict.return_value = _make_classifier_result()

    # minimal BBox stand-in used by the lazy import inside classify()
    class _BBox:
        def __init__(self, xmin, ymin, width, height):
            self.xmin = xmin
            self.ymin = ymin
            self.width = width
            self.height = height

    stub_modules = {
        'speciesnet': MagicMock(),
        'speciesnet.detector': MagicMock(SpeciesNetDetector=MagicMock(return_value=mock_detector_inst)),
        'speciesnet.classifier': MagicMock(SpeciesNetClassifier=MagicMock(return_value=mock_classifier_inst)),
        'speciesnet.ensemble': MagicMock(),
        'speciesnet.utils': MagicMock(BBox=_BBox),
    }

    mock_pil_module = MagicMock()
    mock_pil_module.Image.open.return_value.convert.return_value = _MOCK_PIL_IMAGE

    with patch.dict('sys.modules', stub_modules), \
            patch('PIL.Image.open', mock_pil_module.Image.open):
        yield {
            'detector': mock_detector_inst,
            'classifier': mock_classifier_inst,
        }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSpeciesNetAdapterClassify:
    """Test the SpeciesNetAdapter.classify method."""

    def test_returns_detection_for_animal(self, mock_speciesnet):
        # Arrange
        from crittercam.classifier.speciesnet import SpeciesNetAdapter
        mock_speciesnet['classifier'].predict.return_value = _make_classifier_result(
            classes=['coyote', 'canid', 'animal'], scores=[0.91, 0.06, 0.02],
        )
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
        mock_speciesnet['classifier'].predict.return_value = _make_classifier_result(
            classes=['deer'], scores=[0.8],
        )
        mock_speciesnet['detector'].predict.return_value = _make_detector_result(
            detections=[{'bbox': [0.1, 0.2, 0.3, 0.4], 'conf': 0.8, 'category': '1'}],
        )
        adapter = SpeciesNetAdapter()

        # Act
        result = adapter.classify(Path('/img.jpg'))

        # Assert — stored as (x, y, w, h) exactly as SpeciesNet returns it
        assert result[0].bbox == (0.1, 0.2, 0.3, 0.4)

    def test_blank_returns_detection_with_no_bbox(self, mock_speciesnet):
        # Arrange
        from crittercam.classifier.speciesnet import SpeciesNetAdapter
        mock_speciesnet['classifier'].predict.return_value = _make_classifier_result(
            classes=['blank'], scores=[0.99],
        )
        mock_speciesnet['detector'].predict.return_value = _make_detector_result(
            detections=[{'bbox': [0.1, 0.2, 0.3, 0.4], 'conf': 0.9, 'category': '1'}],
        )
        adapter = SpeciesNetAdapter()

        # Act
        result = adapter.classify(Path('/img.jpg'))

        # Assert — blank label suppresses bbox even when detector found something
        assert result[0].label == 'blank'
        assert result[0].bbox is None

    def test_label_normalized_to_lowercase(self, mock_speciesnet):
        # Arrange
        from crittercam.classifier.speciesnet import SpeciesNetAdapter
        mock_speciesnet['classifier'].predict.return_value = _make_classifier_result(
            classes=['ANIMAL'], scores=[0.7],
        )
        adapter = SpeciesNetAdapter()

        # Act
        result = adapter.classify(Path('/img.jpg'))

        # Assert
        assert result[0].label == 'animal'

    def test_raises_on_component_failures(self, mock_speciesnet):
        # Arrange
        from crittercam.classifier.speciesnet import SpeciesNetAdapter
        mock_speciesnet['classifier'].predict.return_value = _make_classifier_result(
            failures=['CLASSIFIER'],
        )
        adapter = SpeciesNetAdapter()

        # Act / Assert
        with pytest.raises(RuntimeError, match='failures'):
            adapter.classify(Path('/img.jpg'))

    def test_returns_empty_list_when_no_classes(self, mock_speciesnet):
        # Arrange
        from crittercam.classifier.speciesnet import SpeciesNetAdapter
        mock_speciesnet['classifier'].predict.return_value = _make_classifier_result(
            classes=[], scores=[],
        )
        adapter = SpeciesNetAdapter()

        # Act
        result = adapter.classify(Path('/img.jpg'))

        # Assert
        assert result == []

    def test_no_bbox_when_detections_list_empty(self, mock_speciesnet):
        # Arrange
        from crittercam.classifier.speciesnet import SpeciesNetAdapter
        mock_speciesnet['classifier'].predict.return_value = _make_classifier_result(
            classes=['raccoon'], scores=[0.85],
        )
        mock_speciesnet['detector'].predict.return_value = _make_detector_result(detections=[])
        adapter = SpeciesNetAdapter()

        # Act
        result = adapter.classify(Path('/img.jpg'))

        # Assert
        assert result[0].bbox is None

    def test_classifier_receives_bbox_from_detector(self, mock_speciesnet):
        # Arrange — verify detector bbox is forwarded to classifier preprocess
        from crittercam.classifier.speciesnet import SpeciesNetAdapter
        mock_speciesnet['classifier'].predict.return_value = _make_classifier_result(
            classes=['squirrel'], scores=[0.88],
        )
        mock_speciesnet['detector'].predict.return_value = _make_detector_result(
            detections=[{'bbox': [0.1, 0.2, 0.3, 0.4], 'conf': 0.9, 'category': '1'}],
        )
        adapter = SpeciesNetAdapter()

        # Act
        adapter.classify(Path('/img.jpg'))

        # Assert — classifier preprocess called with a non-None bboxes list
        preprocess_call = mock_speciesnet['classifier'].preprocess.call_args
        bboxes = preprocess_call.kwargs.get('bboxes') or preprocess_call.args[1]
        assert bboxes is not None
        assert len(bboxes) == 1
