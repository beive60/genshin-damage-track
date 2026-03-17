"""Tests for visualizer.py — CSV output logic."""
from __future__ import annotations

import csv

from genshin_damage_track.models import (
    CharacterDamage,
    DpsRecord,
    ExtractionResult,
    RegionPattern,
)
from genshin_damage_track.visualizer import write_csv


class TestWriteCsv:
    def test_total_only_has_basic_columns(self, tmp_path):
        result = ExtractionResult(
            pattern=RegionPattern.TOTAL_ONLY,
            dps_records=[
                DpsRecord(timestamp_sec=1.0, dps=1000.0, delta_damage=1000, total_damage=1000),
            ],
        )
        out = tmp_path / "out.csv"
        write_csv(result, out)
        rows = list(csv.DictReader(out.open(encoding="utf-8")))
        assert list(rows[0].keys()) == ["timestamp_sec", "dps", "delta_damage", "total_damage"]

    def test_per_character_includes_char_columns(self, tmp_path):
        chars = [
            CharacterDamage(name="太郎", damage=800, percentage=80.0),
            CharacterDamage(name="次郎", damage=200, percentage=20.0),
        ]
        result = ExtractionResult(
            pattern=RegionPattern.PER_CHARACTER,
            dps_records=[
                DpsRecord(
                    timestamp_sec=1.0, dps=1000.0, delta_damage=1000,
                    total_damage=1000, characters=chars,
                ),
            ],
        )
        out = tmp_path / "out.csv"
        write_csv(result, out)
        rows = list(csv.DictReader(out.open(encoding="utf-8")))
        assert len(rows) == 1
        assert rows[0]["char1_name"] == "太郎"
        assert rows[0]["char1_damage"] == "800"
        assert rows[0]["char1_pct"] == "80.0"
        assert rows[0]["char2_name"] == "次郎"
        assert rows[0]["char2_damage"] == "200"
        assert rows[0]["char2_pct"] == "20.0"

    def test_per_character_empty_characters_no_extra_columns(self, tmp_path):
        result = ExtractionResult(
            pattern=RegionPattern.PER_CHARACTER,
            dps_records=[
                DpsRecord(timestamp_sec=1.0, dps=500.0, delta_damage=500, total_damage=500),
            ],
        )
        out = tmp_path / "out.csv"
        write_csv(result, out)
        rows = list(csv.DictReader(out.open(encoding="utf-8")))
        assert list(rows[0].keys()) == ["timestamp_sec", "dps", "delta_damage", "total_damage"]

    def test_varying_character_count_pads_columns(self, tmp_path):
        result = ExtractionResult(
            pattern=RegionPattern.PER_CHARACTER,
            dps_records=[
                DpsRecord(
                    timestamp_sec=1.0, dps=1000.0, delta_damage=1000,
                    total_damage=1000,
                    characters=[CharacterDamage(name="太郎", damage=1000, percentage=100.0)],
                ),
                DpsRecord(
                    timestamp_sec=2.0, dps=1500.0, delta_damage=2000,
                    total_damage=3000,
                    characters=[
                        CharacterDamage(name="太郎", damage=1800, percentage=60.0),
                        CharacterDamage(name="次郎", damage=1200, percentage=40.0),
                    ],
                ),
            ],
        )
        out = tmp_path / "out.csv"
        write_csv(result, out)
        rows = list(csv.DictReader(out.open(encoding="utf-8")))
        # Max 2 characters → 2 sets of char columns
        assert "char2_name" in rows[0]
        # First row only has 1 character; char2 fields should be empty
        assert rows[0]["char2_name"] == ""
        assert rows[1]["char2_name"] == "次郎"
