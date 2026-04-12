"""MegaDescriptor identifier adapter (BVRA/MegaDescriptor-L-384)."""

import logging
import numpy as np
from pathlib import Path

from crittercam.identifier.base import Embedding

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = 'hf-hub:BVRA/MegaDescriptor-L-384'
_MODEL_VERSION = 'L-384'

# ImageNet mean and std used by MegaDescriptor's timm preprocessing pipeline
_IMAGENET_MEAN = (0.485, 0.456, 0.406)
_IMAGENET_STD = (0.229, 0.224, 0.225)


class MegaDescriptorAdapter:
    """Identifier adapter wrapping MegaDescriptor-L-384 via timm.

    Loads model weights on instantiation. Designed to be created once per
    processing run and reused across many embed() calls.

    Args:
        model_name: timm/HuggingFace model identifier string
        device: torch device string (e.g. 'cpu', 'cuda'); defaults to 'cuda'
            if available, otherwise 'cpu'
    """

    model_name: str = 'megadescriptor'
    model_version: str | None = _MODEL_VERSION

    def __init__(
        self,
        model_name: str = _DEFAULT_MODEL,
        device: str | None = None,
    ) -> None:
        import timm
        import torch

        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self._device = device
        logger.info(f'loading MegaDescriptor model: {model_name} on {device}')
        self._model = timm.create_model(model_name, num_classes=0, pretrained=True)
        self._model = self._model.to(self._device)
        self._model.eval()

        # resolve the preprocessing config from the model's pretrained cfg
        data_cfg = timm.data.resolve_model_data_config(self._model)
        self._transforms = timm.data.create_transform(**data_cfg, is_training=False)

    def embed(self, image_path: Path) -> Embedding:
        """Compute a unit-normalised re-identification embedding for a single image.

        Args:
            image_path: path to a JPEG image file (typically a detection crop)

        Returns:
            Embedding containing a unit-normalised float32 vector of length 384
            and model provenance fields

        Raises:
            RuntimeError: if the image cannot be opened or the model fails
        """
        import torch
        import PIL.Image

        pil_img = PIL.Image.open(image_path).convert('RGB')
        tensor = self._transforms(pil_img).unsqueeze(0).to(self._device)

        with torch.no_grad():
            features = self._model(tensor)

        vector = features.squeeze(0).cpu().numpy().astype(np.float32)

        # unit-normalise so cosine similarity reduces to a dot product
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return Embedding(vector=vector)
