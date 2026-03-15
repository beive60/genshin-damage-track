"""Tests for pipeline/parser.py."""
from __future__ import annotations

import pytest

from genshin_damage_track.pipeline.parser import (
    parse_character_entries,
    parse_character_name,
    parse_to_numeric,
)


class TestParseToNumeric:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("12345", 12345),
            ("12,345", 12345),
            ("太郎: 12345 (67%)", 12345),
            ("胡桃 123,456", 123456),
            ("  12345  ", 12345),
            # OCR mis-recognition corrections (uppercase look-alikes only)
            ("1O2O3", 10203),   # O → 0
            ("l2345", 12345),   # l → 1
            ("I2345", 12345),   # I → 1
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


class TestParseCharacterName:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("胡桃 123,456", "胡桃"),
            ("太郎: 12345", "太郎"),
            ("雷電将軍 99999", "雷電将軍"),
        ],
    )
    def test_extracts_cjk_name(self, text, expected):
        assert parse_character_name(text) == expected

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "   ",
            None,
            "12345",
            "Alice 100",
        ],
    )
    def test_returns_none_for_non_cjk_or_empty(self, text):
        assert parse_character_name(text) is None


class TestParseCharacterEntries:
    def test_single_entry(self):
        text = "太郎: 12345 (67%)"
        entries = parse_character_entries(text)
        assert len(entries) == 1
        assert entries[0].name == "太郎"
        assert entries[0].damage == 12345
        assert entries[0].percentage == pytest.approx(67.0)

    def test_multiple_entries(self):
        text = "太郎: 12345 (67%)\n次郎: 678 (12%)\n三郎: 90 (8%)\n四郎: 10 (1%)"
        entries = parse_character_entries(text)
        assert len(entries) == 4
        assert entries[0].name == "太郎"
        assert entries[0].damage == 12345
        assert entries[1].name == "次郎"
        assert entries[1].damage == 678
        assert entries[2].name == "三郎"
        assert entries[2].damage == 90
        assert entries[3].name == "四郎"
        assert entries[3].damage == 10

    def test_at_most_4_entries(self):
        text = "\n".join(
            f"キャラ{chr(0x5b50 + i)}: {i * 100} ({i}%)" for i in range(1, 6)
        )
        entries = parse_character_entries(text)
        assert len(entries) == 4

    def test_handles_comma_separated_damage(self):
        text = "胡桃: 123,456 (55%)"
        entries = parse_character_entries(text)
        assert len(entries) == 1
        assert entries[0].damage == 123456

    def test_handles_fullwidth_colon_and_parens(self):
        text = "太郎：12345（67%）"
        entries = parse_character_entries(text)
        assert len(entries) == 1
        assert entries[0].name == "太郎"

    def test_handles_decimal_percentage(self):
        text = "太郎: 12345 (67.5%)"
        entries = parse_character_entries(text)
        assert len(entries) == 1
        assert entries[0].percentage == pytest.approx(67.5)

    def test_returns_empty_for_no_match(self):
        assert parse_character_entries("no match here") == []

    def test_returns_empty_for_empty_input(self):
        assert parse_character_entries("") == []
        assert parse_character_entries(None) == []
        assert parse_character_entries("   ") == []
