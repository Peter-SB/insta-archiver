"""Unit tests for service modules.

Tests extract_shortcode, extract_video_id (pure functions), markdown rendering/writing,
and verifies outputs without hitting external services.
"""

import os

import pytest

from app.services.instaloader_service import extract_shortcode
from app.services.markdown_service import render_note, write_note, render_youtube_note, write_youtube_note
from app.services.ytdlp_service import extract_video_id


class TestExtractShortcode:
    """Tests for the URL → shortcode regex extraction."""

    def test_reel_url(self):
        assert extract_shortcode("https://www.instagram.com/reel/ABC123/") == "ABC123"

    def test_post_url(self):
        assert extract_shortcode("https://www.instagram.com/p/DEF456/") == "DEF456"

    def test_reels_url(self):
        assert extract_shortcode("https://www.instagram.com/reels/GHI789/") == "GHI789"

    def test_url_without_trailing_slash(self):
        assert extract_shortcode("https://instagram.com/reel/ABC123") == "ABC123"

    def test_url_with_query_params(self):
        assert extract_shortcode("https://instagram.com/reel/ABC123/?utm_source=ig") == "ABC123"

    def test_shortcode_with_hyphens_and_underscores(self):
        assert extract_shortcode("https://instagram.com/reel/A_B-C123/") == "A_B-C123"

    def test_invalid_url_raises_error(self):
        with pytest.raises(ValueError, match="Could not extract shortcode"):
            extract_shortcode("https://www.google.com/")

    def test_empty_url_raises_error(self):
        with pytest.raises(ValueError):
            extract_shortcode("")


class TestRenderNote:
    """Tests for Jinja2 markdown template rendering."""

    def _render(self, **overrides):
        defaults = dict(
            shortcode="ABC123",
            account_name="testuser",
            url="https://www.instagram.com/reel/ABC123/",
            description="A great post",
            transcript="Hello world",
            folder="Insta Archive",
            date="2025-01-01 00:00",
        )
        defaults.update(overrides)
        return render_note(**defaults)

    def test_contains_frontmatter(self):
        result = self._render()
        assert result.startswith("---")
        assert 'title: "testuser/ABC123"' in result

    def test_contains_description(self):
        result = self._render(description="My amazing trip")
        assert "My amazing trip" in result

    def test_contains_transcript(self):
        result = self._render(transcript="Spoken words here")
        assert "Spoken words here" in result

    def test_empty_transcript_shows_placeholder(self):
        result = self._render(transcript="")
        assert "No audio to transcribe" in result

    def test_empty_description_shows_placeholder(self):
        result = self._render(description="")
        assert "No description" in result

    def test_contains_url(self):
        result = self._render()
        assert "https://www.instagram.com/reel/ABC123/" in result


class TestWriteNote:
    """Tests for writing markdown notes to disk."""

    def test_creates_file_at_correct_path(self, tmp_path):
        relative = write_note(
            markdown_dir=str(tmp_path),
            folder="TestFolder",
            account_name="testuser",
            shortcode="ABC123",
            url="https://instagram.com/reel/ABC123/",
            description="description text",
            transcript="transcript text",
            date="2025-01-01",
        )
        assert relative == os.path.join("TestFolder", "testuser", "testuser_ABC123.md")

        full_path = tmp_path / "TestFolder" / "testuser" / "testuser_ABC123.md"
        assert full_path.exists()

    def test_file_contains_description_and_transcript(self, tmp_path):
        write_note(
            markdown_dir=str(tmp_path),
            folder="F",
            account_name="user",
            shortcode="SC",
            url="url",
            description="my description",
            transcript="my transcript",
            date="date",
        )
        content = (tmp_path / "F" / "user" / "user_SC.md").read_text()
        assert "my description" in content
        assert "my transcript" in content

    def test_creates_nested_directories(self, tmp_path):
        write_note(
            markdown_dir=str(tmp_path),
            folder="New Folder",
            account_name="acct",
            shortcode="SC",
            url="url",
            description="d",
            transcript="t",
            date="date",
        )
        assert (tmp_path / "New Folder" / "acct").is_dir()  # per-account subfolder


class TestWriteNoteDeduplication:
    """write_note should never overwrite an existing note.

    When the same post is submitted a second time the file is saved with a
    ' (2)' suffix.  A third submission becomes ' (3)', and so on.
    """

    def _write(self, tmp_path, shortcode="SC", **overrides):
        kwargs = dict(
            markdown_dir=str(tmp_path),
            folder="Folder",
            account_name="user",
            shortcode=shortcode,
            url="url",
            description="desc",
            transcript="trans",
            date="2025-01-01",
        )
        kwargs.update(overrides)
        return write_note(**kwargs)

    def test_first_write_has_no_suffix(self, tmp_path):
        relative = self._write(tmp_path)
        assert relative == os.path.join("Folder", "user", "user_SC.md")

    def test_second_write_gets_count_2(self, tmp_path):
        self._write(tmp_path)
        relative = self._write(tmp_path)
        assert relative == os.path.join("Folder", "user", "user_SC (2).md")

    def test_third_write_gets_count_3(self, tmp_path):
        self._write(tmp_path)
        self._write(tmp_path)
        relative = self._write(tmp_path)
        assert relative == os.path.join("Folder", "user", "user_SC (3).md")

    def test_both_files_exist_after_duplicate(self, tmp_path):
        self._write(tmp_path)
        self._write(tmp_path)
        assert (tmp_path / "Folder" / "user" / "user_SC.md").exists()
        assert (tmp_path / "Folder" / "user" / "user_SC (2).md").exists()

    def test_different_shortcodes_do_not_interfere(self, tmp_path):
        r1 = self._write(tmp_path, shortcode="AAA")
        r2 = self._write(tmp_path, shortcode="BBB")
        assert r1 == os.path.join("Folder", "user", "user_AAA.md")
        assert r2 == os.path.join("Folder", "user", "user_BBB.md")


