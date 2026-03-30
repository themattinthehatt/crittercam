"""SpeciesNet classifier adapter (google/cameratrapai)."""

import logging
from pathlib import Path

from crittercam.classifier.base import Detection

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = 'kaggle:google/speciesnet/pyTorch/v4.0.2a/1'


class SpeciesNetAdapter:
    """Classifier adapter wrapping Google's SpeciesNet ensemble.

    Loads model weights on instantiation. Designed to be created once per
    processing run and reused across many classify() calls.

    Args:
        country: ISO 3166-1 alpha-3 country code for geofencing (e.g. 'USA')
        admin1_region: state/province abbreviation for geofencing (e.g. 'CT')
        model_name: SpeciesNet model identifier string
    """

    model_name: str = 'speciesnet'
    model_version: str | None = 'v4.0.2a'

    def __init__(
        self,
        country: str | None = None,
        admin1_region: str | None = None,
        model_name: str = _DEFAULT_MODEL,
    ) -> None:
        from speciesnet.classifier import SpeciesNetClassifier
        from speciesnet.detector import SpeciesNetDetector
        from speciesnet.ensemble import SpeciesNetEnsemble

        self._country = country
        self._admin1_region = admin1_region
        self._model_name = model_name
        logger.info('loading SpeciesNet model: %s', model_name)
        self._detector = SpeciesNetDetector(model_name)
        self._classifier_model = SpeciesNetClassifier(model_name)
        self._ensemble = SpeciesNetEnsemble(model_name, geofence=bool(country))

    def classify(self, image_path: Path) -> list[Detection]:
        """Run SpeciesNet detection and classification on a single image.

        Args:
            image_path: path to a JPEG image file

        Returns:
            single-element list containing a Detection on success;
            empty list if SpeciesNet returns no prediction

        Raises:
            RuntimeError: if SpeciesNet reports component failures
        """
        import PIL.Image

        filepath = str(image_path)

        # load image once; convert to RGB to handle MPO/CMYK/palette modes
        pil_img = PIL.Image.open(image_path).convert('RGB')

        # each component has its own preprocess() that returns a PreprocessedImage
        detection_result = self._detector.predict(filepath, self._detector.preprocess(pil_img))
        classification_result = self._classifier_model.predict(
            filepath, self._classifier_model.preprocess(pil_img),
        )

        geolocation_result: dict[str, str] = {}
        if self._country:
            geolocation_result['country'] = self._country
        if self._admin1_region:
            geolocation_result['admin1_region'] = self._admin1_region

        results = self._ensemble.combine(
            filepaths=[filepath],
            classifier_results={filepath: classification_result},
            detector_results={filepath: detection_result},
            geolocation_results={filepath: geolocation_result},
            partial_predictions={},
        )

        result = results[0]

        failures = result.get('failures', [])
        if failures:
            raise RuntimeError(f'SpeciesNet reported failures: {failures}')

        label = result.get('prediction', '')
        if not label:
            return []

        label = str(label).lower()
        confidence = float(result.get('prediction_score', 0.0))

        bbox = None
        if label != 'blank':
            raw_detections = result.get('detections', [])
            if raw_detections:
                raw_bbox = raw_detections[0].get('bbox')
                if raw_bbox and len(raw_bbox) == 4:
                    bbox = (
                        float(raw_bbox[0]),
                        float(raw_bbox[1]),
                        float(raw_bbox[2]),
                        float(raw_bbox[3]),
                    )

        return [Detection(label=label, confidence=confidence, bbox=bbox)]
