from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterator

APP_DIR = Path(__file__).resolve().parent
SQL_DIR = APP_DIR / "sql"

DB_PATH = Path(os.getenv("BOOKING_DB_PATH", str(APP_DIR / "booking.db")))


def _ensure_room_columns(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(rooms)")}
    if "category" not in columns:
        conn.execute("ALTER TABLE rooms ADD COLUMN category TEXT NOT NULL DEFAULT 'library'")
    if "activity" not in columns:
        conn.execute("ALTER TABLE rooms ADD COLUMN activity TEXT")

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db() -> None:
    schema_sql = (SQL_DIR / "schema.sql").read_text(encoding="utf-8")
    seed_sql = (SQL_DIR / "seed.sql").read_text(encoding="utf-8")

    conn = get_conn()
    try:
        conn.executescript(schema_sql)
        _ensure_room_columns(conn)
        conn.executescript(seed_sql)
        conn.commit()
    finally:
        conn.close()
