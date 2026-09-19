"""字幕配音（TTS）：双引擎——edge-tts（微软神经语音，拟人，需联网）与 macOS say（离线兜底）。

SHANJIAN_TTS_ENGINE=auto|edge|say，默认 auto：装了 edge-tts 就用神经音色，
合成失败自动退回 say；显式指定 edge 时失败直接报错（便于发现网络问题）。
文件容器随引擎（say=aiff / edge=mp3），渲染端用 ffprobe 探时长 + ffmpeg 解码，与格式无关。
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

_VOICE_RE = re.compile(r"^(.+?)\s{2,}(zh_[A-Za-z]{2})\s+#\s*(.*)$")
_PREFERRED_SAY = ["Yu-shu", "Tingting", "Eddy (中文（中国大陆）)", "Flo (中文（中国大陆）)", "Meijia"]

# edge 神经音色的中文人设说明（下拉框展示用）
_EDGE_LABELS = {
    "zh-CN-YunxiNeural": "云希 · 年轻男声，自然闲聊感（推荐）",
    "zh-CN-XiaoxiaoNeural": "晓晓 · 年轻女声，温暖自然（推荐）",
    "zh-CN-YunjianNeural": "云健 · 男声，运动解说风",
    "zh-CN-YunyangNeural": "云扬 · 男声，新闻播音风",
    "zh-CN-XiaoyiNeural": "晓伊 · 女声，活泼甜美",
    "zh-CN-liaoning-XiaobeiNeural": "晓北 · 东北口音女声，自带喜感",
    "zh-TW-HsiaoChenNeural": "曉臻 · 台湾腔女声",
    "zh-HK-HiuMaanNeural": "曉曼 · 粤语女声",
}
_EDGE_DEFAULT = "zh-CN-YunxiNeural"


# ---------------- 引擎选择 ----------------

def _edge_importable() -> bool:
    try:
        import edge_tts  # noqa: F401
        return True
    except Exception:
        return False


def engine() -> str:
    want = (os.environ.get("SHANJIAN_TTS_ENGINE") or "auto").strip().lower()
    if want in ("edge", "say"):
        return want
    return "edge" if _edge_importable() else "say"


# ---------------- say（macOS 本地，离线） ----------------

def _say_list() -> list[dict]:
    try:
        out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, timeout=15).stdout
    except Exception:
        return []
    voices = []
    for line in out.splitlines():
        m = _VOICE_RE.match(line.strip())
        if m and m.group(2).lower().startswith("zh"):
            voices.append({"name": m.group(1).strip(), "locale": m.group(2), "comment": m.group(3).strip()})
    return voices


def _say_default(voices: list[dict] | None = None) -> str:
    voices = voices if voices is not None else _say_list()
    names = {v["name"] for v in voices}
    for pref in _PREFERRED_SAY:
        if pref in names:
            return pref
    return voices[0]["name"] if voices else ""


def _say_synth(out_path: Path, text: str, voice: str, rate: float) -> Path:
    voices = _say_list()
    names = {v["name"] for v in voices}
    v = voice if voice in names else _say_default(voices)   # 旧 EDL 里可能存着别的引擎的音色名
    if not v:
        raise RuntimeError("系统没有可用的中文语音（say -v ?）")
    cmd = ["say", "-v", v, "-o", str(out_path)]
    if abs(rate - 1.0) > 0.03:
        cmd += ["-r", str(max(120, round(180 * rate)))]   # say 基准约 180 字/分
    cmd.append(text)
    subprocess.run(cmd, check=True, timeout=120)
    return out_path


# ---------------- edge-tts（微软神经语音，拟人） ----------------

_edge_cache: dict = {"ts": 0.0, "names": None}


def _edge_names() -> set[str]:
    """可用 edge 中文音色名（缓存 1 小时；查询失败返回空集=跳过音色名校验）。"""
    if _edge_cache["names"] is None or time.time() - _edge_cache["ts"] > 3600:
        try:
            import asyncio
            import edge_tts
            data = asyncio.run(edge_tts.list_voices())
            names = {v["ShortName"] for v in data if str(v.get("Locale", "")).lower().startswith("zh")}
            if names:
                _edge_cache.update(ts=time.time(), names=names)
        except Exception:
            pass
    return _edge_cache["names"] or set()


def _edge_rate(rate: float) -> str:
    pct = int(round((rate - 1.0) * 100))
    pct = max(-50, min(60, pct))
    return f"+{pct}%" if pct >= 0 else f"{pct}%"


def _edge_synth(out_path: Path, text: str, voice: str, rate: float) -> Path:
    import asyncio
    import edge_tts
    names = _edge_names()
    v = voice if (not names or voice in names) else _EDGE_DEFAULT   # 未知音色名回默认
    async def _run():
        await edge_tts.Communicate(text, v, rate=_edge_rate(rate)).save(str(out_path))
    asyncio.run(_run())
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError("edge-tts 未产出音频")
    return out_path


def _edge_list() -> list[dict]:
    names = _edge_names()
    if not names:
        return []
    known = [n for n in _EDGE_LABELS if n in names]
    rest = sorted(names - set(_EDGE_LABELS))
    return [{"name": n, "locale": n[:5], "comment": _EDGE_LABELS.get(n, "微软神经音色")}
            for n in known + rest]


# ---------------- 对外 API（与引擎无关） ----------------

def list_voices() -> list[dict]:
    if engine() == "edge":
        voices = _edge_list()
        if voices:
            return voices
    return _say_list()


def default_voice() -> str:
    if engine() == "edge":
        names = _edge_names()
        if names:
            return _EDGE_DEFAULT if _EDGE_DEFAULT in names else sorted(names)[0]
    return _say_default()


def synth(out_path: Path, text: str, voice: str = "", rate: float = 1.0) -> Path:
    """合成一段语音。voice=引擎音色名（空=引擎默认），rate=语速倍率。文本截断 200 字。"""
    text = (text or "").strip()[:200]
    if not text:
        raise RuntimeError("配音文本为空")
    out_path = Path(out_path)
    want = engine()
    if want == "edge":
        try:
            return _edge_synth(out_path, text, voice or "", rate)
        except Exception:
            if os.environ.get("SHANJIAN_TTS_ENGINE", "auto").strip().lower() == "edge":
                raise          # 显式指定 edge：把网络等真实错误暴露出来
            # auto：静默退回离线 say，保证出片不中断
    return _say_synth(out_path, text, voice or "", rate)
