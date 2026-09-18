"""数据库层 · 连接与访问门面（SQLite/WAL）。"""
from __future__ import annotations

import sqlite3
from typing import Any, Iterator

from ..config import DATA_DIR

db_path = DATA_DIR / "shanjian.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def query(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def query_one(sql: str, params: tuple = ()) -> dict[str, Any] | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple = ()) -> int:
    """写操作，返回 lastrowid。"""
    with connect() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid


def executemany(sql: str, seq: Iterator[tuple] | list[tuple]) -> None:
    with connect() as conn:
        conn.executemany(sql, seq)
        conn.commit()
