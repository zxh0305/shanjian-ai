"""MCP 薄壳 · 媒体分析领域（只读）：把本机剪辑能力以标准协议暴露给外部宿主（Claude 等）。

一个领域一个 server、工具=原子操作、动词_宾语命名；实现全部下沉 core/，本文件零业务。
stdio 传输适合本地个人机。注册示例（Claude Code）：
    claude mcp add shanjian-media-analysis -- /path/to/server/scripts/mcp_analysis.sh
"""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from ...core import asr as core_asr
from ...core import llm as core_llm
from ...core import probe as core_probe

mcp = FastMCP("shanjian-media-analysis")


@mcp.tool()
def probe_media(path: str) -> str:
    """读取媒体文件元数据：时长、分辨率、帧率、音视频流信息。"""
    return json.dumps(core_probe.probe(path), ensure_ascii=False)


@mcp.tool()
def extract_keyframes(path: str, count: int = 6) -> str:
    """从视频均匀抽取 N 帧关键帧（带时间戳），返回 [{path, timeMs}] 供视觉理解。"""
    return json.dumps(core_llm.extract_key_frames(path, count), ensure_ascii=False)


@mcp.tool()
def transcribe_audio(path: str, start_ms: int = 0, end_ms: int = 0) -> str:
    """识别媒体文件指定时间窗内的中文语音，返回带毫秒时间戳的文本段落。"""
    return json.dumps(core_asr.transcribe_window(path, start_ms, end_ms), ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
