"""Tests for pipeline/parser.py."""
from __future__ import annotations

import pytest

from genshin_damage_track.pipeline.parser import parse_to_numeric


class TestParseToNumeric:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("12345", 12345),
            ("12,345", 12345),
            ("鍾離: 12345 (67%)", 12345),
            ("胡桃 123,456", 123456),
            ("  12345  ", 12345),
            # OCR mis-recognition corrections (uppercase look-alikes only)
            ("1O2O3", 10203),   # O -> 0
            ("l2345", 12345),   # l -> 1
            ("I2345", 12345),   # I -> 1
        ],
    )
    def test_valid_inputs(self, text, expected):
        assert parse_to_numeric(text) == expected

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "   ",
            None,
            "no numbers here",
            "パーティ",
        ],
    )
    def test_returns_none_for_invalid_input(self, text):
        assert parse_to_numeric(text) is None

    def test_first_number_extracted(self):
        """When multiple numbers are present, only the first is returned."""
        assert parse_to_numeric("100 200 300") == 100
