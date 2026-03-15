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

# Region of interest (ROI) coordinates — placeholder values (require measurement).
# Format: {"x1": int, "y1": int, "x2": int, "y2": int}
#
# Pattern 1: Only party total damage is displayed.
# Pattern 2: Both individual damage and party total damage are displayed,
#             together with the character name.
REGIONS: dict[str, dict[str, dict[str, int]]] = {
    "pattern_1": {
        "party_damage": {"x1": 0, "y1": 0, "x2": 0, "y2": 0},  # TODO: measure
    },
    "pattern_2": {
        "party_damage":      {"x1": 0, "y1": 0, "x2": 0, "y2": 0},  # TODO: measure
        "individual_damage": {"x1": 0, "y1": 0, "x2": 0, "y2": 0},  # TODO: measure
        "character_name":    {"x1": 0, "y1": 0, "x2": 0, "y2": 0},  # TODO: measure
    },
}

# Minimum pixel area for a region to be considered valid (non-placeholder).
MIN_REGION_AREA = 1
