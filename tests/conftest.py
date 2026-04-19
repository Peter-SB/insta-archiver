"""Shared test fixtures."""

import os

import pytest

import app.config as config
import app.database as database


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Provide a temporary SQLite database for testing.

    Monkeypatches config.DB_PATH so all database operations
    use an isolated temp file. Cleans up the connection after each test.
    """
    db_path = str(tmp_path / "db" / "test.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    monkeypatch.setattr(config, "DB_PATH", db_path)

    database.close_connection()
    database.init_db()
    yield db_path
    database.close_connection()


@pytest.fixture
def test_data_dir(tmp_path, monkeypatch):
    """Provide temporary split data directories (db/markdown/media) for testing."""
    data_dir = str(tmp_path / "data")
    markdown_dir = os.path.join(data_dir, "markdown")
    media_dir = os.path.join(data_dir, "media")
    db_dir = os.path.join(data_dir, "db")
    for d in (markdown_dir, media_dir, db_dir):
        os.makedirs(d, exist_ok=True)
    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    monkeypatch.setattr(config, "MARKDOWN_DIR", markdown_dir)
    monkeypatch.setattr(config, "MEDIA_DIR", media_dir)
    monkeypatch.setattr(config, "DB_DIR", db_dir)
    return data_dir
