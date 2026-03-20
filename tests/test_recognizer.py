"""Tests for pipeline/recognizer.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from genshin_damage_track.pipeline.recognizer import (
    OCRDetection,
    OCREngine,
    _reconstruct_lines,
    preprocess_for_ocr,
    read_text_from_image,
)


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


class TestReconstructLines:
    def test_single_detection_per_row(self):
        dets = [
            OCRDetection("胡桃: 12345 (67%)", 0.99, 150.0, 20.0),
            OCRDetection("鍾離: 678 (12%)", 0.99, 150.0, 100.0),
        ]
        result = _reconstruct_lines(dets, image_height=300)
        assert result == "胡桃: 12345 (67%)\n鍾離: 678 (12%)"

    def test_fragments_on_same_row_joined(self):
        """Left-aligned name and right-aligned number on same row are merged."""
        dets = [
            OCRDetection("胡桃:", 0.95, 50.0, 20.0),
            OCRDetection("12345(67%)", 0.90, 250.0, 22.0),
            OCRDetection("鍾離:", 0.95, 50.0, 100.0),
            OCRDetection("678(12%)", 0.90, 250.0, 98.0),
        ]
        result = _reconstruct_lines(dets, image_height=300)
        lines = result.split("\n")
        assert len(lines) == 2
        assert "胡桃:" in lines[0] and "12345" in lines[0]
        assert "鍾離:" in lines[1] and "678" in lines[1]

    def test_rows_sorted_top_to_bottom(self):
        """Rows should appear in top-to-bottom order regardless of input order."""
        dets = [
            OCRDetection("鍾離: 678", 0.99, 150.0, 100.0),
            OCRDetection("胡桃: 12345", 0.99, 150.0, 20.0),
        ]
        result = _reconstruct_lines(dets, image_height=300)
        lines = result.split("\n")
        assert "胡桃" in lines[0]
        assert "鍾離" in lines[1]

    def test_within_row_sorted_left_to_right(self):
        dets = [
            OCRDetection("(67%)", 0.90, 300.0, 20.0),
            OCRDetection("胡桃:", 0.95, 50.0, 22.0),
            OCRDetection("12345", 0.90, 180.0, 21.0),
        ]
        result = _reconstruct_lines(dets, image_height=300)
        assert result == "胡桃: 12345 (67%)"

    def test_empty_detections(self):
        assert _reconstruct_lines([], image_height=300) == ""

    def test_four_character_rows(self):
        """Realistic: 4 characters, each split into name and number fragments."""
        dets = [
            OCRDetection("胡桃:", 0.9, 50, 20),
            OCRDetection("12345(67%)", 0.9, 250, 22),
            OCRDetection("鍾離:", 0.9, 50, 95),
            OCRDetection("678(12%)", 0.9, 250, 97),
            OCRDetection("行秋:", 0.9, 50, 170),
            OCRDetection("90(8%)", 0.9, 250, 172),
            OCRDetection("夜蘭:", 0.9, 50, 245),
            OCRDetection("10(1%)", 0.9, 250, 247),
        ]
        result = _reconstruct_lines(dets, image_height=306)
        lines = result.split("\n")
        assert len(lines) == 4
        assert "胡桃:" in lines[0] and "12345" in lines[0]
        assert "夜蘭:" in lines[3] and "10" in lines[3]


class TestOCREngineReadLines:
    def test_returns_empty_on_empty_image(self):
        engine = OCREngine()
        empty = np.empty((0, 0, 3), dtype=np.uint8)
        assert engine.read_lines(empty) == ""

    def test_reconstructs_fragmented_lines(self):
        engine = OCREngine()
        mock_ocr = MagicMock()
        # Simulate PaddleOCR returning fragmented detections
        mock_ocr.ocr.return_value = [[
            [[[10, 5], [100, 5], [100, 30], [10, 30]], ("胡桃:", 0.95)],
            [[[200, 5], [350, 5], [350, 30], [200, 30]], ("12345(67%)", 0.90)],
            [[[10, 80], [100, 80], [100, 105], [10, 105]], ("鍾離:", 0.95)],
            [[[200, 80], [350, 80], [350, 105], [200, 105]], ("678(12%)", 0.90)],
        ]]
        engine._ocr = mock_ocr

        image = np.full((100, 200, 3), 128, dtype=np.uint8)
        result = engine.read_lines(image)
        lines = result.split("\n")
        assert len(lines) == 2
        assert "胡桃:" in lines[0] and "12345" in lines[0]
        assert "鍾離:" in lines[1] and "678" in lines[1]

    def test_handles_none_page(self):
        engine = OCREngine()
        mock_ocr = MagicMock()
        mock_ocr.ocr.return_value = [None]
        engine._ocr = mock_ocr

        image = np.full((100, 200, 3), 128, dtype=np.uint8)
        assert engine.read_lines(image) == ""
