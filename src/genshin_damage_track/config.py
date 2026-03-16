"""Constants and configuration for genshin-damage-track.

All coordinates are defined for FHD (1920x1080) resolution.
ROI coordinates must be measured from actual game screenshots.
"""
from __future__ import annotations

# Target video resolution
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 60

# Default sampling rate (frames per second to process)
DEFAULT_SAMPLE_RATE: float = 1.0

# Default DPS averaging interval in frames.
# At 60 fps this equals a 1-second window.
DEFAULT_DPS_INTERVAL: int = 60

# Region of interest (ROI) coordinates — placeholder values (require measurement).
# Format: {"x1": int, "y1": int, "x2": int, "y2": int}
#
# Pattern 1: Only cumulative total damage is displayed.
# Pattern 2: Cumulative total damage is displayed together with up to 4
#             individual character entries (name, damage, percentage).
REGIONS: dict[str, dict[str, dict[str, int]]] = {
    "pattern_1": {
        "total_damage": {"x1": 153, "y1": 366, "x2": 333, "y2": 395},
    },
    "pattern_2": {
        "total_damage":     {"x1": 159, "y1": 243, "x2": 328, "y2": 274},
        "character_list":   {"x1": 45, "y1": 293, "x2": 331, "y2": 395},
    },
}

# Minimum pixel area for a region to be considered valid (non-placeholder).
MIN_REGION_AREA = 1
