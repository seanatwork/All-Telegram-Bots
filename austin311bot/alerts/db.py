"""SQLite persistence for alert subscriptions.

DB path defaults to /tmp/austin311_alerts.db.
Set ALERTS_DB_PATH env var (e.g. to a Fly volume) for persistence across redeploys.
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = os.getenv("ALERTS_DB_PATH", "/tmp/austin311_alerts.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id   INTEGER PRIMARY KEY,
    chat_id   INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(user_id),
    alert_type  TEXT NOT NULL,   -- 'crime_daily' | 'district_digest'
    district    TEXT NOT NULL,   -- '1' .. '10'
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sent_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER NOT NULL REFERENCES subscriptions(id),
    data_hash       TEXT NOT NULL,
    sent_at         TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(subscription_id, data_hash)
);
"""


@contextmanager
def _conn():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with _conn() as con:
        con.executescript(SCHEMA)


# ── users ──────────────────────────────────────────────────────────────────────

def upsert_user(user_id: int, chat_id: int) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO users(user_id, chat_id) VALUES(?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET chat_id=excluded.chat_id",
            (user_id, chat_id),
        )


# ── subscriptions ──────────────────────────────────────────────────────────────

def add_subscription(user_id: int, alert_type: str, district: str) -> int:
    with _conn() as con:
        # Deactivate any existing same-type subscription for this user first
        con.execute(
            "UPDATE subscriptions SET active=0 WHERE user_id=? AND alert_type=? AND district=?",
            (user_id, alert_type, district),
        )
        cur = con.execute(
            "INSERT INTO subscriptions(user_id, alert_type, district) VALUES(?,?,?)",
            (user_id, alert_type, district),
        )
        return cur.lastrowid


def get_active_subscriptions(alert_type: str) -> list[sqlite3.Row]:
    with _conn() as con:
        return con.execute(
            "SELECT s.id, s.district, u.chat_id, s.user_id "
            "FROM subscriptions s JOIN users u USING(user_id) "
            "WHERE s.alert_type=? AND s.active=1",
            (alert_type,),
        ).fetchall()


def get_user_subscriptions(user_id: int) -> list[sqlite3.Row]:
    with _conn() as con:
        return con.execute(
            "SELECT id, alert_type, district, created_at FROM subscriptions "
            "WHERE user_id=? AND active=1 ORDER BY created_at",
            (user_id,),
        ).fetchall()


def deactivate_subscription(sub_id: int, user_id: int) -> bool:
    with _conn() as con:
        cur = con.execute(
            "UPDATE subscriptions SET active=0 WHERE id=? AND user_id=?",
            (sub_id, user_id),
        )
        return cur.rowcount > 0


def deactivate_all(user_id: int) -> int:
    with _conn() as con:
        cur = con.execute(
            "UPDATE subscriptions SET active=0 WHERE user_id=?", (user_id,)
        )
        return cur.rowcount


def delete_user_data(user_id: int) -> None:
    with _conn() as con:
        sub_ids = [
            r[0] for r in con.execute(
                "SELECT id FROM subscriptions WHERE user_id=?", (user_id,)
            ).fetchall()
        ]
        if sub_ids:
            con.execute(
                f"DELETE FROM sent_log WHERE subscription_id IN ({','.join('?'*len(sub_ids))})",
                sub_ids,
            )
        con.execute("DELETE FROM subscriptions WHERE user_id=?", (user_id,))
        con.execute("DELETE FROM users WHERE user_id=?", (user_id,))


# ── deduplication ──────────────────────────────────────────────────────────────

def already_sent(sub_id: int, data_hash: str) -> bool:
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM sent_log WHERE subscription_id=? AND data_hash=?",
            (sub_id, data_hash),
        ).fetchone()
        return row is not None


def mark_sent(sub_id: int, data_hash: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT OR IGNORE INTO sent_log(subscription_id, data_hash) VALUES(?,?)",
            (sub_id, data_hash),
        )


def prune_sent_log(days: int = 45) -> None:
    with _conn() as con:
        con.execute(
            "DELETE FROM sent_log WHERE sent_at < datetime('now', ?)",
            (f"-{days} days",),
        )
