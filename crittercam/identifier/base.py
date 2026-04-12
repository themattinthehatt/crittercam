"""Base types for the swappable identifier interface."""

import numpy as np
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class Embedding:
    """A single embedding result from an identifier.

    Attributes:
        vector: unit-normalised embedding vector as a 1-D float32 numpy array
    """

    vector: np.ndarray


class Identifier(Protocol):
    """Protocol for swappable identifier implementations.

    All identifiers must expose model_name and model_version for provenance
    tracking in the detections table, and implement embed() following the
    contract below.
    """

    model_name: str
    model_version: str | None

    def embed(self, image_path: Path) -> Embedding:
        """Compute a re-identification embedding for a single image.

        Args:
            image_path: path to a JPEG image file (typically a detection crop)

        Returns:
            Embedding containing a unit-normalised float32 vector
        """
        ...
