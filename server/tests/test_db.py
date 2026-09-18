"""数据层迁移单测：基线只钉死在 0001/0002，新增迁移对旧库必须真实执行。

回归背景：_BASELINE 曾从 MIGRATIONS 动态生成，网关会话新增 0003 后，
老库首次启动被基线整段标记"已应用"，llm_usage 表从未建出（no such table）。
"""
from __future__ import annotations

import os
import sqlite3
import tempfile

os.environ.setdefault("SHANJIAN_DATA_DIR", tempfile.mkdtemp(prefix="shanjian_db_"))

from app.db import migrate  # noqa: E402
import app.db.connection as conn_mod  # noqa: E402


def _mk_old_db(path) -> None:
    """模拟早期 init_db 建出的旧库：有核心表、无任何迁移记录。"""
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE projects (id INTEGER PRIMARY KEY, title TEXT)")
    c.commit()
    c.close()


def _db(path):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c


def test_old_db_baseline_still_runs_new_migrations(tmp_path, monkeypatch):
    """旧库基线后，0003 照常执行 → llm_usage 必须存在。"""
    db = str(tmp_path / "old.db")
    _mk_old_db(db)
    monkeypatch.setattr(conn_mod, "db_path", db)

    migrate.init_db()

    with _db(db) as c:
        applied = {r["version"] for r in c.execute("SELECT version FROM _migrations")}
        tables = {r["name"] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    assert applied == {"0001", "0002", "0003"}
    assert "llm_usage" in tables


def test_poisoned_marker_self_heals(tmp_path, monkeypatch):
    """曾被基线误标 0003 的库（标记在、表不在）→ init_db 自动补建。"""
    db = str(tmp_path / "poisoned.db")
    _mk_old_db(db)
    monkeypatch.setattr(conn_mod, "db_path", db)
    with _db(db) as c:
        c.execute("""CREATE TABLE _migrations (version TEXT PRIMARY KEY, name TEXT NOT NULL,
                     applied_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")
        c.execute("INSERT INTO _migrations (version, name) VALUES ('0001','core')")
        c.execute("INSERT INTO _migrations (version, name) VALUES ('0002','users')")
        c.execute("INSERT INTO _migrations (version, name) VALUES ('0003','llm_usage')")
        c.commit()

    migrate.init_db()

    with _db(db) as c:
        tables = {r["name"] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    assert "llm_usage" in tables


def test_fresh_db_all_migrations(tmp_path, monkeypatch):
    """全新库：全部迁移按序执行。"""
    db = str(tmp_path / "fresh.db")
    monkeypatch.setattr(conn_mod, "db_path", db)
    migrate.init_db()
    with _db(db) as c:
        applied = {r["version"] for r in c.execute("SELECT version FROM _migrations")}
        tables = {r["name"] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    assert applied == {"0001", "0002", "0003"}
    assert {"projects", "users", "llm_usage"} <= tables


def test_init_db_idempotent(tmp_path, monkeypatch):
    """重复 init_db 不重复执行、不报错。"""
    db = str(tmp_path / "twice.db")
    monkeypatch.setattr(conn_mod, "db_path", db)
    migrate.init_db()
    migrate.init_db()
    with _db(db) as c:
        n = c.execute("SELECT COUNT(*) AS n FROM _migrations").fetchone()["n"]
    assert n == 3
