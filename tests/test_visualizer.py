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
        assert list(rows[0].keys()) == ["timestamp_sec", "total_damage", "delta_damage", "dps"]

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
        assert rows[0]["胡桃_total_damage"] == "800"
        assert rows[0]["胡桃_dps"] == "800.00"  # 1000 * 0.8
        assert rows[0]["胡桃_pct"] == "80.0"  # 800/1000*100
        assert rows[0]["鍾離_total_damage"] == "200"
        assert rows[0]["鍾離_dps"] == "200.00"  # 1000 * 0.2
        assert rows[0]["鍾離_pct"] == "20.0"  # 200/1000*100

    def test_per_character_column_order(self, tmp_path):
        chars = [CharacterDamage(slot=0, name="胡桃", damage=500)]
        result = ExtractionResult(
            pattern=RegionPattern.PER_CHARACTER,
            party=["胡桃"],
            dps_records=[
                DpsRecord(
                    timestamp_sec=1.0, dps=1000.0, delta_damage=500,
                    total_damage=500, characters=chars,
                ),
            ],
        )
        out = tmp_path / "out.csv"
        write_csv(result, out)
        rows = list(csv.DictReader(out.open(encoding="utf-8")))
        assert list(rows[0].keys()) == [
            "timestamp_sec", "total_damage", "delta_damage", "dps",
            "胡桃_total_damage", "胡桃_delta_damage", "胡桃_dps", "胡桃_pct",
        ]

    def test_per_character_delta_damage(self, tmp_path):
        result = ExtractionResult(
            pattern=RegionPattern.PER_CHARACTER,
            party=["胡桃"],
            dps_records=[
                DpsRecord(
                    timestamp_sec=1.0, dps=1000.0, delta_damage=1000,
                    total_damage=1000,
                    characters=[CharacterDamage(slot=0, name="胡桃", damage=1000)],
                ),
                DpsRecord(
                    timestamp_sec=2.0, dps=1500.0, delta_damage=2000,
                    total_damage=3000,
                    characters=[CharacterDamage(slot=0, name="胡桃", damage=2500)],
                ),
            ],
        )
        out = tmp_path / "out.csv"
        write_csv(result, out)
        rows = list(csv.DictReader(out.open(encoding="utf-8")))
        # First row: no previous → delta is empty
        assert rows[0]["胡桃_delta_damage"] == ""
        # Second row: 2500 - 1000 = 1500
        assert rows[1]["胡桃_delta_damage"] == "1500"

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
        assert list(rows[0].keys()) == ["timestamp_sec", "total_damage", "delta_damage", "dps"]

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
        assert rows[0]["鍾離_total_damage"] == ""
        assert rows[0]["鍾離_delta_damage"] == ""
        assert rows[0]["鍾離_dps"] == ""
        assert rows[0]["鍾離_pct"] == ""
        # Second row: both present
        assert rows[1]["鍾離_total_damage"] == "1200"
        assert rows[1]["胡桃_total_damage"] == "1800"
        assert rows[1]["胡桃_dps"] == "900.00"  # 1500 * (1800/3000)


