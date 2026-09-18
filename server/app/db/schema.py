"""数据库层 · Schema（八表 DDL，唯一真相）。"""
from __future__ import annotations

CORE_TABLES = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    status INTEGER NOT NULL DEFAULT 0,            -- 0 草稿 / 1 已导出
    note TEXT DEFAULT '',
    cover_key TEXT,
    current_version INTEGER DEFAULT 0,            -- 最新 EDL 快照版本
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,                      -- 原片相对 assets_dir 的 key
    duration_ms INTEGER,
    width INTEGER,
    height INTEGER,
    fps REAL,
    size_bytes INTEGER,
    shot_at TEXT,                                 -- 拍摄时间
    proxy_key TEXT,                               -- 720p 代理
    thumb_key TEXT,                               -- 封面缩略图
    quality_score REAL,                           -- 「画质佳」评分，>=0.8 打标
    probe_status INTEGER NOT NULL DEFAULT 0,      -- 0 待解析 / 1 完成 / 2 失败
    proxy_status INTEGER NOT NULL DEFAULT 0,      -- 0 生成中 / 1 完成 / 2 失败
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS analysis_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,
    status INTEGER NOT NULL DEFAULT 0,            -- 0 进行中 / 1 完成 / 2 失败
    scene_tags TEXT,                              -- JSON: [{clip_ref, label, category}]
    mood_mix TEXT,                                -- JSON: {"舒缓":0.62,...}
    tempo_bpm REAL,
    energy_curve TEXT,                            -- JSON: [{t_ms, energy}]
    elapsed_ms INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS music_library (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,               -- 相对 music_dir
    title TEXT,
    artist TEXT,
    duration_ms INTEGER,
    bpm REAL,
    chorus_ms INTEGER,                            -- 副歌起点
    energy REAL,
    mood_tags TEXT,                               -- JSON 数组
    status INTEGER NOT NULL DEFAULT 0,            -- 0 待打标 / 1 就绪
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS timelines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    source INTEGER NOT NULL DEFAULT 1,            -- 1 AI / 2 手动 / 3 换剪法
    edl TEXT NOT NULL,                            -- EDL JSON（docs/EDL-spec.md）
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (project_id, version)
);

CREATE TABLE IF NOT EXISTS exports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,                     -- v{n}，不覆盖
    file_key TEXT NOT NULL,
    resolution TEXT,
    fps INTEGER,
    size_bytes INTEGER,
    elapsed_ms INTEGER,
    saved_to_album INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (project_id, version)
);
"""

USER_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    pass_hash TEXT NOT NULL,                      -- scrypt: salt$hex
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS auth_tokens (
    token TEXT PRIMARY KEY,                       -- secrets.token_hex(24)，长期有效
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
"""
