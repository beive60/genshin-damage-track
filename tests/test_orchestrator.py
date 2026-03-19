"""Tests for orchestrator.py — DPS computation logic."""
from __future__ import annotations

import pytest

from genshin_damage_track.models import CharacterDamage, FrameRecord
from genshin_damage_track.orchestrator import compute_dps


class TestComputeDps:
    def test_empty_records(self):
        assert compute_dps([]) == []

    def test_single_record_no_dps(self):
        records = [FrameRecord(timestamp_sec=0.0, total_damage=100)]
        result = compute_dps(records)
        assert result == []

    def test_two_records_basic_dps(self):
        records = [
            FrameRecord(timestamp_sec=0.0, total_damage=0),
            FrameRecord(timestamp_sec=1.0, total_damage=1000),
        ]
        result = compute_dps(records, dps_interval=1)
        assert len(result) == 1
        assert result[0].timestamp_sec == 1.0
        assert result[0].dps == pytest.approx(1000.0)
        assert result[0].delta_damage == 1000
        assert result[0].total_damage == 1000

    def test_skips_none_frames(self):
        records = [
            FrameRecord(timestamp_sec=0.0, total_damage=0),
            FrameRecord(timestamp_sec=1.0, total_damage=None),
            FrameRecord(timestamp_sec=2.0, total_damage=2000),
        ]
        result = compute_dps(records, dps_interval=1)
        assert len(result) == 1
        assert result[0].timestamp_sec == 2.0
        # 2000 damage over 2 seconds = 1000 DPS
        assert result[0].dps == pytest.approx(1000.0)
        assert result[0].delta_damage == 2000

    def test_cumulative_delta_calculation(self):
        records = [
            FrameRecord(timestamp_sec=0.0, total_damage=1000),
            FrameRecord(timestamp_sec=1.0, total_damage=2500),
            FrameRecord(timestamp_sec=2.0, total_damage=5000),
        ]
        result = compute_dps(records, dps_interval=1)
        assert len(result) == 2
        assert result[0].dps == pytest.approx(1500.0)  # 2500 - 1000 = 1500 over 1s
        assert result[1].dps == pytest.approx(2500.0)  # 5000 - 2500 = 2500 over 1s

    def test_moving_average_window(self):
        records = [
            FrameRecord(timestamp_sec=0.0, total_damage=0),
            FrameRecord(timestamp_sec=1.0, total_damage=1000),
            FrameRecord(timestamp_sec=2.0, total_damage=3000),
            FrameRecord(timestamp_sec=3.0, total_damage=4000),
        ]
        # 3 instantaneous DPS values: 1000, 2000, 1000
        # With window=2: avg(1000)=1000, avg(1000,2000)=1500, avg(2000,1000)=1500
        result = compute_dps(records, dps_interval=2)
        assert len(result) == 3
        assert result[0].dps == pytest.approx(1000.0)
        assert result[1].dps == pytest.approx(1500.0)
        assert result[2].dps == pytest.approx(1500.0)

    def test_interval_1_no_averaging(self):
        records = [
            FrameRecord(timestamp_sec=0.0, total_damage=0),
            FrameRecord(timestamp_sec=1.0, total_damage=1000),
            FrameRecord(timestamp_sec=2.0, total_damage=3000),
        ]
        result = compute_dps(records, dps_interval=1)
        assert len(result) == 2
        assert result[0].dps == pytest.approx(1000.0)
        assert result[1].dps == pytest.approx(2000.0)

    def test_all_none_records(self):
        records = [
            FrameRecord(timestamp_sec=0.0, total_damage=None),
            FrameRecord(timestamp_sec=1.0, total_damage=None),
        ]
        result = compute_dps(records)
        assert result == []

    def test_zero_time_delta(self):
        records = [
            FrameRecord(timestamp_sec=0.0, total_damage=0),
            FrameRecord(timestamp_sec=0.0, total_damage=1000),
        ]
        result = compute_dps(records, dps_interval=1)
        # Zero time delta records are skipped (no meaningful DPS)
        assert result == []

    def test_characters_propagated_to_dps_records(self):
        chars = [CharacterDamage(slot=0, name="胡桃", damage=800)]
        records = [
            FrameRecord(timestamp_sec=0.0, total_damage=0),
            FrameRecord(timestamp_sec=1.0, total_damage=1000, characters=chars),
        ]
        result = compute_dps(records, dps_interval=1)
        assert len(result) == 1
        assert len(result[0].characters) == 1
        assert result[0].characters[0].name == "胡桃"
        assert result[0].characters[0].damage == 800

    def test_characters_propagated_through_moving_average(self):
        chars_a = [CharacterDamage(slot=0, name="胡桃", damage=500)]
        chars_b = [
            CharacterDamage(slot=0, name="胡桃", damage=1200),
            CharacterDamage(slot=1, name="鍾離", damage=800),
        ]
        records = [
            FrameRecord(timestamp_sec=0.0, total_damage=0),
            FrameRecord(timestamp_sec=1.0, total_damage=1000, characters=chars_a),
            FrameRecord(timestamp_sec=2.0, total_damage=3000, characters=chars_b),
        ]
        result = compute_dps(records, dps_interval=2)
        assert len(result) == 2
        # Each DPS record keeps the characters from its source frame
        assert result[0].characters == chars_a
        assert result[1].characters == chars_b

    def test_default_interval_returns_instantaneous_dps(self):
        records = [
            FrameRecord(timestamp_sec=0.0, total_damage=0),
            FrameRecord(timestamp_sec=1.0, total_damage=1000),
            FrameRecord(timestamp_sec=2.0, total_damage=3000),
            FrameRecord(timestamp_sec=3.0, total_damage=4000),
        ]
        # dps_interval=1 (default) returns raw instantaneous DPS
        result = compute_dps(records)
        assert len(result) == 3
        assert result[0].dps == pytest.approx(1000.0)
        assert result[1].dps == pytest.approx(2000.0)
        assert result[2].dps == pytest.approx(1000.0)
