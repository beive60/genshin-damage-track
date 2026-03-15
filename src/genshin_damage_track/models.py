"""Data models for damage tracking."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RegionPattern(Enum):
    """Detected region pattern type."""

    PATTERN_1 = "party_only"
    PATTERN_2 = "individual_and_party"


@dataclass
class DamageRecord:
    """Damage data extracted from a single frame."""

    timestamp_sec: float
    party_damage: int | None
    individual_damage: int | None
    character_name: str | None  # Only populated for PATTERN_2


@dataclass
class ExtractionResult:
    """Full pipeline extraction result."""

    pattern: RegionPattern
    records: list[DamageRecord] = field(default_factory=list)
    source_file: str = ""
    fps_sample_rate: float = 1.0
