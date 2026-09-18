"""SQL 层 · 成片导出。"""
from __future__ import annotations

from ..db import execute, query, query_one


def for_project(pid: int) -> list[dict]:
    return query("SELECT * FROM exports WHERE project_id=? ORDER BY version DESC", (pid,))


def get_version(pid: int, version: int) -> dict | None:
    return query_one("SELECT * FROM exports WHERE project_id=? AND version=?", (pid, version))


def max_version(pid: int) -> int:
    return query_one("SELECT MAX(version) AS v FROM exports WHERE project_id=?", (pid,))["v"] or 0


def add(pid: int, version: int, file_key: str, resolution: str, fps: int, size_bytes: int, elapsed_ms: int) -> None:
    execute(
        """INSERT INTO exports (project_id, version, file_key, resolution, fps, size_bytes, elapsed_ms)
           VALUES (?,?,?,?,?,?,?)""",
        (pid, version, file_key, resolution, fps, size_bytes, elapsed_ms))


def delete(pid: int, version: int) -> None:
    execute("DELETE FROM exports WHERE project_id=? AND version=?", (pid, version))


def project_title(pid: int) -> str:
    return query_one("SELECT title FROM projects WHERE id=?", (pid,))["title"]
