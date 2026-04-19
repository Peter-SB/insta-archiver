"""End-to-end tests for the FastAPI application.

Uses FastAPI TestClient to exercise HTTP endpoints.
The worker is mocked out so no actual downloading/transcription happens.
"""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app.config as config
import app.database as database


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a test client with isolated DB and split data directories.

    Mocks start_worker so no background thread is spawned during tests.
    """
    data_dir = str(tmp_path / "data")
    db_dir = os.path.join(data_dir, "db")
    markdown_dir = os.path.join(data_dir, "markdown")
    media_dir = os.path.join(data_dir, "media")
    for d in (db_dir, media_dir, os.path.join(markdown_dir, "Insta Archive")):
        os.makedirs(d, exist_ok=True)

    db_path = os.path.join(db_dir, "test.db")
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    monkeypatch.setattr(config, "DB_DIR", db_dir)
    monkeypatch.setattr(config, "MARKDOWN_DIR", markdown_dir)
    monkeypatch.setattr(config, "MEDIA_DIR", media_dir)

    # Reset any existing thread-local connection
    database.close_connection()

    with patch("app.worker.start_worker"), patch("app.worker.signal_worker"):
        from app.main import app

        with TestClient(app) as c:
            yield c

    database.close_connection()


class TestIndex:
    def test_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_contains_page_title(self, client):
        response = client.get("/")
        assert "Instagram Archiver" in response.text

    def test_contains_form(self, client):
        response = client.get("/")
        assert 'name="url"' in response.text
        assert 'name="folder"' in response.text
        assert 'name="save_video"' in response.text


class TestAddJob:
    def test_valid_url_creates_job(self, client):
        response = client.post(
            "/jobs",
            data={"url": "https://www.instagram.com/reel/ABC123/", "folder": "Insta Archive"},
        )
        assert response.status_code == 200
        jobs = database.get_all_jobs()
        assert len(jobs) == 1
        assert jobs[0]["shortcode"] == "ABC123"

    def test_invalid_url_returns_error(self, client):
        response = client.post(
            "/jobs",
            data={"url": "not-a-valid-url", "folder": "Insta Archive"},
        )
        assert response.status_code == 200
        assert "Could not extract shortcode" in response.text
        assert database.get_all_jobs() == []

    def test_duplicate_url_returns_warning(self, client):
        client.post(
            "/jobs",
            data={"url": "https://instagram.com/reel/ABC123/", "folder": "Insta Archive"},
        )
        response = client.post(
            "/jobs",
            data={"url": "https://instagram.com/reel/ABC123/", "folder": "Insta Archive"},
        )
        assert "already been submitted" in response.text
        assert len(database.get_all_jobs()) == 1  # Not duplicated

    def test_force_allows_duplicate(self, client):
        client.post(
            "/jobs",
            data={"url": "https://instagram.com/reel/ABC123/", "folder": "Insta Archive"},
        )
        response = client.post(
            "/jobs",
            data={
                "url": "https://instagram.com/reel/ABC123/",
                "folder": "Insta Archive",
                "force": "true",
            },
        )
        assert response.status_code == 200
        assert len(database.get_all_jobs()) == 2

    def test_save_video_stored(self, client):
        client.post(
            "/jobs",
            data={"url": "https://instagram.com/reel/ABC123/", "folder": "Insta Archive", "save_video": "true"},
        )
        jobs = database.get_all_jobs()
        assert jobs[0]["save_video"] == 1

    def test_save_video_defaults_false(self, client):
        client.post(
            "/jobs",
            data={"url": "https://instagram.com/reel/ABC123/", "folder": "Insta Archive"},
        )
        jobs = database.get_all_jobs()
        assert jobs[0]["save_video"] == 0

    def test_success_triggers_refresh(self, client):
        response = client.post(
            "/jobs",
            data={"url": "https://instagram.com/reel/NEW123/", "folder": "Insta Archive"},
        )
        assert response.headers.get("HX-Trigger") == "refreshJobs"


class TestListJobs:
    def test_returns_job_list_html(self, client):
        client.post(
            "/jobs",
            data={"url": "https://instagram.com/reel/ABC123/", "folder": "Insta Archive"},
        )
        response = client.get("/jobs")
        assert response.status_code == 200
        assert "ABC123" in response.text

    def test_empty_state(self, client):
        response = client.get("/jobs")
        assert "No jobs yet" in response.text


class TestFolders:
    def test_returns_default_folder(self, client):
        response = client.get("/folders")
        assert response.status_code == 200
        assert "Insta Archive" in response.json()

    def test_lists_markdown_subdirectories(self, client, tmp_path):
        """Folders are sourced from MARKDOWN_DIR, not DATA_DIR root."""
        os.makedirs(os.path.join(tmp_path, "data", "markdown", "Custom Folder"), exist_ok=True)
        response = client.get("/folders")
        assert "Custom Folder" in response.json()


class TestHealth:
    def test_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
