"""orchestrator — coordinate the full extraction pipeline."""
from __future__ import annotations

import logging
from pathlib import Path

import cv2

from genshin_damage_track.config import DEFAULT_DPS_INTERVAL, DEFAULT_SAMPLE_RATE, REGIONS
from genshin_damage_track.detector import detect_pattern
from genshin_damage_track.models import (
    CharacterDamage,
    DpsRecord,
    ExtractionResult,
    FrameRecord,
    RegionPattern,
)
from genshin_damage_track.pipeline.cropper import crop_region_of_interest
from genshin_damage_track.pipeline.parser import parse_character_entries, parse_to_numeric
from genshin_damage_track.pipeline.recognizer import OCREngine
from genshin_damage_track.pipeline.sampler import sample_frames

logger = logging.getLogger(__name__)


def run_pipeline(
    video_path: str | Path,
    sample_rate: float = DEFAULT_SAMPLE_RATE,
    dps_interval: int = DEFAULT_DPS_INTERVAL,
    engine: OCREngine | None = None,
    save_crops_dir: str | Path | None = None,
) -> ExtractionResult:
    """Execute the full damage-extraction pipeline on *video_path*.

    Parameters
    ----------
    video_path:
        Path to the FHD video file.
    sample_rate:
        Frames per second to process.
    dps_interval:
        Number of sampled frames for the DPS moving-average window.
        At the default of 60 with a 60 fps video sampled at 60 fps this
        equals a 1-second window.
    engine:
        Optional pre-initialised :class:`OCREngine`.  A new instance is
        created when not provided.
    save_crops_dir:
        When provided, cropped ROI images are saved to this directory for
        visual debugging.  The directory is created if it does not exist.

    Returns
    -------
    ExtractionResult
        Contains the detected :class:`RegionPattern`, the raw
        :class:`FrameRecord` list, and the computed :class:`DpsRecord` list.
    """
    path = Path(video_path)
    if engine is None:
        engine = OCREngine()

    # Prepare crop-saving directory
    crops_dir: Path | None = None
    if save_crops_dir is not None:
        crops_dir = Path(save_crops_dir)
        crops_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Saving cropped ROI images to %s", crops_dir)

    # --- Phase 1: detect the active pattern --------------------------------
    sampled = list(sample_frames(path, sample_rate=sample_rate))
    logger.info("Sampled %d frames from %s", len(sampled), path)
    frame_iter = (sf.image for sf in sampled)
    pattern = detect_pattern(frame_iter, engine=engine)

    # Default to PATTERN_1 when auto-detection fails (no numeric region found)
    if pattern is None:
        logger.warning("Auto-detection failed; defaulting to PATTERN_1")
        pattern = RegionPattern.PATTERN_1
    else:
        logger.info("Using pattern: %s", pattern.value)

    # --- Phase 2: extract per-frame cumulative records ---------------------
    frame_records: list[FrameRecord] = []
    valid_ocr_count = 0

    for idx, sampled_frame in enumerate(sampled):
        record = _extract_frame_record(
            sampled_frame.timestamp_sec, sampled_frame.image, pattern, engine,
            crops_dir=crops_dir, frame_index=idx,
        )
        frame_records.append(record)
        if record.total_damage is not None:
            valid_ocr_count += 1

    logger.info(
        "Extraction complete: %d/%d frames yielded valid total_damage",
        valid_ocr_count, len(frame_records),
    )

    # --- Phase 3: compute DPS from cumulative-damage deltas ----------------
    dps_records = compute_dps(frame_records, dps_interval)
    logger.info("Computed %d DPS records (interval=%d)", len(dps_records), dps_interval)

    return ExtractionResult(
        pattern=pattern,
        frame_records=frame_records,
        dps_records=dps_records,
        source_file=str(path),
        fps_sample_rate=sample_rate,
        dps_interval=dps_interval,
    )


