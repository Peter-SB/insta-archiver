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
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(config, "DB_PATH", db_path)

    database.close_connection()
    database.init_db()
    yield db_path
    database.close_connection()


@pytest.fixture
def test_data_dir(tmp_path, monkeypatch):
    """Provide a temporary data directory for testing."""
    data_dir = str(tmp_path / "data")
    os.makedirs(data_dir, exist_ok=True)
    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    return data_dir
