"""SQL 层 · 素材。"""
from __future__ import annotations

from ..db import execute, query, query_one


def for_project(pid: int) -> list[dict]:
    return query("SELECT * FROM assets WHERE project_id=? ORDER BY id", (pid,))


def get(aid: int) -> dict | None:
    return query_one("SELECT * FROM assets WHERE id=?", (aid,))


def count_in_project(pid: int) -> int:
    return query_one("SELECT COUNT(*) AS n FROM assets WHERE project_id=?", (pid,))["n"]


def add(pid: int, file_name: str, file_path: str, size_bytes: int) -> int:
    return execute(
        "INSERT INTO assets (project_id, file_name, file_path, size_bytes) VALUES (?,?,?,?)",
        (pid, file_name, file_path, size_bytes))


def save_probe(aid: int, meta: dict, quality: float) -> None:
    execute(
        """UPDATE assets SET duration_ms=?, width=?, height=?, fps=?, size_bytes=?,
           shot_at=?, quality_score=?, probe_status=1, updated_at=datetime('now','localtime') WHERE id=?""",
        (meta["duration_ms"], meta["width"], meta["height"], meta["fps"], meta["size_bytes"],
         meta["shot_at"], quality, aid))


def mark_probe_failed(aid: int) -> None:
    execute("UPDATE assets SET probe_status=2, updated_at=datetime('now','localtime') WHERE id=?", (aid,))


def save_proxy(aid: int, proxy_key: str, thumb_key: str) -> None:
    execute(
        "UPDATE assets SET proxy_key=?, thumb_key=?, proxy_status=1, updated_at=datetime('now','localtime') WHERE id=?",
        (proxy_key, thumb_key, aid))


def mark_proxy_failed(aid: int) -> None:
    execute("UPDATE assets SET proxy_status=2, updated_at=datetime('now','localtime') WHERE id=?", (aid,))


def delete(aid: int) -> None:
    execute("DELETE FROM assets WHERE id=?", (aid,))
