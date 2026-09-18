"""工具层 · 首批具体工具：薄壳包装 core/ 纯函数实现（FastAPI 与未来的 MCP 共用一套实现）。

命名规范：动词_宾语 snake_case，一个工具 = 一个可独立验证的原子操作。
"""
from __future__ import annotations

import json

from ..core import asr as core_asr
from ..core import probe as core_probe
from ..core import tts as core_tts
from .base import BaseTool


class ProbeMediaTool(BaseTool):
    name = "probe_media"
    description = "读取媒体文件元数据：时长、分辨率、帧率、音视频流信息。上传后摸底用。"
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "媒体文件绝对路径"}},
        "required": ["path"],
    }

    def execute(self, path: str) -> str:
        meta = core_probe.probe(path)
        meta["durationMs"] = meta.get("duration_ms")
        return json.dumps(meta, ensure_ascii=False)


class TranscribeAudioTool(BaseTool):
    name = "transcribe_audio"
    description = "识别媒体文件指定时间窗内的中文语音，返回带毫秒时间戳的文本段落（相对窗口起点）。"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "媒体文件绝对路径"},
            "start_ms": {"type": "integer", "description": "窗口起点（毫秒）", "default": 0},
            "end_ms": {"type": "integer", "description": "窗口终点（毫秒）"},
        },
        "required": ["path", "end_ms"],
    }

    def execute(self, path: str, start_ms: int = 0, end_ms: int = 0) -> str:
        segs = core_asr.transcribe_window(path, start_ms, end_ms)
        return json.dumps(segs, ensure_ascii=False)


class SynthTtsTool(BaseTool):
    name = "synth_tts"
    description = "把一段中文文本合成为语音文件（aiff），返回文件路径。可选音色与语速倍率。"
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要朗读的文本（≤200 字）"},
            "out_path": {"type": "string", "description": "输出文件路径（.aiff）"},
            "voice": {"type": "string", "description": "音色名，空=默认中文音色", "default": ""},
            "rate": {"type": "number", "description": "语速倍率 0.6~1.6，1.0=正常", "default": 1.0},
        },
        "required": ["text", "out_path"],
    }

    def execute(self, text: str, out_path: str, voice: str = "", rate: float = 1.0) -> str:
        from pathlib import Path
        p = core_tts.synth(Path(out_path), text, voice or None, rate)
        return str(p)


# 声明式组合：智能体按需引用
MEDIA_TOOLS = None  # 由具体 agent 组合，避免模块级实例化副作用
