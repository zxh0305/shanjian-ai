"""SQL 层 · 大模型调用计量。"""
from __future__ import annotations

from ..db import execute, query_one


def add(uid: int, task: str, model: str, tokens_in: int, tokens_out: int, elapsed_ms: int, ok: bool) -> None:
    execute(
        """INSERT INTO llm_usage (user_id, task, model, tokens_in, tokens_out, elapsed_ms, ok)
           VALUES (?,?,?,?,?,?,?)""",
        (uid, task, model, tokens_in, tokens_out, elapsed_ms, 1 if ok else 0))


def month_summary(uid: int) -> dict:
    """本月用量：次数/失败数/输入输出 tokens。"""
    row = query_one(
        """SELECT COUNT(*) AS calls,
                  COALESCE(SUM(CASE WHEN ok=0 THEN 1 ELSE 0 END),0) AS failed,
                  COALESCE(SUM(tokens_in),0) AS tokens_in,
                  COALESCE(SUM(tokens_out),0) AS tokens_out
           FROM llm_usage
           WHERE user_id=? AND created_at >= datetime('now','localtime','start of month')""", (uid,))
    return row or {"calls": 0, "failed": 0, "tokens_in": 0, "tokens_out": 0}
