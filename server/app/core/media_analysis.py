"""素材分析 MVP（对应原型「AI 分析与音乐匹配」四步，W3–W4 的轻量实现）。

全部基于 ffmpeg 统计 + numpy，不依赖外部 API：
- 场景切分: ffmpeg select=gt(scene,threshold) 逐镜头时间戳
- 能量曲线: astats 按秒 RMS → onset 自相关估 BPM
- 场景归类: 亮度(signalstats YAVG) + 运动密度(切镜频率) → 明亮舒缓/暗调氛围/高动态
- 情绪构成: 三类占比（真实算出，非演示假数）

W3–W4 升级路径：换 open_clip 语义聚类命名（docs 定稿 §1）。
"""
from __future__ import annotations

import json
import re
import subprocess

import numpy as np

from ..config import settings

PTS_RE = re.compile(r"pts_time:([\d.]+)")
YAVG_RE = re.compile(r"YAVG:([\d.]+)")
RMS_RE = re.compile(r"RMS level dB: (-?[\d.]+)")


def _run(cmd: list[str], timeout: int = 300) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return proc.stderr  # ffmpeg 的 metadata/astats 都走 stderr


def detect_scenes(path: str, threshold: float = 0.35) -> list[float]:
    """返回镜头切换时间点（秒），含 0。"""
    out = _run([
        settings.ffmpeg, "-hide_banner", "-i", path,
        "-vf", f"select='gt(scene,{threshold})',metadata=print",
        "-an", "-f", "null", "-",
    ])
    cuts = [0.0] + sorted({float(m) for m in PTS_RE.findall(out)})
    return cuts


def avg_brightness(path: str) -> float:
    out = _run([
        settings.ffmpeg, "-hide_banner", "-i", path,
        "-vf", "select='not(mod(n,60))',signalstats,metadata=print",
        "-an", "-f", "null", "-",
    ])
    vals = [float(m) for m in YAVG_RE.findall(out)]
    return round(sum(vals) / len(vals), 1) if vals else 128.0


def audio_energy_curve(path: str, step_s: float = 1.0) -> list[float]:
    """按 step 秒桶聚合的 RMS(dB) 能量曲线（astats 逐帧输出，按 pts_time 归桶取均值）。"""
    out = _run([
        settings.ffmpeg, "-hide_banner", "-i", path,
        "-af", "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
        "-vn", "-f", "null", "-",
    ])
    # ametadata 每帧输出两行：frame:N pts:... pts_time:T / lavfi.astats.Overall.RMS_level=V
    pts_times = [float(m) for m in PTS_RE.findall(out)]
    vals_raw = re.findall(r"lavfi\.astats\.Overall\.RMS_level=(-?[\d.]+|-inf)", out)
    if not pts_times or len(pts_times) != len(vals_raw):
        return []
    vals = [-60.0 if v == "-inf" else max(float(v), -60.0) for v in vals_raw]

    buckets: dict[int, list[float]] = {}
    for t, v in zip(pts_times, vals):
        buckets.setdefault(int(t // step_s), []).append(v)
    return [round(sum(v) / len(v), 1) for _, v in sorted(buckets.items())]


def estimate_bpm(curve_db: list[float], step_s: float = 1.0) -> float | None:
    """能量 onset 的自相关估 BPM（60–180 范围取峰）。数据不足/无起伏返回 None。"""
    if len(curve_db) < 16:
        return None
    x = np.array(curve_db, dtype=float)
    onset = np.clip(np.diff(x), 0, None)
    onset = onset - onset.mean()
    if np.allclose(onset, 0):
        return None
    corr = np.correlate(onset, onset, mode="full")[len(onset) - 1:]
    fps = 1.0 / step_s
    best_bpm, best_val = None, -1.0
    for bpm in range(60, 181):
        lag = int(round(fps * 60.0 / bpm))
        if lag >= len(corr):
            continue
        if corr[lag] > best_val:
            best_val, best_bpm = corr[lag], bpm
    return float(best_bpm) if best_bpm else None


def scene_label(brightness: float, cuts_per_min: float) -> str:
    """按亮度与切镜频率归类（真实统计推导）。"""
    if cuts_per_min >= 8:
        return "高动态"
    if brightness >= 140:
        return "明亮舒缓"
    if brightness <= 90:
        return "暗调氛围"
    return "日常记录"


def analyze_asset(path: str, duration_ms: int) -> dict:
    """单素材分析：镜头列表 + 逐镜头标注 + 能量/BPM。"""
    cuts = detect_scenes(path)
    duration_s = duration_ms / 1000
    cuts = [c for c in cuts if c < duration_s - 0.5] or [0.0]
    scenes = []
    for i, start in enumerate(cuts):
        end = cuts[i + 1] if i + 1 < len(cuts) else duration_s
        if end - start < 1.0:  # 碎闪镜头并入前一段
            continue
        scenes.append({"index": i, "startMs": int(start * 1000), "endMs": int(end * 1000)})
    if not scenes:
        scenes = [{"index": 0, "startMs": 0, "endMs": duration_ms}]

    bright = avg_brightness(path)
    cuts_per_min = len(cuts) / max(duration_s / 60.0, 0.1)
    label = scene_label(bright, cuts_per_min)
    for s in scenes:
        s["label"] = label

    curve = audio_energy_curve(path)
    bpm = estimate_bpm(curve)

    return {
        "scenes": scenes,
        "sceneSummary": {"label": label, "count": len(scenes), "brightness": bright,
                         "cutsPerMin": round(cuts_per_min, 2)},
        "energyCurve": curve,
        "tempoBpm": bpm,
    }


def mood_mix(assets_results: list[dict]) -> dict[str, float]:
    """整体情绪构成：按三标签的镜头时长占比。"""
    total = 0.0
    acc: dict[str, float] = {}
    for r in assets_results:
        for s in r["scenes"]:
            d = (s["endMs"] - s["startMs"]) / 1000
            acc[s["label"]] = acc.get(s["label"], 0.0) + d
            total += d
    if total <= 0:
        return {"日常记录": 1.0}
    return {k: round(v / total, 3) for k, v in sorted(acc.items(), key=lambda kv: -kv[1])}


def overall_bpm(assets_results: list[dict]) -> float | None:
    bpms = [r["tempoBpm"] for r in assets_results if r.get("tempoBpm")]
    if not bpms:
        return None
    return float(round(sum(bpms) / len(bpms), 1))


def pace_advice(bpm: float | None, label_counts: dict[str, int]) -> str:
    """节奏建议文案（对应原型「中慢速 · 约 82 BPM，适合叠化长镜头」）。"""
    if bpm is None:
        return "素材节奏信息不足，按舒缓长镜头处理"
    if bpm < 95:
        return f"中慢速 · 约 {bpm:.0f} BPM，适合叠化长镜头，不建议快闪卡点"
    if bpm < 130:
        return f"中速 · 约 {bpm:.0f} BPM，叠化与硬切均可，可在高点卡点"
    return f"快节奏 · 约 {bpm:.0f} BPM，适合动态剪辑与节拍对齐"


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)
