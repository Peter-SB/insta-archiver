"""Unit tests for pipeline orchestration.

Covers _delete_video cleanup behaviour and process_job orchestration
for both Instagram and YouTube jobs.
Tests run without network access — instaloader, yt-dlp, and whisper are mocked.
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


class TestProcessYouTubeJob:
    """process_job routes YouTube jobs to the YouTube sub-pipeline."""

    def _make_job(self, save_video=False, **overrides):
        base = {
            "id": 1,
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "folder": "YouTube Archive",
            "save_video": int(save_video),
            "platform": "youtube",
        }
        base.update(overrides)
        return base

    @patch("app.pipeline.ytdlp_service.download_video")
    @patch("app.pipeline.whisper_service.transcribe_audio", return_value="transcript text")
    @patch("app.pipeline.markdown_service.write_youtube_note", return_value="YouTube Archive/Chan/Chan_id.md")
    @patch("app.pipeline.update_job_status")
    def test_successful_youtube_job(self, mock_status, mock_write, mock_transcribe, mock_download):
        from app.services.ytdlp_service import VideoData
        mock_download.return_value = VideoData(
            video_id="dQw4w9WgXcQ",
            channel="RickAstley",
            title="Never Gonna Give You Up",
            upload_date="19871027",
            view_count=1_000_000,
            like_count=50_000,
            channel_followers=500_000,
            description="Official video",
            media_path="/tmp/vid.m4a",
        )
        from app.pipeline import process_job
        process_job(self._make_job(), MagicMock())

        mock_download.assert_called_once()
        mock_transcribe.assert_called_once()
        mock_write.assert_called_once()
        final_call = mock_status.call_args_list[-1]
        assert final_call[0][1] == "successful"

    @patch("app.pipeline.ytdlp_service.download_video")
    @patch("app.pipeline.whisper_service.transcribe_audio", return_value="")
    @patch("app.pipeline.markdown_service.write_youtube_note", return_value="note.md")
    @patch("app.pipeline.update_job_status")
    def test_youtube_job_skips_transcription_when_no_media(self, mock_status, mock_write, mock_transcribe, mock_download):
        from app.services.ytdlp_service import VideoData
        mock_download.return_value = VideoData(
            video_id="dQw4w9WgXcQ",
            channel="Chan",
            title="title",
            upload_date="",
            view_count=None,
            like_count=None,
            channel_followers=None,
            description="",
            media_path=None,
        )
        from app.pipeline import process_job
        process_job(self._make_job(), MagicMock())

        mock_transcribe.assert_not_called()
        mock_write.assert_called_once()

    @patch("app.pipeline.ytdlp_service.download_video", side_effect=RuntimeError("network error"))
    @patch("app.pipeline.update_job_status")
    def test_youtube_job_marks_failed_on_download_error(self, mock_status, mock_download):
        from app.pipeline import process_job
        process_job(self._make_job(), MagicMock())

        final_call = mock_status.call_args_list[-1]
        assert final_call[0][1] == "failed"
        assert "network error" in final_call[1].get("error_message", "")

    @patch("app.pipeline.ytdlp_service.download_video")
    @patch("app.pipeline.whisper_service.transcribe_audio", return_value="transcript")
    @patch("app.pipeline.markdown_service.write_youtube_note", return_value="note.md")
    @patch("app.pipeline.update_job_status")
    @patch("app.pipeline._delete_video")
    def test_youtube_job_deletes_media_when_save_video_false(self, mock_delete, mock_status, mock_write, mock_transcribe, mock_download):
        from app.services.ytdlp_service import VideoData
        mock_download.return_value = VideoData(
            video_id="abc",
            channel="Chan",
            title="t",
            upload_date="",
            view_count=None,
            like_count=None,
            channel_followers=None,
            description="",
            media_path="/tmp/vid.m4a",
        )
        from app.pipeline import process_job
        process_job(self._make_job(save_video=False), MagicMock())
        mock_delete.assert_called_once_with("/tmp/vid.m4a")

    @patch("app.pipeline.ytdlp_service.download_video")
    @patch("app.pipeline.whisper_service.transcribe_audio", return_value="transcript")
    @patch("app.pipeline.markdown_service.write_youtube_note", return_value="note.md")
    @patch("app.pipeline.update_job_status")
    @patch("app.pipeline._delete_video")
    def test_youtube_job_keeps_media_when_save_video_true(self, mock_delete, mock_status, mock_write, mock_transcribe, mock_download):
        from app.services.ytdlp_service import VideoData
        mock_download.return_value = VideoData(
            video_id="abc",
            channel="Chan",
            title="t",
            upload_date="",
            view_count=None,
            like_count=None,
            channel_followers=None,
            description="",
            media_path="/tmp/vid.mp4",
        )
        from app.pipeline import process_job
        process_job(self._make_job(save_video=True), MagicMock())
        mock_delete.assert_not_called()
