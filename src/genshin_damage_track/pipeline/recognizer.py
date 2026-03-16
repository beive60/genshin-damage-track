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


def preprocess_for_ocr(cropped: np.ndarray) -> np.ndarray:
    """Improve OCR accuracy with grayscale conversion, binarisation and noise removal.

    Parameters
    ----------
    cropped:
        BGR image array of the region of interest.

    Returns
    -------
    np.ndarray
        Pre-processed single-channel binary image.
    """
    if cropped.size == 0:
        return cropped

    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2,
    )
    kernel = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    return cleaned


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
