"""SQL 层 · AI 分析报告。"""
from __future__ import annotations

from ..db import execute, query_one


def get_done(pid: int) -> dict | None:
    return query_one("SELECT * FROM analysis_reports WHERE project_id=? AND status=1", (pid,))


def invalidate(pid: int) -> None:
    """素材集变化后旧报告失真：删除，让流程自动重跑。"""
    execute("DELETE FROM analysis_reports WHERE project_id=?", (pid,))
