# Testing Guide

## Overview

Tests are split into **unit tests** (fast, isolated, no external dependencies) and **end-to-end tests** (exercise HTTP endpoints via FastAPI TestClient).

## Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run only unit tests
pytest tests/unit/ -v

# Run only e2e tests
pytest tests/e2e/ -v
```

## Test Structure

```
tests/
├── conftest.py            # Shared fixtures (test_db, test_data_dir)
├── unit/
│   ├── test_database.py   # SQLite CRUD, dedup, status transitions
│   └── test_services.py   # URL parsing, markdown rendering/writing
└── e2e/
    └── test_api.py        # HTTP endpoints via TestClient
```

## What's Tested

### Unit Tests — `test_database.py`
- **Job creation** — returns ID, sets `waiting` status, records `created_at`
- **Duplicate URLs allowed** — URL is not unique; multiple jobs for the same URL are valid
- **Job ordering** — `get_all_jobs()` returns newest first; `get_next_waiting_job()` returns oldest
- **Status transitions** — `update_job_status()` changes status and sets optional fields (`note_path`, `error_message`, `account_name`)
- **Field whitelist** — `update_job_status()` rejects unknown fields to prevent SQL injection via dynamic column names
- **Dedup check** — `job_exists_for_url()` correctly reports presence regardless of status

### Unit Tests — `test_services.py`
- **`extract_shortcode()`** — Handles `/reel/`, `/reels/`, `/p/` URLs, with/without trailing slash, query params, special shortcode characters. Raises `ValueError` for invalid URLs.
- **`render_note()`** — Verifies Obsidian frontmatter, description, transcript, and placeholder text for empty fields.
- **`write_note()`** — Creates file at the correct `{folder}/{account}_{shortcode}/{account}_{shortcode}.md` path, creates nested directories, and includes description + transcript in content.

### E2E Tests — `test_api.py`
- **`GET /`** — Returns 200, contains page title and form elements
- **`POST /jobs`** — Creates job for valid URL; returns error for invalid URL; returns duplicate warning; allows force-add; returns `HX-Trigger: refreshJobs` header on success
- **`GET /jobs`** — Returns job list HTML; shows empty state when no jobs
- **`GET /folders`** — Returns default folder; lists data subdirectories
- **`GET /health`** — Returns `{"status": "ok"}`

## Test Fixtures

| Fixture          | Scope    | Purpose                                                    |
|------------------|----------|------------------------------------------------------------|
| `test_db`        | function | Temporary SQLite DB via monkeypatched `config.DB_PATH`     |
| `test_data_dir`  | function | Temporary data directory via monkeypatched `config.DATA_DIR` |
| `client`         | function | FastAPI `TestClient` with mocked worker (no background thread) |

## Design Notes

- **No external services needed** — Worker is mocked in e2e tests so no Instagram downloading or Whisper transcription occurs during testing.
- **Isolated databases** — Each test gets a fresh SQLite file in `tmp_path`, preventing cross-test contamination.
- **Config monkeypatching** — All modules reference `config.X` at runtime (not import-time copies), making monkeypatch reliable.
