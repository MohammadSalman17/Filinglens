"""Query logging and answer caching. Nothing in here is allowed to crash the app."""
import contextlib
import json
import os
import re
import sqlite3
import tempfile
import time
from pathlib import Path

# Change this text whenever you change the prompt, the model or the data.
# Old cached answers will then be ignored automatically.
CACHE_VERSION = "v1"


def pick_folder():
    base = Path(os.getenv("TRACK_DIR", Path(__file__).parent.parent / "data" / "tracking"))
    try:
        base.mkdir(parents=True, exist_ok=True)
        probe = base / ".write_test"
        probe.write_text("x")
        probe.unlink()
        return base
    except Exception:
        # e.g. inside Docker where the app folder is read-only
        fallback = Path(tempfile.gettempdir()) / "filinglens_tracking"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


TRACK_DIR = pick_folder()
LOG_FILE = TRACK_DIR / "queries.jsonl"
CACHE_DB = TRACK_DIR / "cache.sqlite3"


def normalize(question):
    """'What was Alphabet's revenue?' and 'what was alphabet s revenue' become the same key."""
    return re.sub(r"[^a-z0-9]+", " ", question.lower()).strip()


def cache_key(question):
    return f"{CACHE_VERSION}|{normalize(question)}"


def connect():
    conn = sqlite3.connect(CACHE_DB, timeout=5)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS cache "
        "(key TEXT PRIMARY KEY, answer TEXT, sources TEXT, created REAL)"
    )
    return conn


def cache_get(question):
    """Returns (answer_text, sources) or None."""
    try:
        with contextlib.closing(connect()) as conn:
            row = conn.execute(
                "SELECT answer, sources FROM cache WHERE key = ?", (cache_key(question),)
            ).fetchone()
        if row:
            return row[0], json.loads(row[1])
    except Exception as e:
        print(f"[cache] read failed: {e}")
    return None


def cache_put(question, answer, sources):
    try:
        with contextlib.closing(connect()) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache VALUES (?, ?, ?, ?)",
                (cache_key(question), answer, json.dumps(sources), time.time()),
            )
            conn.commit()
    except Exception as e:
        print(f"[cache] write failed: {e}")


def log_event(**fields):
    """Appends one line (one JSON object) per question to queries.jsonl."""
    try:
        fields["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(fields, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[log] write failed: {e}")