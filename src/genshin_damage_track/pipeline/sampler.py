"""sample_frames — extract frames from a video at a given sample rate."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np

from genshin_damage_track.config import DEFAULT_SAMPLE_RATE, VIDEO_FPS


class SampledFrame(NamedTuple):
    """A frame sampled from the video together with its timestamp."""

    timestamp_sec: float
    image: np.ndarray


def sample_frames(
    video_path: str | Path,
    sample_rate: float = DEFAULT_SAMPLE_RATE,
) -> Iterator[SampledFrame]:
    """Yield frames from *video_path* at *sample_rate* frames per second.

    Parameters
    ----------
    video_path:
        Path to the video file.
    sample_rate:
        Number of frames to extract per second of video (e.g. ``1.0``).

    Yields
    ------
    SampledFrame
        Named tuple containing the timestamp in seconds and the BGR image array.

    Raises
    ------
    FileNotFoundError
        If *video_path* does not exist.
    RuntimeError
        If the video cannot be opened by OpenCV.
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {path}")

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video file: {path}")

    try:
        native_fps: float = cap.get(cv2.CAP_PROP_FPS) or VIDEO_FPS
        frame_interval: int = max(1, round(native_fps / sample_rate))
        frame_index = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_index % frame_interval == 0:
                timestamp_sec = frame_index / native_fps
                yield SampledFrame(timestamp_sec=timestamp_sec, image=frame)

            frame_index += 1
    finally:
        cap.release()
