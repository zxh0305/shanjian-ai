"""字幕配音（TTS）：用 macOS 内置 say 合成中文语音——离线、免费、无需密钥。

新式神经音色（Eddy/Flo/Grandma 等）质量不错；也兼容经典音色（Tingting 等）。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

_VOICE_RE = re.compile(r"^(.+?)\s{2,}(zh_[A-Za-z]{2})\s+#\s*(.*)$")

# 音色优先级：无备注偏好的话按这个顺序挑默认
_PREFERRED = ["Yu-shu", "Tingting", "Eddy (中文（中国大陆）)", "Flo (中文（中国大陆）)", "Meijia"]


def list_voices() -> list[dict]:
    """列出可用中文音色：[{name, locale, comment}]。"""
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


def default_voice() -> str:
    voices = list_voices()
    names = {v["name"] for v in voices}
    for pref in _PREFERRED:
        if pref in names:
            return pref
    return voices[0]["name"] if voices else ""


def synth(out_path: Path, text: str, voice: str = "", rate: float = 1.0) -> Path:
    """把一段文字合成语音文件（aiff，44.1k）。rate 为语速倍率，文本截断到 200 字。"""
    voice = voice or default_voice()
    if not voice:
        raise RuntimeError("系统没有可用的中文语音（say -v ?）")
    cmd = ["say", "-v", voice, "-o", str(out_path)]
    if abs(rate - 1.0) > 0.03:
        cmd += ["-r", str(max(120, round(180 * rate)))]   # say 基准约 180 字/分
    cmd.append((text or "").strip()[:200])
    subprocess.run(cmd, check=True, timeout=120)
    return out_path
