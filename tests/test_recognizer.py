"""Tests for pipeline/recognizer.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from genshin_damage_track.pipeline.recognizer import OCREngine, preprocess_for_ocr, read_text_from_image


class TestPreprocessForOcr:
    def test_returns_empty_on_empty_input(self):
        empty = np.empty((0, 0, 3), dtype=np.uint8)
        result = preprocess_for_ocr(empty)
        assert result.size == 0

    def test_output_is_single_channel(self):
        image = np.full((100, 200, 3), 128, dtype=np.uint8)
        result = preprocess_for_ocr(image)
        assert result.ndim == 2  # single-channel grayscale image

    def test_output_shape_upscaled(self):
        image = np.random.randint(0, 255, (80, 160, 3), dtype=np.uint8)
        result = preprocess_for_ocr(image)
        assert result.shape == (80 * 3, 160 * 3)  # default 3x upscale

    def test_custom_scale_factor(self):
        image = np.random.randint(0, 255, (50, 100, 3), dtype=np.uint8)
        result = preprocess_for_ocr(image, scale_factor=2)
        assert result.shape == (100, 200)


def _make_ocr_result(text: str):
    """Build a fake PaddleOCR result for a single line."""
    return [[[None, [text, 0.99]]]]


class TestOCREngine:
    def _make_engine_with_mock_ocr(self, ocr_text: str) -> OCREngine:
        engine = OCREngine()
        mock_ocr = MagicMock()
        mock_ocr.ocr.return_value = _make_ocr_result(ocr_text)
        engine._ocr = mock_ocr
        return engine

    def test_returns_empty_string_on_empty_image(self):
        engine = OCREngine()
        empty = np.empty((0, 0, 3), dtype=np.uint8)
        assert engine.read(empty) == ""

    def test_returns_recognised_text(self):
        engine = self._make_engine_with_mock_ocr("12345")
        image = np.full((100, 200, 3), 128, dtype=np.uint8)
        result = engine.read(image)
        assert "12345" in result

    def test_handles_none_page_in_result(self):
        engine = OCREngine()
        mock_ocr = MagicMock()
        mock_ocr.ocr.return_value = [None]
        engine._ocr = mock_ocr

        image = np.full((100, 200, 3), 128, dtype=np.uint8)
        result = engine.read(image)
        assert result == ""


class TestReadTextFromImage:
    def test_creates_default_engine_when_none(self):
        empty = np.empty((0, 0, 3), dtype=np.uint8)
        result = read_text_from_image(empty)
        assert result == ""
