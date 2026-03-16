"""detector — automatically detect which region pattern is active.

The detection strategy:
1. Crop both pattern regions from the first few frames.
2. Run OCR on each cropped area.
3. Whichever pattern yields a valid numeric result first is used for the
   remainder of the video.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator

import numpy as np

from genshin_damage_track.config import REGIONS
from genshin_damage_track.models import RegionPattern
from genshin_damage_track.pipeline.cropper import crop_region_of_interest
from genshin_damage_track.pipeline.parser import parse_to_numeric
from genshin_damage_track.pipeline.recognizer import OCREngine

logger = logging.getLogger(__name__)


def _is_valid_region(bbox: dict[str, int]) -> bool:
    """Return True when the bounding box has a non-zero area."""
    return (bbox["x2"] > bbox["x1"]) and (bbox["y2"] > bbox["y1"])


def detect_pattern(
    frames: Iterator[np.ndarray],
    engine: OCREngine | None = None,
    max_probe_frames: int = 30,
) -> RegionPattern | None:
    """Probe up to *max_probe_frames* frames to determine the active pattern.

    Both pattern regions are cropped and passed through OCR on each probed
    frame.  The first pattern that yields a valid numeric result is returned.

    Parameters
    ----------
    frames:
        Iterator of BGR image arrays (full-resolution frames).
    engine:
        Optional pre-initialised :class:`OCREngine`.
    max_probe_frames:
        Maximum number of frames to check before giving up.

    Returns
    -------
    RegionPattern | None
        The detected pattern, or ``None`` when no valid region is found within
        the probe window.
    """
    if engine is None:
        engine = OCREngine()

    p1_bbox = REGIONS["pattern_1"]["total_damage"]
    p2_bbox = REGIONS["pattern_2"]["total_damage"]

    p1_valid_region = _is_valid_region(p1_bbox)
    p2_valid_region = _is_valid_region(p2_bbox)

    logger.debug(
        "Pattern detection: p1_bbox=%s (valid=%s), p2_bbox=%s (valid=%s), max_probe=%d",
        p1_bbox, p1_valid_region, p2_bbox, p2_valid_region, max_probe_frames,
    )

    for i, frame in enumerate(frames):
        if i >= max_probe_frames:
            break

        logger.debug("Probing frame %d (shape=%s)", i, frame.shape)

        # Check PATTERN_2 first — it is the more specific pattern (total +
        # characters).  The two patterns place the total-damage region at
        # different Y coordinates, so checking pattern 1 first on a pattern 2
        # video may pick up character-entry text in the pattern 1 ROI and lock
        # in the wrong pattern for all subsequent frames.
        if p2_valid_region:
            crop_p2 = crop_region_of_interest(frame, p2_bbox)
            text_p2 = engine.read(crop_p2)
            value_p2 = parse_to_numeric(text_p2)
            logger.debug("  Pattern 2: OCR=%r -> parsed=%s", text_p2, value_p2)
            if value_p2 is not None:
                logger.info("Pattern detected: PATTERN_2 at frame %d (value=%d)", i, value_p2)
                return RegionPattern.PATTERN_2

        if p1_valid_region:
            crop_p1 = crop_region_of_interest(frame, p1_bbox)
            text_p1 = engine.read(crop_p1)
            value_p1 = parse_to_numeric(text_p1)
            logger.debug("  Pattern 1: OCR=%r -> parsed=%s", text_p1, value_p1)
            if value_p1 is not None:
                logger.info("Pattern detected: PATTERN_1 at frame %d (value=%d)", i, value_p1)
                return RegionPattern.PATTERN_1

    logger.warning("No pattern detected after %d probe frames", max_probe_frames)
    return None
