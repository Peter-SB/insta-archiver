"""Unit tests for app.database module.

Tests cover CRUD operations, dedup checking, status transitions,
and the security whitelist on update_job_status fields.
"""

import pytest

from app import database


class TestCreateJob:
    def test_returns_job_id(self, test_db):
        job_id = database.create_job("https://instagram.com/reel/ABC123/", "ABC123", "Insta Archive")
        assert job_id == 1

    def test_duplicate_urls_allowed(self, test_db):
        """URL is NOT unique — users can re-archive the same post."""
        url = "https://instagram.com/reel/ABC123/"
        database.create_job(url, "ABC123", "Insta Archive")
        database.create_job(url, "ABC123", "Insta Archive")
        jobs = database.get_all_jobs()
        assert len(jobs) == 2

    def test_job_has_waiting_status(self, test_db):
        database.create_job("url", "SC", "folder")
        jobs = database.get_all_jobs()
        assert jobs[0]["status"] == "waiting"

    def test_job_has_created_at(self, test_db):
        database.create_job("url", "SC", "folder")
        jobs = database.get_all_jobs()
        assert jobs[0]["created_at"] is not None

    def test_save_video_defaults_false(self, test_db):
        database.create_job("url", "SC", "folder")
        jobs = database.get_all_jobs()
        assert jobs[0]["save_video"] == 0

    def test_save_video_stored_true(self, test_db):
        database.create_job("url", "SC", "folder", save_video=True)
        jobs = database.get_all_jobs()
        assert jobs[0]["save_video"] == 1


class TestGetAllJobs:
    def test_returns_newest_first(self, test_db):
        database.create_job("url1", "SC1", "folder")
        database.create_job("url2", "SC2", "folder")
        jobs = database.get_all_jobs()
        assert jobs[0]["shortcode"] == "SC2"
        assert jobs[1]["shortcode"] == "SC1"

    def test_returns_empty_list_when_no_jobs(self, test_db):
        assert database.get_all_jobs() == []


class TestGetNextWaitingJob:
    def test_returns_oldest_waiting(self, test_db):
        database.create_job("url1", "SC1", "folder")
        database.create_job("url2", "SC2", "folder")
        job = database.get_next_waiting_job()
        assert job["shortcode"] == "SC1"

    def test_skips_non_waiting_jobs(self, test_db):
        job_id = database.create_job("url1", "SC1", "folder")
        database.update_job_status(job_id, "started")
        database.create_job("url2", "SC2", "folder")
        job = database.get_next_waiting_job()
        assert job["shortcode"] == "SC2"

    def test_returns_none_when_queue_empty(self, test_db):
        assert database.get_next_waiting_job() is None

    def test_returns_none_when_all_complete(self, test_db):
        job_id = database.create_job("url", "SC", "folder")
        database.update_job_status(job_id, "successful")
        assert database.get_next_waiting_job() is None


class TestUpdateJobStatus:
    def test_changes_status(self, test_db):
        job_id = database.create_job("url", "SC", "folder")
        database.update_job_status(job_id, "started")
        jobs = database.get_all_jobs()
        assert jobs[0]["status"] == "started"

    def test_downloading_status(self, test_db):
        job_id = database.create_job("url", "SC", "folder")
        database.update_job_status(job_id, "downloading")
        assert database.get_all_jobs()[0]["status"] == "downloading"

    def test_transcribing_status(self, test_db):
        job_id = database.create_job("url", "SC", "folder")
        database.update_job_status(job_id, "transcribing")
        assert database.get_all_jobs()[0]["status"] == "transcribing"

    def test_sets_note_path(self, test_db):
        job_id = database.create_job("url", "SC", "folder")
        database.update_job_status(job_id, "successful", note_path="folder/note.md")
        jobs = database.get_all_jobs()
        assert jobs[0]["note_path"] == "folder/note.md"

    def test_sets_error_message(self, test_db):
        job_id = database.create_job("url", "SC", "folder")
        database.update_job_status(job_id, "failed", error_message="download error")
        jobs = database.get_all_jobs()
        assert jobs[0]["error_message"] == "download error"

    def test_sets_account_name(self, test_db):
        job_id = database.create_job("url", "SC", "folder")
        database.update_job_status(job_id, "started", account_name="testuser")
        jobs = database.get_all_jobs()
        assert jobs[0]["account_name"] == "testuser"

    def test_rejects_disallowed_fields(self, test_db):
        """Prevents SQL injection via dynamic column names."""
        job_id = database.create_job("url", "SC", "folder")
        with pytest.raises(ValueError, match="not an allowed update field"):
            database.update_job_status(job_id, "started", malicious_field="DROP TABLE")


class TestJobExistsForUrl:
    def test_returns_false_when_no_match(self, test_db):
        assert database.job_exists_for_url("https://instagram.com/reel/MISSING/") is False

    def test_returns_true_when_match_exists(self, test_db):
        database.create_job("https://instagram.com/reel/ABC123/", "ABC123", "folder")
        assert database.job_exists_for_url("https://instagram.com/reel/ABC123/") is True

    def test_returns_true_regardless_of_status(self, test_db):
        job_id = database.create_job("url", "SC", "folder")
        database.update_job_status(job_id, "failed", error_message="err")
        assert database.job_exists_for_url("url") is True
