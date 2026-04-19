"""Unit tests for service modules.

Tests extract_shortcode (pure function), markdown rendering/writing,
and verifies outputs without hitting external services.
"""

import os

import pytest

from app.services.instaloader_service import extract_shortcode
from app.services.markdown_service import render_note, write_note


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
            data_dir=str(tmp_path),
            folder="TestFolder",
            account_name="testuser",
            shortcode="ABC123",
            url="https://instagram.com/reel/ABC123/",
            description="description text",
            transcript="transcript text",
            date="2025-01-01",
        )
        assert relative == os.path.join("TestFolder", "testuser_ABC123", "testuser_ABC123.md")

        full_path = tmp_path / "TestFolder" / "testuser_ABC123" / "testuser_ABC123.md"
        assert full_path.exists()

    def test_file_contains_description_and_transcript(self, tmp_path):
        write_note(
            data_dir=str(tmp_path),
            folder="F",
            account_name="user",
            shortcode="SC",
            url="url",
            description="my description",
            transcript="my transcript",
            date="date",
        )
        content = (tmp_path / "F" / "user_SC" / "user_SC.md").read_text()
        assert "my description" in content
        assert "my transcript" in content

    def test_creates_nested_directories(self, tmp_path):
        write_note(
            data_dir=str(tmp_path),
            folder="New Folder",
            account_name="acct",
            shortcode="SC",
            url="url",
            description="d",
            transcript="t",
            date="date",
        )
        assert (tmp_path / "New Folder" / "acct_SC").is_dir()
