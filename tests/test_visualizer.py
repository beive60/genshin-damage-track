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

    def test_per_character_columns_use_party_names(self, tmp_path):
        chars = [
            CharacterDamage(slot=0, name="胡桃", damage=800),
            CharacterDamage(slot=1, name="鍾離", damage=200),
        ]
        result = ExtractionResult(
            pattern=RegionPattern.PER_CHARACTER,
            party=["胡桃", "鍾離"],
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
        assert rows[0]["胡桃_damage"] == "800"
        assert rows[0]["胡桃_dps"] == "800.00"  # 1000 * 0.8
        assert rows[0]["胡桃_pct"] == "80.0"  # 800/1000*100
        assert rows[0]["鍾離_damage"] == "200"
        assert rows[0]["鍾離_dps"] == "200.00"  # 1000 * 0.2
        assert rows[0]["鍾離_pct"] == "20.0"  # 200/1000*100
        # No char{N}_name columns
        assert "char1_name" not in rows[0]

    def test_empty_party_no_extra_columns(self, tmp_path):
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

    def test_missing_character_in_frame_gets_empty_values(self, tmp_path):
        result = ExtractionResult(
            pattern=RegionPattern.PER_CHARACTER,
            party=["胡桃", "鍾離"],
            dps_records=[
                DpsRecord(
                    timestamp_sec=1.0, dps=1000.0, delta_damage=1000,
                    total_damage=1000,
                    characters=[CharacterDamage(slot=0, name="胡桃", damage=1000)],
                ),
                DpsRecord(
                    timestamp_sec=2.0, dps=1500.0, delta_damage=2000,
                    total_damage=3000,
                    characters=[
                        CharacterDamage(slot=0, name="胡桃", damage=1800),
                        CharacterDamage(slot=1, name="鍾離", damage=1200),
                    ],
                ),
            ],
        )
        out = tmp_path / "out.csv"
        write_csv(result, out)
        rows = list(csv.DictReader(out.open(encoding="utf-8")))
        # First row: 鍾離 not present → empty
        assert rows[0]["鍾離_damage"] == ""
        assert rows[0]["鍾離_dps"] == ""
        assert rows[0]["鍾離_pct"] == ""
        # Second row: both present
        assert rows[1]["鍾離_damage"] == "1200"
        assert rows[1]["鍾離_dps"] == "600.00"  # 1500 * (1200/3000)
        assert rows[1]["胡桃_damage"] == "1800"
        assert rows[1]["胡桃_dps"] == "900.00"  # 1500 * (1800/3000)
