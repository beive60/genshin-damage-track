"""Data models for damage tracking."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RegionPattern(Enum):
    """Detected region pattern type.

    Both patterns display cumulative total damage.

    PATTERN_1 — total damage only.
    PATTERN_2 — total damage **plus** up to 4 individual character entries
                (name, damage, percentage).
    """

    PATTERN_1 = "total_only"
    PATTERN_2 = "total_and_characters"


@dataclass
class CharacterDamage:
    """Individual character damage entry (Pattern 2 only).

    Represents one line such as ``太郎: 12345 (67%)``.
    """

    name: str
    damage: int
    percentage: float  # e.g. 67.0 for "67%"


@dataclass
class FrameRecord:
    """Raw OCR data extracted from a single sampled frame.

    ``total_damage`` is the **cumulative** total shown on screen.
    """

    timestamp_sec: float
    total_damage: int | None
    characters: list[CharacterDamage] = field(default_factory=list)


@dataclass
class DpsRecord:
    """Computed DPS (damage per second) for a time point."""

    timestamp_sec: float
    dps: float | None
    delta_damage: int | None  # damage dealt since previous successful read
    total_damage: int | None  # cumulative total at this point


@dataclass
class ExtractionResult:
    """Full pipeline extraction result."""

    pattern: RegionPattern
    frame_records: list[FrameRecord] = field(default_factory=list)
    dps_records: list[DpsRecord] = field(default_factory=list)
    source_file: str = ""
    fps_sample_rate: float = 1.0
    dps_interval: int = 60
