"""ffprobe 封装：读取素材元数据（定稿 W1–W2 任务）。"""
from __future__ import annotations

import json
import subprocess

from ..config import settings


class ProbeError(RuntimeError):
    pass


def probe_duration(path: str) -> int:
    """任意媒体（音频/视频）的时长，毫秒。"""
    cmd = [
        settings.ffprobe, "-v", "error", "-print_format", "json",
        "-show_format", path,
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
    except FileNotFoundError as e:
        raise ProbeError(f"找不到 {settings.ffprobe}，请先安装 ffmpeg（brew install ffmpeg）") from e
    except subprocess.CalledProcessError as e:
        raise ProbeError(f"ffprobe 失败: {e.stderr.strip()[:200]}") from e
    data = json.loads(out.stdout)
    duration_ms = int(round(float(data.get("format", {}).get("duration", 0)) * 1000))
    if duration_ms <= 0:
        raise ProbeError("读不到时长")
    return duration_ms


def probe(path: str) -> dict:
    """返回视频流元数据：duration_ms / width / height / fps / has_audio。"""
    cmd = [
        settings.ffprobe, "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", path,
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
    except FileNotFoundError as e:
        raise ProbeError(f"找不到 {settings.ffprobe}，请先安装 ffmpeg（brew install ffmpeg）") from e
    except subprocess.CalledProcessError as e:
        raise ProbeError(f"ffprobe 失败: {e.stderr.strip()[:200]}") from e

    data = json.loads(out.stdout)
    v_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if v_stream is None:
        raise ProbeError("文件中没有视频流")

    # duration 优先取 format 层；流层的 num/den 兜底
    duration_ms = int(round(float(data.get("format", {}).get("duration", 0)) * 1000))
    if duration_ms <= 0:
        num, den = v_stream.get("duration") or 0, None
        duration_ms = int(round(float(num or 0) * 1000))
    if duration_ms <= 0:
        rate = v_stream.get("avg_frame_rate", "30/1")
        n, d = rate.split("/")
        nb, db = v_stream.get("nb_frames") or 0, 1
        duration_ms = int(int(nb) / (float(n) / float(d)) * 1000) if nb and float(d) else 0

    num, den = (v_stream.get("avg_frame_rate") or v_stream.get("r_frame_rate") or "30/1").split("/")
    fps = round(float(num) / float(den), 3) if float(den) else 30.0

    creation = (data.get("format", {}).get("tags", {}).get("creation_time")
                or v_stream.get("tags", {}).get("creation_time"))

    return {
        "duration_ms": duration_ms,
        "width": int(v_stream["width"]),
        "height": int(v_stream["height"]),
        "fps": fps,
        "size_bytes": int(data.get("format", {}).get("size", 0)),
        "shot_at": creation,
        "has_audio": any(s.get("codec_type") == "audio" for s in data.get("streams", [])),
    }
