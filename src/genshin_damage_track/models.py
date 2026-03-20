"""Data models for damage tracking."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RegionPattern(Enum):
    """Region pattern type.

    Both patterns display cumulative total damage.

    TOTAL_ONLY — total damage only.
    PER_CHARACTER — total damage **plus** up to 4 individual character
                    cumulative damage values.
    """

    TOTAL_ONLY = "total-only"
    PER_CHARACTER = "per-character"


@dataclass
class CharacterDamage:
    """Individual character damage entry (Pattern 2 only).

    ``slot`` is the 0-based position in the on-screen list (0–3).
    ``name`` is assigned from the CLI ``--names`` option; defaults to
    ``"char_0"`` … ``"char_3"`` when not provided.
    """

    slot: int
    name: str
    damage: int


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
    characters: list[CharacterDamage] = field(default_factory=list)


@dataclass
class ExtractionResult:
    """Full pipeline extraction result."""

    pattern: RegionPattern
    frame_records: list[FrameRecord] = field(default_factory=list)
    dps_records: list[DpsRecord] = field(default_factory=list)
    party: list[str] = field(default_factory=list)
    source_file: str = ""
    fps_sample_rate: float = 1.0
    dps_interval: int = 1
