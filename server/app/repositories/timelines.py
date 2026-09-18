"""SQL 层 · 时间线（EDL 快照）。"""
from __future__ import annotations

from ..db import execute, query_one


def latest(pid: int) -> dict | None:
    return query_one("SELECT * FROM timelines WHERE project_id=? ORDER BY version DESC LIMIT 1", (pid,))


def get_version(pid: int, version: int) -> dict | None:
    return query_one("SELECT * FROM timelines WHERE project_id=? AND version=?", (pid, version))


def max_version(pid: int) -> int:
    return query_one("SELECT MAX(version) AS v FROM timelines WHERE project_id=?", (pid,))["v"] or 0


def insert(pid: int, version: int, source: int, edl_json: str) -> None:
    execute("INSERT INTO timelines (project_id, version, source, edl) VALUES (?,?,?,?)",
            (pid, version, source, edl_json))


def update_edl(pid: int, version: int, edl_json: str) -> None:
    execute("UPDATE timelines SET edl=? WHERE project_id=? AND version=?", (edl_json, pid, version))
