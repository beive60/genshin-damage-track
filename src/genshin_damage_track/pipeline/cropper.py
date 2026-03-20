"""crop_region_of_interest — crop a bounding box from a frame."""
from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

# Bounding-box type alias: {"x1", "y1", "x2", "y2"}
BoundingBox = dict[str, int]


def split_bbox_rows(bbox: BoundingBox, n: int) -> list[BoundingBox]:
    """Divide *bbox* into *n* equal-height horizontal strips.

    Parameters
    ----------
    bbox:
        Bounding box to split.
    n:
        Number of rows (must be >= 1).

    Returns
    -------
    list[BoundingBox]
        *n* bounding boxes stacked vertically.
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")

    x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
    total_h = y2 - y1
    row_h = total_h / n

    rows: list[BoundingBox] = []
    for i in range(n):
        ry1 = y1 + round(row_h * i)
        ry2 = y1 + round(row_h * (i + 1))
        rows.append({"x1": x1, "y1": ry1, "x2": x2, "y2": ry2})
    return rows


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
        Dictionary with keys ``x1``, ``y1``, ``x2``, ``y2`` (exclusive upper bounds,
        following NumPy slicing convention: ``frame[y1:y2, x1:x2]``).

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
        logger.debug("Zero-area bbox (%d,%d)-(%d,%d) -> empty crop", x1, y1, x2, y2)
        return np.empty((0, 0, frame.shape[2] if frame.ndim == 3 else 0), dtype=frame.dtype)

    h, w = frame.shape[:2]
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(w, x2)
    y2 = min(h, y2)

    cropped = frame[y1:y2, x1:x2].copy()
    logger.debug(
        "Crop (%d,%d)-(%d,%d) from %dx%d frame -> %dx%d region",
        bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"],
        w, h, cropped.shape[1], cropped.shape[0],
    )
    return cropped
