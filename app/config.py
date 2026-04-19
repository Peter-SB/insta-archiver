"""Application configuration loaded from environment variables.

Design decision: All config is module-level so other modules can reference
config.X at runtime (not import-time copies). This makes monkeypatching
in tests straightforward.
"""

import os

DATA_DIR = os.environ.get("DATA_DIR", "/data")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")
DEFAULT_FOLDER = "Insta Archive"
DB_PATH = os.path.join(DATA_DIR, "insta_archiver.db")
