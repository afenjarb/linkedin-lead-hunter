import sqlite3
import json
from pathlib import Path

DB_PATH = Path("leads.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT NOT NULL,
            profile_url      TEXT NOT NULL,
            post_text        TEXT NOT NULL,
            score            INTEGER NOT NULL,
            bucket           TEXT NOT NULL,
            matched_keywords TEXT NOT NULL,
            score_breakdown  TEXT NOT NULL,
            created_at       TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id    INTEGER NOT NULL REFERENCES leads(id),
            invite     TEXT,
            email      TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


def upsert_lead(lead: dict) -> int:
    """Insert warm lead; skip if profile_url already exists. Returns lead id."""
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM leads WHERE profile_url = ?", (lead["profile_url"],)
    ).fetchone()
    if existing:
        conn.close()
        return existing["id"]

    cur = conn.execute(
        """INSERT INTO leads (name, profile_url, post_text, score, bucket,
                              matched_keywords, score_breakdown)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            lead["name"],
            lead["profile_url"],
            lead["post_text"],
            lead["score"],
            lead["bucket"],
            json.dumps(lead["matched_keywords"]),
            json.dumps(lead["score_breakdown"]),
        ),
    )
    conn.commit()
    lead_id = cur.lastrowid
    conn.close()
    return lead_id


def save_messages(lead_id: int, invite: str, email: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO messages (lead_id, invite, email) VALUES (?, ?, ?)",
        (lead_id, invite, email),
    )
    conn.commit()
    conn.close()
