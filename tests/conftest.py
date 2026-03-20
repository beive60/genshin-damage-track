"""Shared fixtures for the test suite."""
from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture()
def blank_frame() -> np.ndarray:
    """Return a solid black FHD BGR frame."""
    return np.zeros((1080, 1920, 3), dtype=np.uint8)


@pytest.fixture()
def white_frame() -> np.ndarray:
    """Return a solid white FHD BGR frame."""
    return np.full((1080, 1920, 3), 255, dtype=np.uint8)


@pytest.fixture()
def sample_bbox() -> dict[str, int]:
    """A valid 200×100 bounding box near the centre of FHD."""
    return {"x1": 860, "y1": 490, "x2": 1060, "y2": 590}
