"""TTS 双引擎单测：引擎选择、语速换算、未知音色回退、say 兜底、口语化底线注入。"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS

os.environ.setdefault("SHANJIAN_DATA_DIR", tempfile.mkdtemp(prefix="shanjian_tts_"))

from app.core import tts  # noqa: E402


def test_engine_env_override(monkeypatch):
    monkeypatch.setenv("SHANJIAN_TTS_ENGINE", "say")
    assert tts.engine() == "say"
    monkeypatch.setenv("SHANJIAN_TTS_ENGINE", "edge")
    assert tts.engine() == "edge"
    monkeypatch.setenv("SHANJIAN_TTS_ENGINE", "auto")
    monkeypatch.setattr(tts, "_edge_importable", lambda: False)
    assert tts.engine() == "say"           # auto：未装 edge-tts → 离线兜底
    monkeypatch.setattr(tts, "_edge_importable", lambda: True)
    assert tts.engine() == "edge"


def test_edge_rate_conversion():
    assert tts._edge_rate(1.0) == "+0%"
    assert tts._edge_rate(1.15) == "+15%"
    assert tts._edge_rate(0.7) == "-30%"
    assert tts._edge_rate(1.9) == "+60%"    # 上限钳制
    assert tts._edge_rate(0.1) == "-50%"


def test_edge_synth_unknown_voice_falls_back(monkeypatch, tmp_path):
    """旧 EDL 里存的 say 音色名在 edge 引擎下自动回默认，不报错。"""
    monkeypatch.setattr(tts, "_edge_names", lambda: {"zh-CN-YunxiNeural"})
    captured = {}

    class _FakeComm:
        def __init__(self, text, voice, rate=""):
            captured.update(voice=voice, rate=rate)

        async def save(self, p):
            Path(p).write_bytes(b"mp3bytes")

    import sys, types
    fake = types.SimpleNamespace(Communicate=_FakeComm)
    monkeypatch.setitem(sys.modules, "edge_tts", fake)

    out = tts._edge_synth(tmp_path / "v.mp3", "测试", "Tingting", 1.15)
    assert out.exists() and captured["voice"] == "zh-CN-YunxiNeural"   # 未知音色 → 默认
    assert captured["rate"] == "+15%"


def test_synth_falls_back_to_say_when_edge_fails(monkeypatch, tmp_path):
    """auto 引擎下 edge 失败静默退回 say；显式 edge 则抛错。"""
    def _boom(*a, **k):
        raise RuntimeError("网络不可达")
    monkeypatch.setenv("SHANJIAN_TTS_ENGINE", "auto")
    monkeypatch.setattr(tts, "_edge_synth", _boom)
    def _fake_say(p, t, v, r):
        p.write_bytes(b"aiff")
        return p
    monkeypatch.setattr(tts, "_say_synth", _fake_say)

    out = tts.synth(tmp_path / "a.aiff", "你好", "", 1.0)
    assert out.exists()

    monkeypatch.setenv("SHANJIAN_TTS_ENGINE", "edge")
    try:
        tts.synth(tmp_path / "b.mp3", "你好", "", 1.0)
        raise AssertionError("显式 edge 失败应抛错")
    except RuntimeError as e:
        assert "网络" in str(e)


def test_narration_style_includes_baseline():
    """所有文案风格都追加「口语化底线」，反 AI 味规则随 skill 资产生效。"""
    from app.skills import loader
    style = loader.narration_style_text("humor")
    assert "说人话底线" in style and "镜头腔" in style
    assert "玩梗" in style                    # 风格本体仍在
    assert loader.narration_style_text("warm") != style   # 不同风格内容不同


def test_say_synth_unknown_voice_guards(monkeypatch, tmp_path):
    """edge 时代切回 say 引擎时，旧 EDL 里的 edge 音色名回退到 say 默认。"""
    monkeypatch.setattr(tts, "_say_list",
                        lambda: [{"name": "Tingting", "locale": "zh_CN", "comment": ""}])
    ran = {}
    def fake_run(cmd, check, timeout):
        ran["voice"] = cmd[cmd.index("-v") + 1]
        Path(cmd[cmd.index("-o") + 1]).write_bytes(b"aiff")
        return NS(returncode=0)
    import subprocess as sp
    monkeypatch.setattr(sp, "run", fake_run)
    out = tts._say_synth(tmp_path / "v.aiff", "测试", "zh-CN-YunxiNeural", 1.0)
    assert out.exists() and ran["voice"] == "Tingting"