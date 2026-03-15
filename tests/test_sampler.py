"""Tests for pipeline/sampler.py."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from genshin_damage_track.pipeline.sampler import SampledFrame, sample_frames


def _make_mock_cap(frame_count: int = 10, fps: float = 10.0):
    """Return a mock cv2.VideoCapture that yields *frame_count* black frames."""
    frames = [np.zeros((1080, 1920, 3), dtype=np.uint8)] * frame_count
    read_calls = [(True, f) for f in frames] + [(False, None)]

    cap = MagicMock()
    cap.isOpened.return_value = True
    cap.get.return_value = fps
    cap.read.side_effect = read_calls
    return cap


class TestSampleFrames:
    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            list(sample_frames(tmp_path / "nonexistent.mp4"))

    def test_raises_when_cap_fails_to_open(self, tmp_path):
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        cap = MagicMock()
        cap.isOpened.return_value = False

        with patch("genshin_damage_track.pipeline.sampler.cv2.VideoCapture", return_value=cap):
            with pytest.raises(RuntimeError, match="Cannot open video file"):
                list(sample_frames(video_path))

    def test_sample_rate_1fps_from_10fps_video(self, tmp_path):
        """1 fps from a 10 fps source → every 10th frame = 1 frame per second."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        cap = _make_mock_cap(frame_count=20, fps=10.0)
        with patch("genshin_damage_track.pipeline.sampler.cv2.VideoCapture", return_value=cap):
            result = list(sample_frames(video_path, sample_rate=1.0))

        # 20 frames at 10fps = 2 seconds → expect 2 sampled frames (frame 0, frame 10)
        assert len(result) == 2

    def test_sample_rate_equals_source_fps(self, tmp_path):
        """sample_rate == native fps → every frame is returned."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        frame_count = 5
        cap = _make_mock_cap(frame_count=frame_count, fps=5.0)
        with patch("genshin_damage_track.pipeline.sampler.cv2.VideoCapture", return_value=cap):
            result = list(sample_frames(video_path, sample_rate=5.0))

        assert len(result) == frame_count

    def test_returns_sampled_frame_namedtuple(self, tmp_path):
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        cap = _make_mock_cap(frame_count=10, fps=10.0)
        with patch("genshin_damage_track.pipeline.sampler.cv2.VideoCapture", return_value=cap):
            result = list(sample_frames(video_path, sample_rate=1.0))

        for sf in result:
            assert isinstance(sf, SampledFrame)
            assert isinstance(sf.image, np.ndarray)
            assert isinstance(sf.timestamp_sec, float)

    def test_timestamps_are_correct(self, tmp_path):
        """Timestamps should be multiples of 1/fps."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        cap = _make_mock_cap(frame_count=30, fps=10.0)
        with patch("genshin_damage_track.pipeline.sampler.cv2.VideoCapture", return_value=cap):
            result = list(sample_frames(video_path, sample_rate=1.0))

        # 30 frames at 10fps = 3 seconds → frames at t=0.0, 1.0, 2.0
        assert [sf.timestamp_sec for sf in result] == pytest.approx([0.0, 1.0, 2.0])

    def test_cap_is_released_after_iteration(self, tmp_path):
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        cap = _make_mock_cap(frame_count=5, fps=5.0)
        with patch("genshin_damage_track.pipeline.sampler.cv2.VideoCapture", return_value=cap):
            list(sample_frames(video_path, sample_rate=1.0))

        cap.release.assert_called_once()
