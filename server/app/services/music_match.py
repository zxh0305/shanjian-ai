"""音乐库：扫描目录 → 打标（时长/BPM/能量/副歌起点）→ 按素材节奏打分选 Top-4。

打分规则（定稿 §4.2）：BPM 接近（±10% 满分）+ 能量曲线相关性 + 时长够用。
副歌起点 MVP 口径：能量最高 10s 窗口的起点（W5 可升级为结构分析）。
"""
from __future__ import annotations

import re
from pathlib import Path

from .. import db
from ..config import settings
from ..core import media_analysis as ma

AUDIO_EXTS = {".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg"}


def scan_library() -> int:
    """扫描 music_dir，登记未入库的音频文件。返回新增数量。"""
    known = {r["file_path"] for r in db.query("SELECT file_path FROM music_library")}
    added = 0
    for p in sorted(settings.music_dir.rglob("*")):
        if p.suffix.lower() not in AUDIO_EXTS or p.is_dir():
            continue
        rel = str(p.relative_to(settings.music_dir))
        if rel in known:
            continue
        db.execute(
            "INSERT OR IGNORE INTO music_library (file_path, title) VALUES (?,?)",
            (rel, p.stem),
        )
        added += 1
    return added


def tag_track(row: dict) -> None:
    """为一条待打标记录计算 BPM/能量/时长/副歌（就绪后 status=1）。"""
    path = settings.music_dir / row["file_path"]
    try:
        from .probe import probe_duration
        duration_ms = probe_duration(str(path))
        curve = ma.audio_energy_curve(str(path))
        bpm = ma.estimate_bpm(curve)
        energy = round(sum(curve) / len(curve), 1) if curve else -60.0
        chorus_ms = _chorus_start(curve)
        title = _title_from_name(row["file_path"])
        db.execute(
            """UPDATE music_library SET title=?, bpm=?, energy=?, chorus_ms=?,
               duration_ms=?, status=1, updated_at=datetime('now','localtime') WHERE id=?""",
            (title, bpm, energy, chorus_ms, duration_ms, row["id"]),
        )
    except Exception as e:  # noqa: BLE001 打不动的歌标记为 2，不阻塞库内其他曲目
        db.execute(
            "UPDATE music_library SET status=2, updated_at=datetime('now','localtime') WHERE id=?",
            (row["id"],),
        )
        print(f"[music] 跳过 {row['file_path']}: {e}")


def _chorus_start(curve_db: list[float], window_s: int = 10) -> int:
    if len(curve_db) <= window_s:
        return 0
    best_i, best_v = 0, -1e9
    for i in range(len(curve_db) - window_s):
        v = sum(curve_db[i:i + window_s])
        if v > best_v:
            best_v, best_i = v, i
    return best_i * 1000


def _title_from_name(rel: str) -> str:
    stem = Path(rel).stem
    stem = re.sub(r"^\d+[\s._-]*", "", stem)  # 去掉曲库常见的序号前缀
    return stem or rel


def candidates(project_bpm: float | None, need_duration_ms: int, offset: int = 0, limit: int = 4) -> list[dict]:
    """按项目节奏选 Top-4（offset 支持换一批）。分数即原型「96% 匹配」口径。"""
    rows = db.query("SELECT * FROM music_library WHERE status=1 ORDER BY id")
    scored = []
    for r in rows:
        score = 0.5
        reasons = []
        if project_bpm and r["bpm"]:
            diff = abs(r["bpm"] - project_bpm) / max(project_bpm, 1)
            if diff <= 0.10:
                score += 0.35
                reasons.append("节奏吻合")
            elif diff <= 0.25:
                score += 0.15
            if r["energy"] is not None and r["energy"] > -30:
                score += 0.05
        if r["duration_ms"] and r["duration_ms"] >= need_duration_ms * 0.8:
            score += 0.10
            reasons.append("长度合适")
        if r["chorus_ms"]:
            score += 0.03
        scored.append((min(score, 0.99), reasons, r))
    scored.sort(key=lambda t: -t[0])
    out = []
    for score, reasons, r in scored[offset:offset + limit]:
        out.append({
            "musicId": r["id"],
            "title": r["title"],
            "artist": r["artist"],
            "bpm": r["bpm"],
            "durationMs": r["duration_ms"],
            "chorusMs": r["chorus_ms"],
            "match": int(round(score * 100)),          # 演示口径 96/92/89/85
            "reasons": reasons or ["综合匹配"],
            "previewUrl": f"/media/music/{r['file_path']}",
        })
    return out


def ensure_tagged(max_new: int = 20) -> None:
    """有未打标曲目就先打标（同步跑，单人曲库量级小）。"""
    pending = db.query(
        "SELECT * FROM music_library WHERE status=0 ORDER BY id LIMIT ?", (max_new,))
    for row in pending:
        tag_track(row)
