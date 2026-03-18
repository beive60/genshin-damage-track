"""Tests for visualizer.py — CSV output and read-back logic."""
from __future__ import annotations

import csv

from genshin_damage_track.models import (
    CharacterDamage,
    DpsRecord,
    ExtractionResult,
    RegionPattern,
)
from genshin_damage_track.visualizer import read_csv, write_csv


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


class TestReadCsv:
    """Tests for read_csv() — CSV to ExtractionResult round-trip."""

    def _round_trip(self, result: ExtractionResult, tmp_path):
        """Write *result* to CSV and read it back."""
        out = tmp_path / "rt.csv"
        write_csv(result, out)
        return read_csv(out)

    def test_total_only_round_trip(self, tmp_path):
        original = ExtractionResult(
            pattern=RegionPattern.TOTAL_ONLY,
            dps_records=[
                DpsRecord(timestamp_sec=1.0, dps=1000.0, delta_damage=1000, total_damage=1000),
                DpsRecord(timestamp_sec=2.0, dps=2000.0, delta_damage=2000, total_damage=3000),
            ],
        )
        loaded = self._round_trip(original, tmp_path)
        assert loaded.pattern == RegionPattern.TOTAL_ONLY
        assert loaded.party == []
        assert len(loaded.dps_records) == 2
        assert loaded.dps_records[0].timestamp_sec == 1.0
        assert loaded.dps_records[0].dps == 1000.0
        assert loaded.dps_records[0].delta_damage == 1000
        assert loaded.dps_records[0].total_damage == 1000
        assert loaded.dps_records[1].dps == 2000.0

    def test_per_character_round_trip(self, tmp_path):
        chars = [
            CharacterDamage(slot=0, name="胡桃", damage=800),
            CharacterDamage(slot=1, name="鍾離", damage=200),
        ]
        original = ExtractionResult(
            pattern=RegionPattern.PER_CHARACTER,
            party=["胡桃", "鍾離"],
            dps_records=[
                DpsRecord(
                    timestamp_sec=1.0, dps=1000.0, delta_damage=1000,
                    total_damage=1000, characters=chars,
                ),
            ],
        )
        loaded = self._round_trip(original, tmp_path)
        assert loaded.pattern == RegionPattern.PER_CHARACTER
        assert loaded.party == ["胡桃", "鍾離"]
        assert len(loaded.dps_records) == 1
        rec = loaded.dps_records[0]
        assert len(rec.characters) == 2
        assert rec.characters[0].name == "胡桃"
        assert rec.characters[0].damage == 800
        assert rec.characters[1].name == "鍾離"
        assert rec.characters[1].damage == 200

    def test_missing_values_preserved(self, tmp_path):
        original = ExtractionResult(
            pattern=RegionPattern.TOTAL_ONLY,
            dps_records=[
                DpsRecord(timestamp_sec=1.0, dps=None, delta_damage=None, total_damage=None),
            ],
        )
        loaded = self._round_trip(original, tmp_path)
        rec = loaded.dps_records[0]
        assert rec.dps is None
        assert rec.delta_damage is None
        assert rec.total_damage is None

    def test_missing_character_in_frame(self, tmp_path):
        """When a character has no data in a row, it should not appear in characters list."""
        original = ExtractionResult(
            pattern=RegionPattern.PER_CHARACTER,
            party=["胡桃", "鍾離"],
            dps_records=[
                DpsRecord(
                    timestamp_sec=1.0, dps=1000.0, delta_damage=1000,
                    total_damage=1000,
                    characters=[CharacterDamage(slot=0, name="胡桃", damage=1000)],
                ),
            ],
        )
        loaded = self._round_trip(original, tmp_path)
        rec = loaded.dps_records[0]
        # Only 胡桃 has data; 鍾離 was empty in CSV → not in characters
        assert len(rec.characters) == 1
        assert rec.characters[0].name == "胡桃"

    def test_dps_interval_passed_through(self, tmp_path):
        original = ExtractionResult(
            pattern=RegionPattern.TOTAL_ONLY,
            dps_records=[
                DpsRecord(timestamp_sec=1.0, dps=100.0, delta_damage=100, total_damage=100),
            ],
        )
        out = tmp_path / "rt.csv"
        write_csv(original, out)
        loaded = read_csv(out, dps_interval=120)
        assert loaded.dps_interval == 120

    def test_hand_edited_csv(self, tmp_path):
        """Simulate a user hand-editing a CSV to fix OCR errors."""
        csv_content = (
            "timestamp_sec,dps,delta_damage,total_damage,胡桃_damage,胡桃_dps,胡桃_pct\n"
            "1.0,1000.00,1000,1000,1000,1000.00,100.0\n"
            "2.0,5000.00,5000,6000,3600,3000.00,60.0\n"
        )
        csv_file = tmp_path / "edited.csv"
        csv_file.write_text(csv_content, encoding="utf-8")
        loaded = read_csv(csv_file)
        assert loaded.pattern == RegionPattern.PER_CHARACTER
        assert loaded.party == ["胡桃"]
        assert len(loaded.dps_records) == 2
        assert loaded.dps_records[1].dps == 5000.0
        assert loaded.dps_records[1].total_damage == 6000
        assert loaded.dps_records[1].characters[0].damage == 3600
