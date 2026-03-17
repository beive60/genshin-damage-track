"""read_text_from_image — run OCR on a cropped image region.

PaddleOCR is the primary engine.  The module exposes a thin wrapper so that
the engine can be swapped out (e.g. for EasyOCR) without touching the rest of
the pipeline.
"""
from __future__ import annotations

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def preprocess_for_ocr(cropped: np.ndarray, scale_factor: int = 3) -> np.ndarray:
    """Improve OCR accuracy by upscaling and converting to grayscale.

    Small ROI crops (e.g. 169×31 px) often fail PaddleOCR's text detector
    because the character strokes are too thin.  Upscaling by *scale_factor*
    before recognition significantly improves detection rates.

    Parameters
    ----------
    cropped:
        BGR image array of the region of interest.
    scale_factor:
        Integer multiplier for width and height (default 3).

    Returns
    -------
    np.ndarray
        Pre-processed single-channel grayscale image.
    """
    if cropped.size == 0:
        return cropped

    upscaled = cv2.resize(
        cropped, None,
        fx=scale_factor, fy=scale_factor,
        interpolation=cv2.INTER_CUBIC,
    )
    gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
    return gray


class OCREngine:
    """Lazy-initialised PaddleOCR wrapper.

    The model is loaded only on the first call to :meth:`read` to avoid
    importing heavy dependencies at module import time.
    """

    def __init__(self, use_gpu: bool = False) -> None:
        self._use_gpu = use_gpu
        self._ocr: object | None = None

    def _get_ocr(self) -> object:
        if self._ocr is None:
            from paddleocr import PaddleOCR  # type: ignore[import-untyped]

            self._ocr = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=self._use_gpu)
        return self._ocr

    def read(self, image: np.ndarray) -> str:
        """Run OCR on *image* and return the concatenated recognised text.

        Parameters
        ----------
        image:
            BGR or single-channel image array.

        Returns
        -------
        str
            All recognised text lines joined by newlines.  Returns an empty
            string when *image* is empty or nothing is recognised.
        """
        if image.size == 0:
            logger.debug("OCR skipped: empty image (size=0)")
            return ""

        preprocessed = preprocess_for_ocr(image) if image.ndim == 3 else image
        ocr = self._get_ocr()
        result = ocr.ocr(preprocessed, cls=True)  # type: ignore[union-attr]

        lines: list[str] = []
        if result:
            for page in result:
                if page is None:
                    continue
                for line in page:
                    text: str = line[1][0]
                    lines.append(text)
        joined = "\n".join(lines)
        logger.debug("OCR result (image %dx%d): %r", image.shape[1], image.shape[0], joined)
        return joined


def read_text_from_image(image: np.ndarray, engine: OCREngine | None = None) -> str:
    """Convenience wrapper: run OCR on *image* with a default :class:`OCREngine`.

    Parameters
    ----------
    image:
        BGR image array.
    engine:
        Optional pre-initialised :class:`OCREngine`.  A new instance is
        created when not provided.

    Returns
    -------
    str
        Recognised text or empty string.
    """
    if engine is None:
        engine = OCREngine()
    return engine.read(image)
