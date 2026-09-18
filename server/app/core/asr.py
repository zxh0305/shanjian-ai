"""本地语音识别 → 字幕：faster-whisper（CPU int8，模型首次使用时自动下载）。

ASR 只做一件事：把媒体文件音轨在指定时间窗内的语音转成 [{startMs,endMs,text}]，
时间相对窗口起点（毫秒）。窗口抽取用 ffmpeg 转 16k 单声道 wav，稳定且省内存。
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from ..config import settings

_model = None
_model_name: str | None = None


def _get_model():
    global _model, _model_name
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")  # 国内直连 HF 易超时
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")               # Xet 协议不走镜像，会 401
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise RuntimeError(
            "未安装 faster-whisper，无法识别字幕（cd server && .venv/bin/pip install faster-whisper）") from e
    name = os.environ.get("SHANJIAN_ASR_MODEL", "base")
    if _model is None or _model_name != name:
        print(f"[ASR] 加载 whisper 模型 {name}（首次使用会下载，请稍候）...", flush=True)
        _model = WhisperModel(name, device="cpu", compute_type="int8")
        _model_name = name
    return _model


def has_audio_track(media_path) -> bool:
    try:
        out = subprocess.run(
            [settings.ffprobe, "-v", "error", "-print_format", "json", "-show_streams",
             "-select_streams", "a", str(media_path)],
            capture_output=True, text=True, timeout=30).stdout
        import json
        return bool(json.loads(out).get("streams"))
    except Exception:
        return True


# 引导简体的提示词——同时用来过滤「把提示词当识别内容」的幻觉
_SIMPLIFY_HINT = "以下是普通话句子，请用简体中文输出。"
# whisper 在静音/噪声上的常见幻觉
_HALLUCINATIONS = ("请用简体中文输出", "谢谢观看", "请订阅", "下次再见", "请不吝点赞",
                   "amigos", "subtitles", "thank you for watching")


def _clean(text: str) -> str:
    t = (text or "").strip().replace(" ", "")
    if not t or t in _SIMPLIFY_HINT or _SIMPLIFY_HINT in t:
        return ""
    low = t.lower()
    if len(t) < 30 and any(h in low for h in _HALLUCINATIONS):
        return ""
    return t


def _transcribe(wav: Path) -> list[dict]:
    segments, _info = _get_model().transcribe(
        str(wav), language="zh", vad_filter=True, beam_size=5,
        initial_prompt=_SIMPLIFY_HINT)
    out = []
    for s in segments:
        text = _clean(s.text)
        if text:
            out.append({"startMs": int(s.start * 1000), "endMs": int(s.end * 1000), "text": text})
    return out


def transcribe_window(media_path, start_ms: int, end_ms: int) -> list[dict]:
    """识别 media_path 音轨 [start_ms, end_ms) 窗口内的语音；返回相对窗口的毫秒时间。"""
    if not has_audio_track(media_path):
        return []
    dur_s = max(0.5, (end_ms - start_ms) / 1000)
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "a.wav"
        r = subprocess.run(
            [settings.ffmpeg, "-y", "-v", "error",
             "-ss", f"{start_ms / 1000:.3f}", "-t", f"{dur_s:.3f}", "-i", str(media_path),
             "-vn", "-ac", "1", "-ar", "16000", str(wav)],
            capture_output=True, text=True, timeout=180)
        if r.returncode != 0 or not wav.exists():
            return []
        global _model
        try:
            return _transcribe(wav)
        except Exception:
            # 偶发失败（如模型文件下载竞态）→ 重置模型重试一次
            _model = None
            return _transcribe(wav)
