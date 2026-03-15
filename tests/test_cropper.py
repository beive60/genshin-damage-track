"""Tests for pipeline/cropper.py."""
from __future__ import annotations

import numpy as np
import pytest

from genshin_damage_track.pipeline.cropper import crop_region_of_interest


class TestCropRegionOfInterest:
    def test_basic_crop(self, blank_frame, sample_bbox):
        cropped = crop_region_of_interest(blank_frame, sample_bbox)
        expected_h = sample_bbox["y2"] - sample_bbox["y1"]
        expected_w = sample_bbox["x2"] - sample_bbox["x1"]
        assert cropped.shape[:2] == (expected_h, expected_w)

    def test_zero_area_bbox_returns_empty(self, blank_frame):
        bbox = {"x1": 100, "y1": 100, "x2": 100, "y2": 200}
        result = crop_region_of_interest(blank_frame, bbox)
        assert result.size == 0

    def test_placeholder_bbox_returns_empty(self, blank_frame):
        """Placeholder bbox (all zeros) must return an empty array."""
        bbox = {"x1": 0, "y1": 0, "x2": 0, "y2": 0}
        result = crop_region_of_interest(blank_frame, bbox)
        assert result.size == 0

    def test_missing_key_raises_value_error(self, blank_frame):
        bad_bbox = {"x1": 10, "y1": 10, "x2": 100}  # missing y2
        with pytest.raises(ValueError, match="bbox must contain keys"):
            crop_region_of_interest(blank_frame, bad_bbox)

    def test_bbox_clamped_to_frame_bounds(self, blank_frame):
        bbox = {"x1": 1800, "y1": 1000, "x2": 2000, "y2": 1200}  # extends beyond 1920×1080
        cropped = crop_region_of_interest(blank_frame, bbox)
        assert cropped.shape[0] > 0 and cropped.shape[1] > 0

    def test_pixel_values_are_preserved(self, sample_bbox):
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame[490:590, 860:1060] = [0, 128, 255]

        cropped = crop_region_of_interest(frame, sample_bbox)
        assert np.all(cropped == [0, 128, 255])

    def test_returns_copy_not_view(self, blank_frame, sample_bbox):
        cropped = crop_region_of_interest(blank_frame, sample_bbox)
        cropped[:] = 42
        assert np.all(blank_frame == 0), "Original frame must not be mutated"
