"""read_text_from_image — run OCR on a cropped image region.

PaddleOCR is the primary engine.  The module exposes a thin wrapper so that
the engine can be swapped out (e.g. for EasyOCR) without touching the rest of
the pipeline.
"""
from __future__ import annotations

import logging
from typing import NamedTuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class OCRDetection(NamedTuple):
    """Single text detection with spatial position."""

    text: str
    confidence: float
    center_x: float
    center_y: float


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
        result = self._run_ocr(preprocessed)

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

    def read_lines(self, image: np.ndarray) -> str:
        """Spatially-aware OCR that reconstructs proper text lines.

        PaddleOCR may detect left-aligned text (e.g. character names) and
        right-aligned text (e.g. damage numbers) as **separate** text
        regions even though they belong to the same visual line.

        This method groups detections by vertical position and sorts them
        left-to-right within each group, producing correctly reconstructed
        multi-line text.

        Parameters
        ----------
        image:
            BGR or single-channel image array.

        Returns
        -------
        str
            Reconstructed text with one visual line per ``\\n``.
        """
        if image.size == 0:
            logger.debug("OCR read_lines skipped: empty image")
            return ""

        preprocessed = preprocess_for_ocr(image) if image.ndim == 3 else image
        result = self._run_ocr(preprocessed)

        detections: list[OCRDetection] = []
        if result:
            for page in result:
                if page is None:
                    continue
                for line in page:
                    box = line[0]  # [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
                    text: str = line[1][0]
                    confidence: float = line[1][1]
                    center_x = sum(p[0] for p in box) / len(box)
                    center_y = sum(p[1] for p in box) / len(box)
                    detections.append(OCRDetection(text, confidence, center_x, center_y))

        if not detections:
            return ""

        joined = _reconstruct_lines(detections, preprocessed.shape[0])
        logger.debug(
            "OCR read_lines (image %dx%d): %r",
            image.shape[1], image.shape[0], joined,
        )
        return joined

    def _run_ocr(self, preprocessed: np.ndarray) -> list:
        """Run PaddleOCR on an already-preprocessed image."""
        ocr = self._get_ocr()
        return ocr.ocr(preprocessed, cls=True)  # type: ignore[union-attr]


def _reconstruct_lines(
    detections: list[OCRDetection],
    image_height: int,
) -> str:
    """Group OCR detections into visual lines using spatial proximity.

    Detections whose vertical centres are within *row_threshold* pixels of
    each other are considered part of the same line.  Within each line the
    detections are sorted left-to-right and concatenated with a space.

    The threshold is derived from the image height: ``image_height / 8``
    (clamped to a minimum of 10 px).  For typical character-list crops
    (4 rows in ~306 px after 3× upscale) this yields ~38 px — well within
    one row but far smaller than the ~76 px inter-row distance.
    """
    row_threshold = max(image_height / 8, 10.0)

    sorted_dets = sorted(detections, key=lambda d: d.center_y)
    rows: list[list[OCRDetection]] = []

    for det in sorted_dets:
        placed = False
        for row in rows:
            avg_y = sum(d.center_y for d in row) / len(row)
            if abs(det.center_y - avg_y) < row_threshold:
                row.append(det)
                placed = True
                break
        if not placed:
            rows.append([det])

    rows.sort(key=lambda r: sum(d.center_y for d in r) / len(r))

    lines: list[str] = []
    for row in rows:
        row.sort(key=lambda d: d.center_x)
        lines.append(" ".join(d.text for d in row))

    return "\n".join(lines)


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
