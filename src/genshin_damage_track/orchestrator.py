"""orchestrator — coordinate the full extraction pipeline."""
from __future__ import annotations

from pathlib import Path

from genshin_damage_track.config import DEFAULT_SAMPLE_RATE, REGIONS
from genshin_damage_track.detector import detect_pattern
from genshin_damage_track.models import DamageRecord, ExtractionResult, RegionPattern
from genshin_damage_track.pipeline.cropper import crop_region_of_interest
from genshin_damage_track.pipeline.parser import parse_character_name, parse_to_numeric
from genshin_damage_track.pipeline.recognizer import OCREngine
from genshin_damage_track.pipeline.sampler import sample_frames


def run_pipeline(
    video_path: str | Path,
    sample_rate: float = DEFAULT_SAMPLE_RATE,
    engine: OCREngine | None = None,
) -> ExtractionResult:
    """Execute the full damage-extraction pipeline on *video_path*.

    Parameters
    ----------
    video_path:
        Path to the FHD video file.
    sample_rate:
        Frames per second to process.
    engine:
        Optional pre-initialised :class:`OCREngine`.  A new instance is
        created when not provided.

    Returns
    -------
    ExtractionResult
        Contains the detected :class:`RegionPattern` and the list of
        :class:`DamageRecord` instances — one per sampled frame.
    """
    path = Path(video_path)
    if engine is None:
        engine = OCREngine()

    # --- Phase 1: detect the active pattern --------------------------------
    sampled = list(sample_frames(path, sample_rate=sample_rate))
    frame_iter = (sf.image for sf in sampled)
    pattern = detect_pattern(frame_iter, engine=engine)

    # Default to PATTERN_1 when auto-detection fails (no numeric region found)
    if pattern is None:
        pattern = RegionPattern.PATTERN_1

    # --- Phase 2: extract damage records -----------------------------------
    records: list[DamageRecord] = []

    for sampled_frame in sampled:
        record = _extract_record(sampled_frame.timestamp_sec, sampled_frame.image, pattern, engine)
        records.append(record)

    return ExtractionResult(
        pattern=pattern,
        records=records,
        source_file=str(path),
        fps_sample_rate=sample_rate,
    )


def _extract_record(
    timestamp_sec: float,
    frame,
    pattern: RegionPattern,
    engine: OCREngine,
) -> DamageRecord:
    """Extract a single :class:`DamageRecord` from one sampled frame."""
    party_damage: int | None = None
    individual_damage: int | None = None
    character_name: str | None = None

    if pattern == RegionPattern.PATTERN_1:
        bbox = REGIONS["pattern_1"]["party_damage"]
        cropped = crop_region_of_interest(frame, bbox)
        text = engine.read(cropped)
        party_damage = parse_to_numeric(text)

    elif pattern == RegionPattern.PATTERN_2:
        # Party damage
        party_bbox = REGIONS["pattern_2"]["party_damage"]
        party_crop = crop_region_of_interest(frame, party_bbox)
        party_text = engine.read(party_crop)
        party_damage = parse_to_numeric(party_text)

        # Individual damage
        ind_bbox = REGIONS["pattern_2"]["individual_damage"]
        ind_crop = crop_region_of_interest(frame, ind_bbox)
        ind_text = engine.read(ind_crop)
        individual_damage = parse_to_numeric(ind_text)

        # Character name
        name_bbox = REGIONS["pattern_2"]["character_name"]
        name_crop = crop_region_of_interest(frame, name_bbox)
        name_text = engine.read(name_crop)
        character_name = parse_character_name(name_text)

    return DamageRecord(
        timestamp_sec=timestamp_sec,
        party_damage=party_damage,
        individual_damage=individual_damage,
        character_name=character_name,
    )
