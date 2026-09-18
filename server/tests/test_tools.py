"""工具层三件套单测：schema 输出、按名分发、异常兜底、真实工具冒烟。"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("SHANJIAN_DATA_DIR", tempfile.mkdtemp(prefix="shanjian_tools_"))

from app.tools.base import BaseTool, ToolCollection, ToolResult  # noqa: E402
from app.tools.media_tools import ProbeMediaTool, SynthTtsTool  # noqa: E402

HAS_FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")


class _EchoTool(BaseTool):
    name = "echo"
    description = "回声测试"
    parameters = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}

    def execute(self, text: str) -> str:
        if text == "boom":
            raise ValueError("炸了")
        return f"echo:{text}"


def test_schema_and_dispatch():
    col = ToolCollection(_EchoTool(), ProbeMediaTool())
    params = col.to_params()
    assert params[0]["function"]["name"] == "echo"
    assert params[0]["function"]["parameters"]["required"] == ["text"]
    assert col.execute("echo", {"text": "hi"}).output == "echo:hi"
    assert col.execute("nope").error  # 未注册工具
    assert col.execute("echo", {"text": "boom"}).error.startswith("ValueError")  # 异常兜底


def test_result_concat():
    assert (ToolResult.success("a") + ToolResult.success("b")).output == "a\nb"
    assert not ToolResult.failure("x")


@pytest.mark.skipif(not HAS_FFMPEG, reason="需要 ffmpeg")
def test_probe_media_tool_real():
    tmp = Path(tempfile.mkdtemp())
    v = tmp / "a.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "testsrc=duration=2:size=640x360:rate=30", str(v)], check=True)
    r = ProbeMediaTool()(path=str(v))
    assert r and '"duration_ms": 2000' in r.output.replace("\n", "")


@pytest.mark.skipif(not shutil.which("say"), reason="需要 macOS say")
def test_synth_tts_tool_real():
    tmp = Path(tempfile.mkdtemp())
    r = SynthTtsTool()(text="工具层测试", out_path=str(tmp / "t.aiff"))
    assert r and Path(r.output).exists() and Path(r.output).stat().st_size > 1000
