"""MCP 薄壳 · 媒体渲染领域（写、长耗时）：EDL 渲染成片与 TTS 配音。

实现全部在 core/（render/tts），本文件零业务。注意 render_edl 会真实写
data/renders/ 并占用 FFmpeg 数秒到数分钟，外部宿主调用时请耐心等待。
注册示例（Claude Code）：
    claude mcp add shanjian-media-render -- /path/to/server/scripts/mcp_render.sh
"""
from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ...core import render as core_render
from ...core import tts as core_tts
from ...schemas.edl import EDL

mcp = FastMCP("shanjian-media-render")


@mcp.tool()
def render_edl(project_id: int, edl_json: str, height: int = 1080, fps: int = 30) -> str:
    """按 EDL（剪辑决策列表 JSON）渲染竖屏成片，返回 {fileKey, sizeBytes, elapsedMs} 等。

    height 须为 720/1080/2160，fps 须为 30/60；EDL 字段规格见 docs/EDL-spec.md。
    """
    edl = EDL(**json.loads(edl_json))
    result = core_render.render_edl(project_id, edl, height, fps)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def synth_tts(text: str, out_path: str, voice: str = "", rate: float = 1.0) -> str:
    """把一段中文文本合成为语音文件（aiff），返回文件路径。voice=音色名，rate=语速倍率 0.6~1.6。"""
    return str(core_tts.synth(Path(out_path), text, voice or None, rate))


if __name__ == "__main__":
    mcp.run()
