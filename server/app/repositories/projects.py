"""SQL 层 · 项目。"""
from __future__ import annotations

from ..db import execute, query, query_one


def list_for_user(uid: int) -> list[dict]:
    return query("SELECT * FROM projects WHERE user_id=? ORDER BY updated_at DESC", (uid,))


def get(pid: int) -> dict | None:
    return query_one("SELECT * FROM projects WHERE id=?", (pid,))


def create(title: str, uid: int) -> int:
    return execute("INSERT INTO projects (title, user_id) VALUES (?,?)", (title or "未命名项目", uid))


def set_status_exported(pid: int) -> None:
    execute("UPDATE projects SET status=1, updated_at=datetime('now','localtime') WHERE id=? AND status=0", (pid,))


def bump_updated(pid: int) -> None:
    execute("UPDATE projects SET updated_at=datetime('now','localtime') WHERE id=?", (pid,))


def set_current_version(pid: int, version: int) -> None:
    execute("UPDATE projects SET current_version=?, updated_at=datetime('now','localtime') WHERE id=?",
            (version, pid))


def delete(pid: int) -> None:
    execute("DELETE FROM projects WHERE id=?", (pid,))