class TestReadCsv:
    """Tests for read_csv() — CSV read-back with recomputation."""

    def test_total_only_recomputes_dps(self, tmp_path):
        """read_csv builds FrameRecords and uses compute_dps to derive DPS."""
        csv_content = (
            "timestamp_sec,total_damage,delta_damage,dps\n"
            "1.0,1000,,\n"
            "2.0,3000,,\n"
        )
        csv_file = tmp_path / "in.csv"
        csv_file.write_text(csv_content, encoding="utf-8")
        loaded = read_csv(csv_file, dps_interval=1)
        assert loaded.pattern == RegionPattern.TOTAL_ONLY
        assert loaded.party == []
        # compute_dps produces 1 record from 2 frames (delta between them)
        assert len(loaded.dps_records) == 1
        rec = loaded.dps_records[0]
        assert rec.total_damage == 3000
        assert rec.delta_damage == 2000  # 3000 - 1000
        assert rec.dps == 2000.0  # 2000 / 1.0s

    def test_per_character_recomputes(self, tmp_path):
        csv_content = (
            "timestamp_sec,total_damage,delta_damage,dps,"
            "胡桃_total_damage,胡桃_delta_damage,胡桃_dps,胡桃_pct\n"
            "1.0,1000,,,800,,,\n"
            "2.0,3000,,,2400,,,\n"
        )
        csv_file = tmp_path / "in.csv"
        csv_file.write_text(csv_content, encoding="utf-8")
        loaded = read_csv(csv_file, dps_interval=1)
        assert loaded.pattern == RegionPattern.PER_CHARACTER
        assert loaded.party == ["胡桃"]
        assert len(loaded.dps_records) == 1
        rec = loaded.dps_records[0]
        assert rec.total_damage == 3000
        assert rec.delta_damage == 2000
        assert rec.characters[0].name == "胡桃"
        assert rec.characters[0].damage == 2400

    def test_missing_total_damage_skipped(self, tmp_path):
        """Rows with empty total_damage are treated as OCR failures."""
        csv_content = (
            "timestamp_sec,total_damage,delta_damage,dps\n"
            "1.0,1000,,\n"
            "2.0,,,\n"
            "3.0,4000,,\n"
        )
        csv_file = tmp_path / "in.csv"
        csv_file.write_text(csv_content, encoding="utf-8")
        loaded = read_csv(csv_file, dps_interval=1)
        # compute_dps skips the None row, delta = 4000-1000 over 2s
        assert len(loaded.dps_records) == 1
        assert loaded.dps_records[0].delta_damage == 3000
        assert loaded.dps_records[0].dps == 1500.0

    def test_dps_interval_passed_through(self, tmp_path):
        csv_content = (
            "timestamp_sec,total_damage,delta_damage,dps\n"
            "1.0,100,,\n"
            "2.0,200,,\n"
        )
        csv_file = tmp_path / "in.csv"
        csv_file.write_text(csv_content, encoding="utf-8")
        loaded = read_csv(csv_file, dps_interval=120)
        assert loaded.dps_interval == 120

    def test_hand_edited_csv_recomputes(self, tmp_path):
        """User fixes total_damage; DPS is recomputed, not read from CSV."""
        csv_content = (
            "timestamp_sec,total_damage,delta_damage,dps,"
            "胡桃_total_damage,胡桃_delta_damage,胡桃_dps,胡桃_pct\n"
            "1.0,1000,9999,9999.00,1000,,9999.00,100.0\n"
            "2.0,6000,9999,9999.00,3600,,9999.00,60.0\n"
        )
        csv_file = tmp_path / "edited.csv"
        csv_file.write_text(csv_content, encoding="utf-8")
        loaded = read_csv(csv_file, dps_interval=1)
        assert loaded.pattern == RegionPattern.PER_CHARACTER
        assert loaded.party == ["胡桃"]
        # DPS is recomputed from total_damage, not the 9999 in CSV
        rec = loaded.dps_records[0]
        assert rec.delta_damage == 5000  # 6000 - 1000
        assert rec.dps == 5000.0  # 5000 / 1.0s
        assert rec.characters[0].damage == 3600

    def test_round_trip_preserves_master_data(self, tmp_path):
        """write_csv → read_csv round-trip preserves cumulative damage."""
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
        out = tmp_path / "rt.csv"
        write_csv(original, out)
        loaded = read_csv(out, dps_interval=1)
        # Only one DPS record from one frame → no consecutive pair → no DPS
        # But the frame_records should contain the master data
        assert loaded.pattern == RegionPattern.PER_CHARACTER
        assert loaded.party == ["胡桃", "鍾離"]
        assert len(loaded.frame_records) == 1
        assert loaded.frame_records[0].total_damage == 1000
        assert loaded.frame_records[0].characters[0].damage == 800