def _extract_frame_record(
    timestamp_sec: float,
    frame,
    pattern: RegionPattern,
    engine: OCREngine,
    *,
    crops_dir: Path | None = None,
    frame_index: int = 0,
) -> FrameRecord:
    """Extract a single :class:`FrameRecord` from one sampled frame."""
    total_damage: int | None = None
    characters: list[CharacterDamage] = []

    if pattern == RegionPattern.PATTERN_1:
        bbox = REGIONS["pattern_1"]["total_damage"]
        cropped = crop_region_of_interest(frame, bbox)
        if crops_dir is not None and cropped.size > 0:
            cv2.imwrite(
                str(crops_dir / f"frame_{frame_index:04d}_total.png"), cropped,
            )
        text = engine.read(cropped)
        total_damage = parse_to_numeric(text)
        logger.debug(
            "Frame t=%.3fs [P1]: OCR=%r → total_damage=%s",
            timestamp_sec, text, total_damage,
        )

    elif pattern == RegionPattern.PATTERN_2:
        # Total cumulative damage
        total_bbox = REGIONS["pattern_2"]["total_damage"]
        total_crop = crop_region_of_interest(frame, total_bbox)
        if crops_dir is not None and total_crop.size > 0:
            cv2.imwrite(
                str(crops_dir / f"frame_{frame_index:04d}_total.png"), total_crop,
            )
        total_text = engine.read(total_crop)
        total_damage = parse_to_numeric(total_text)
        logger.debug(
            "Frame t=%.3fs [P2]: OCR=%r → total_damage=%s",
            timestamp_sec, total_text, total_damage,
        )

        # Character list (up to 4 entries)
        char_bbox = REGIONS["pattern_2"]["character_list"]
        char_crop = crop_region_of_interest(frame, char_bbox)
        if crops_dir is not None and char_crop.size > 0:
            cv2.imwrite(
                str(crops_dir / f"frame_{frame_index:04d}_chars.png"), char_crop,
            )
        char_text = engine.read(char_crop)
        for entry in parse_character_entries(char_text):
            characters.append(
                CharacterDamage(
                    name=entry.name,
                    damage=entry.damage,
                    percentage=entry.percentage,
                )
            )
        if characters:
            logger.debug(
                "Frame t=%.3fs [P2]: %d character entries parsed",
                timestamp_sec, len(characters),
            )

    return FrameRecord(
        timestamp_sec=timestamp_sec,
        total_damage=total_damage,
        characters=characters,
    )


def compute_dps(
    frame_records: list[FrameRecord],
    dps_interval: int = DEFAULT_DPS_INTERVAL,
) -> list[DpsRecord]:
    """Compute DPS records from frame-level cumulative damage readings.

    For each pair of consecutive frames where OCR returned a valid
    ``total_damage``, the delta (current − previous) is divided by the
    elapsed time to produce an instantaneous DPS value.  A simple
    moving-average over *dps_interval* entries is then applied.

    Parameters
    ----------
    frame_records:
        Ordered list of per-frame cumulative damage readings.
    dps_interval:
        Window size (in number of instantaneous DPS samples) for the
        moving average.

    Returns
    -------
    list[DpsRecord]
        One entry per consecutive-pair with valid readings.
    """
    # Build instantaneous DPS entries from consecutive valid readings
    raw: list[DpsRecord] = []
    prev_ts: float | None = None
    prev_dmg: int | None = None

    for rec in frame_records:
        if rec.total_damage is not None:
            if prev_ts is not None and prev_dmg is not None:
                dt = rec.timestamp_sec - prev_ts
                delta = rec.total_damage - prev_dmg
                if dt > 0:
                    dps = delta / dt
                    raw.append(DpsRecord(
                        timestamp_sec=rec.timestamp_sec,
                        dps=dps,
                        delta_damage=delta,
                        total_damage=rec.total_damage,
                    ))
            prev_ts = rec.timestamp_sec
            prev_dmg = rec.total_damage

    if not raw or dps_interval <= 1:
        return raw

    # Apply moving average over the dps_interval window
    averaged: list[DpsRecord] = []
    for i, entry in enumerate(raw):
        window_start = max(0, i - dps_interval + 1)
        window = raw[window_start : i + 1]
        avg_dps = sum(r.dps for r in window if r.dps is not None) / len(window)
        averaged.append(DpsRecord(
            timestamp_sec=entry.timestamp_sec,
            dps=avg_dps,
            delta_damage=entry.delta_damage,
            total_damage=entry.total_damage,
        ))

    return averaged
