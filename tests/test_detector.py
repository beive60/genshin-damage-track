"""Tests for detector.py."""
from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from genshin_damage_track.detector import detect_pattern
from genshin_damage_track.models import RegionPattern


def _make_engine(responses: list[str]) -> MagicMock:
    """Return a mock OCREngine whose read() yields *responses* in order."""
    engine = MagicMock()
    engine.read.side_effect = responses
    return engine


def _frames(count: int = 5):
    """Yield *count* blank FHD frames."""
    for _ in range(count):
        yield np.zeros((1080, 1920, 3), dtype=np.uint8)


class TestDetectPattern:
    def test_returns_none_when_no_valid_region(self):
        """When all REGIONS bboxes are placeholders (zero area), detection yields None."""
        engine = _make_engine(["", ""])
        result = detect_pattern(_frames(2), engine=engine)
        assert result is None

    def test_respects_max_probe_frames(self):
        """Engine.read should be called at most max_probe_frames × (number of valid regions) times."""
        engine = _make_engine([""] * 100)

        # Patch REGIONS to have a valid region so that engine.read is actually called
        from unittest.mock import patch
        valid_regions = {
            "pattern_1": {"party_damage": {"x1": 100, "y1": 100, "x2": 200, "y2": 200}},
            "pattern_2": {"party_damage": {"x1": 0, "y1": 0, "x2": 0, "y2": 0}},
        }
        with patch("genshin_damage_track.detector.REGIONS", valid_regions):
            detect_pattern(_frames(50), engine=engine, max_probe_frames=3)

        # At most 3 calls (one per probed frame for pattern_1)
        assert engine.read.call_count <= 3

    def test_detects_pattern_1_on_numeric_result(self):
        """When pattern_1 region yields a number, PATTERN_1 is returned."""
        valid_regions = {
            "pattern_1": {"party_damage": {"x1": 100, "y1": 100, "x2": 200, "y2": 200}},
            "pattern_2": {"party_damage": {"x1": 0, "y1": 0, "x2": 0, "y2": 0}},
        }
        engine = _make_engine(["12345"])

        from unittest.mock import patch
        with patch("genshin_damage_track.detector.REGIONS", valid_regions):
            result = detect_pattern(_frames(5), engine=engine)

        assert result == RegionPattern.PATTERN_1

    def test_detects_pattern_2_on_numeric_result(self):
        """When pattern_2 region yields a number (and pattern_1 is placeholder), PATTERN_2 is returned."""
        valid_regions = {
            "pattern_1": {"party_damage": {"x1": 0, "y1": 0, "x2": 0, "y2": 0}},
            "pattern_2": {"party_damage": {"x1": 100, "y1": 100, "x2": 200, "y2": 200}},
        }
        engine = _make_engine(["12345"])

        from unittest.mock import patch
        with patch("genshin_damage_track.detector.REGIONS", valid_regions):
            result = detect_pattern(_frames(5), engine=engine)

        assert result == RegionPattern.PATTERN_2

    def test_returns_none_on_exhausted_frames_without_match(self):
        valid_regions = {
            "pattern_1": {"party_damage": {"x1": 100, "y1": 100, "x2": 200, "y2": 200}},
            "pattern_2": {"party_damage": {"x1": 0, "y1": 0, "x2": 0, "y2": 0}},
        }
        engine = _make_engine(["no number"] * 10)

        from unittest.mock import patch
        with patch("genshin_damage_track.detector.REGIONS", valid_regions):
            result = detect_pattern(_frames(5), engine=engine)

        assert result is None
