"""Base types for the swappable classifier interface."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class Detection:
    """A single detection result from a classifier.

    Attributes:
        label: species label or special value ('blank', 'animal', 'human', 'vehicle')
        confidence: prediction confidence in [0, 1]
        bbox: normalized bounding box as (x, y, w, h) in [0, 1] coordinates,
            where x/y are the top-left corner; None if no bounding box
    """

    label: str
    confidence: float
    bbox: tuple[float, float, float, float] | None


class Classifier(Protocol):
    """Protocol for swappable classifier implementations.

    All classifiers must expose model_name and model_version for provenance
    tracking in the detections table, and implement classify() following
    the contract below.
    """

    model_name: str
    model_version: str | None

    def classify(self, image_path: Path) -> list[Detection]:
        """Run detection and classification on a single image.

        Args:
            image_path: path to a JPEG image file

        Returns:
            list of Detection objects; a single-element list on success
            (including a Detection with label='blank' for confirmed empty frames);
            empty list if the classifier produces no prediction
        """
        ...
