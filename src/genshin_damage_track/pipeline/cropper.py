"""crop_region_of_interest — crop a bounding box from a frame."""
from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

# Bounding-box type alias: {"x1", "y1", "x2", "y2"}
BoundingBox = dict[str, int]


def crop_region_of_interest(
    frame: np.ndarray,
    bbox: BoundingBox,
) -> np.ndarray:
    """Return the sub-image of *frame* defined by *bbox*.

    Parameters
    ----------
    frame:
        Full BGR image array (H × W × 3).
    bbox:
        Dictionary with keys ``x1``, ``y1``, ``x2``, ``y2`` (inclusive pixel
        coordinates in FHD space).

    Returns
    -------
    np.ndarray
        Cropped BGR image array.  If the bounding box has zero area (i.e. the
        coordinates are still placeholders) an empty array is returned.

    Raises
    ------
    ValueError
        If required keys are missing from *bbox*.
    """
    required_keys = {"x1", "y1", "x2", "y2"}
    if not required_keys.issubset(bbox):
        raise ValueError(f"bbox must contain keys {required_keys}, got {set(bbox)}")

    x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]

    if x2 <= x1 or y2 <= y1:
        logger.debug("Zero-area bbox (%d,%d)-(%d,%d) → empty crop", x1, y1, x2, y2)
        return np.empty((0, 0, frame.shape[2] if frame.ndim == 3 else 0), dtype=frame.dtype)

    h, w = frame.shape[:2]
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(w, x2)
    y2 = min(h, y2)

    cropped = frame[y1:y2, x1:x2].copy()
    logger.debug(
        "Crop (%d,%d)-(%d,%d) from %dx%d frame → %dx%d region",
        bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"],
        w, h, cropped.shape[1], cropped.shape[0],
    )
    return cropped
