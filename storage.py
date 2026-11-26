"""Historique des SMS dans SQLite.

Statuts : pending -> sent | failed
"""
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

import config

_lock = threading.Lock()


@contextmanager
def _db():
    with _lock:
        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db() -> None:
    with _db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS sms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                next_try_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )


def add_sms(number: str, message: str) -> int:
    now = _now()
    with _db() as c:
        cur = c.execute(
            "INSERT INTO sms (number, message, next_try_at, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (number, message, now, now, now),
        )
        return cur.lastrowid


def get_sms(sms_id: int):
    with _db() as c:
        row = c.execute("SELECT * FROM sms WHERE id = ?", (sms_id,)).fetchone()
        return dict(row) if row else None


def list_sms(limit: int = 50, status: str | None = None):
    query = "SELECT * FROM sms"
    params: list = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with _db() as c:
        return [dict(r) for r in c.execute(query, params).fetchall()]


def next_pending():
    """Prochain SMS à envoyer (pending et délai de retry écoulé)."""
    with _db() as c:
        row = c.execute(
            "SELECT * FROM sms WHERE status = 'pending' AND next_try_at <= ? "
            "ORDER BY id ASC LIMIT 1",
            (_now(),),
        ).fetchone()
        return dict(row) if row else None


def mark_sent(sms_id: int) -> None:
    with _db() as c:
        c.execute(
            "UPDATE sms SET status='sent', attempts=attempts+1, error=NULL, "
            "updated_at=? WHERE id=?",
            (_now(), sms_id),
        )


def mark_retry(sms_id: int, error: str, next_try_at: str) -> None:
    with _db() as c:
        c.execute(
            "UPDATE sms SET attempts=attempts+1, error=?, next_try_at=?, "
            "updated_at=? WHERE id=?",
            (error, next_try_at, _now(), sms_id),
        )


def mark_failed(sms_id: int, error: str) -> None:
    with _db() as c:
        c.execute(
            "UPDATE sms SET status='failed', attempts=attempts+1, error=?, "
            "updated_at=? WHERE id=?",
            (error, _now(), sms_id),
        )
