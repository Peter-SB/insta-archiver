"""Application configuration loaded from environment variables.

Data is split into three subdirectories so each can be volume-mounted
independently:
  DB_DIR       — SQLite database only
  MARKDOWN_DIR — Obsidian notes (safe to mount directly into a vault)
  MEDIA_DIR    — Downloaded video/image files (can be excluded from vault)

Design decision: All config is module-level so other modules can reference
config.X at runtime (not import-time copies). This makes monkeypatching
in tests straightforward.
"""

import os

DATA_DIR = os.environ.get("DATA_DIR", "/data")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")
DEFAULT_FOLDER = "Insta Archive"
YOUTUBE_DEFAULT_FOLDER = "YouTube Archive"

DB_DIR = os.path.join(DATA_DIR, "db")
MARKDOWN_DIR = os.path.join(DATA_DIR, "markdown")
MEDIA_DIR = os.path.join(DATA_DIR, "media")

DB_PATH = os.path.join(DB_DIR, "insta_archiver.db")
