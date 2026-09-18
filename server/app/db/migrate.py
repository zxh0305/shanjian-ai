"""数据库层 · 版本化迁移。

- 新库：按 MIGRATIONS 顺序执行未应用的版本；
- 旧库（由早期 init_db 建好）：基线标记 0001/0002 已应用，不再重复执行；
- 以后每次 schema 变更新增一个 (version, name, sql) 条目即可。
"""
from __future__ import annotations

from .connection import connect
from .schema import CORE_TABLES, USER_TABLES

MIGRATIONS: list[tuple[str, str, str]] = [
    ("0001", "core_six_tables", CORE_TABLES),
    ("0002", "users_and_ownership", USER_TABLES + "\n"
     "ALTER TABLE projects ADD COLUMN user_id INTEGER REFERENCES users(id);\n"),
    ("0003", "llm_usage", """
CREATE TABLE IF NOT EXISTS llm_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    task TEXT NOT NULL,                 -- analyze_scenes/build_edl/write_narration/review_cut
    model TEXT,                         -- 实际使用的模型 id
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    elapsed_ms INTEGER DEFAULT 0,
    ok INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_llm_usage_user_time ON llm_usage(user_id, created_at);
"""),
]

# 旧库基线：早期 init_db 时代的 schema 到 0002 为止。必须写死，禁止从 MIGRATIONS
# 动态生成——否则以后每次新增迁移，老库都会被"基线"直接标记为已应用而跳过建表
# （0003 曾因此翻车：标记在、表不在，首用即 no such table）。
_BASELINE = {"0001", "0002"}


def _table_exists(conn, name: str) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchall())


def init_db() -> None:
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS _migrations (
            version TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")
        applied = {r["version"] for r in conn.execute("SELECT version FROM _migrations").fetchall()}
        # 旧库基线：核心表已存在但没有任何迁移记录 → 只标记基线版本，之后的迁移照常执行
        if not applied and _table_exists(conn, "projects"):
            for version, name, _ in MIGRATIONS:
                if version in _BASELINE:
                    conn.execute("INSERT OR IGNORE INTO _migrations (version, name) VALUES (?,?)",
                                 (version, name))
            conn.commit()
            applied = set(_BASELINE)
        for version, name, sql in MIGRATIONS:
            if version in applied:
                continue
            conn.executescript(sql)
            # ALTER 可能因列已存在而失败 → 单独容错补列
            conn.execute("INSERT OR IGNORE INTO _migrations (version, name) VALUES (?,?)", (version, name))
            conn.commit()
        # 兜底：基线期误标 0003 的库（标记在、表不在）自动补建
        if "0003" in applied and not _table_exists(conn, "llm_usage"):
            conn.executescript(next(sql for v, _, sql in MIGRATIONS if v == "0003"))
            conn.commit()
        # 兜底：projects.user_id 缺失则补（旧库单独升级过一半的情况）
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(projects)").fetchall()]
        if "user_id" not in cols:
            conn.execute("ALTER TABLE projects ADD COLUMN user_id INTEGER REFERENCES users(id)")
            conn.commit()
