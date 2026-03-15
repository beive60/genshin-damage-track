"""detector — automatically detect which region pattern is active.

The detection strategy:
1. Crop both pattern regions from the first few frames.
2. Run OCR on each cropped area.
3. Whichever pattern yields a valid numeric result first is used for the
   remainder of the video.
"""
from __future__ import annotations

from collections.abc import Iterator

import numpy as np

from genshin_damage_track.config import REGIONS
from genshin_damage_track.models import RegionPattern
from genshin_damage_track.pipeline.cropper import crop_region_of_interest
from genshin_damage_track.pipeline.parser import parse_to_numeric
from genshin_damage_track.pipeline.recognizer import OCREngine


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

    for i, frame in enumerate(frames):
        if i >= max_probe_frames:
            break

        if p1_valid_region:
            crop_p1 = crop_region_of_interest(frame, p1_bbox)
            text_p1 = engine.read(crop_p1)
            if parse_to_numeric(text_p1) is not None:
                return RegionPattern.PATTERN_1

        if p2_valid_region:
            crop_p2 = crop_region_of_interest(frame, p2_bbox)
            text_p2 = engine.read(crop_p2)
            if parse_to_numeric(text_p2) is not None:
                return RegionPattern.PATTERN_2

    return None