class TestExtractVideoId:
    """Tests for the YouTube URL → video ID regex extraction."""

    def test_watch_url(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_watch_url_with_extra_params(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s") == "dQw4w9WgXcQ"

    def test_short_url_with_query(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ?si=abc123") == "dQw4w9WgXcQ"

    def test_invalid_url_raises_error(self):
        with pytest.raises(ValueError, match="Could not extract video ID"):
            extract_video_id("https://www.google.com/")

    def test_empty_url_raises_error(self):
        with pytest.raises(ValueError):
            extract_video_id("")

    def test_instagram_url_raises_error(self):
        with pytest.raises(ValueError):
            extract_video_id("https://www.instagram.com/reel/ABC123/")


class TestRenderYouTubeNote:
    """Tests for Jinja2 YouTube markdown template rendering."""

    def _render(self, **overrides):
        defaults = dict(
            video_id="dQw4w9WgXcQ",
            channel="RickAstleyVEVO",
            title="Rick Astley - Never Gonna Give You Up",
            upload_date="19871027",
            view_count=1_500_000_000,
            like_count=15_000_000,
            channel_followers=3_000_000,
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            description="The official music video",
            transcript="Never gonna give you up",
            folder="YouTube Archive",
            date="2025-01-01 00:00",
        )
        defaults.update(overrides)
        return render_youtube_note(**defaults)

    def test_contains_frontmatter(self):
        result = self._render()
        assert result.startswith("---")
        assert 'title: "RickAstleyVEVO/dQw4w9WgXcQ"' in result

    def test_contains_channel(self):
        result = self._render()
        assert "RickAstleyVEVO" in result

    def test_contains_title_text(self):
        result = self._render()
        assert "Rick Astley - Never Gonna Give You Up" in result

    def test_contains_upload_date(self):
        result = self._render()
        assert "19871027" in result

    def test_contains_view_count(self):
        result = self._render()
        assert "1,500,000,000" in result

    def test_contains_like_count(self):
        result = self._render()
        assert "15,000,000" in result

    def test_contains_subscriber_count(self):
        result = self._render()
        assert "3,000,000" in result

    def test_contains_description(self):
        result = self._render()
        assert "The official music video" in result

    def test_contains_transcript(self):
        result = self._render()
        assert "Never gonna give you up" in result

    def test_empty_transcript_shows_placeholder(self):
        result = self._render(transcript="")
        assert "No audio to transcribe" in result

    def test_empty_description_shows_placeholder(self):
        result = self._render(description="")
        assert "No description" in result

    def test_none_view_count_shows_tilde(self):
        result = self._render(view_count=None)
        assert "view_count: ~" in result

    def test_none_like_count_shows_tilde(self):
        result = self._render(like_count=None)
        assert "like_count: ~" in result

    def test_none_channel_followers_shows_tilde(self):
        result = self._render(channel_followers=None)
        assert "channel_followers: ~" in result


class TestWriteYouTubeNote:
    """Tests for writing YouTube markdown notes to disk."""

    def _write(self, tmp_path, **overrides):
        defaults = dict(
            markdown_dir=str(tmp_path),
            folder="YouTube Archive",
            channel="RickAstleyVEVO",
            video_id="dQw4w9WgXcQ",
            title="Never Gonna Give You Up",
            upload_date="19871027",
            view_count=1_000_000,
            like_count=50_000,
            channel_followers=500_000,
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            description="desc",
            transcript="trans",
            date="2025-01-01",
        )
        defaults.update(overrides)
        return write_youtube_note(**defaults)

    def test_creates_file_at_correct_path(self, tmp_path):
        relative = self._write(tmp_path)
        assert relative == os.path.join("YouTube Archive", "RickAstleyVEVO", "RickAstleyVEVO_dQw4w9WgXcQ.md")
        full_path = tmp_path / "YouTube Archive" / "RickAstleyVEVO" / "RickAstleyVEVO_dQw4w9WgXcQ.md"
        assert full_path.exists()

    def test_file_contains_description_and_transcript(self, tmp_path):
        self._write(tmp_path, description="my description", transcript="my transcript")
        content = (tmp_path / "YouTube Archive" / "RickAstleyVEVO" / "RickAstleyVEVO_dQw4w9WgXcQ.md").read_text()
        assert "my description" in content
        assert "my transcript" in content

    def test_creates_nested_directories(self, tmp_path):
        self._write(tmp_path)
        assert (tmp_path / "YouTube Archive" / "RickAstleyVEVO").is_dir()

    def test_second_write_gets_count_2(self, tmp_path):
        self._write(tmp_path)
        relative = self._write(tmp_path)
        assert relative == os.path.join("YouTube Archive", "RickAstleyVEVO", "RickAstleyVEVO_dQw4w9WgXcQ (2).md")

    def test_both_files_exist_after_duplicate(self, tmp_path):
        self._write(tmp_path)
        self._write(tmp_path)
        assert (tmp_path / "YouTube Archive" / "RickAstleyVEVO" / "RickAstleyVEVO_dQw4w9WgXcQ.md").exists()
        assert (tmp_path / "YouTube Archive" / "RickAstleyVEVO" / "RickAstleyVEVO_dQw4w9WgXcQ (2).md").exists()
