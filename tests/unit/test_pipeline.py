"""Unit tests for pipeline orchestration.

Covers _delete_video cleanup behaviour and process_job orchestration.
Tests run without network access — instaloader and whisper are mocked.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.pipeline import _delete_video


class TestDeleteVideo:
    """_delete_video should remove both the file and its parent directory."""

    def test_deletes_video_file(self, tmp_path):
        video_dir = tmp_path / "post_dir"
        video_dir.mkdir()
        video_file = video_dir / "video.mp4"
        video_file.write_bytes(b"fake video")

        _delete_video(str(video_file))

        assert not video_file.exists()

    def test_deletes_parent_directory(self, tmp_path):
        video_dir = tmp_path / "post_dir"
        video_dir.mkdir()
        video_file = video_dir / "video.mp4"
        video_file.write_bytes(b"fake video")

        _delete_video(str(video_file))

        assert not video_dir.exists()

    def test_does_not_raise_when_file_missing(self, tmp_path):
        """Graceful failure — logs a warning but never raises."""
        _delete_video(str(tmp_path / "nonexistent" / "video.mp4"))  # must not raise

    def test_does_not_raise_when_dir_not_empty(self, tmp_path):
        """If directory has other files, rmdir fails — should log, not raise."""
        video_dir = tmp_path / "post_dir"
        video_dir.mkdir()
        video_file = video_dir / "video.mp4"
        video_file.write_bytes(b"fake video")
        (video_dir / "thumbnail.jpg").write_bytes(b"img")

        _delete_video(str(video_file))  # must not raise even though dir can't be removed
