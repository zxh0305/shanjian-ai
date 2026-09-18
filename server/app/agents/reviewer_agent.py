"""审片官智能体：抽帧 + 客观摘要 → LLM 打分，产出 verdict。

对应原 pipeline._review_export；客观指标（片段时长分布、朗读密度）由本模块计算后
与抽帧一起交给 LLM，评分标准来自 prompts/reviewer.py。
"""
from __future__ import annotations

import base64
import json
import subprocess
import tempfile
from pathlib import Path

from ..config import settings
from ..prompts import reviewer as reviewer_prompts
from ..schemas.edl import EDL, TransitionType
from ..core import llm as qwen_vl
from .base import AgentState, BaseAgent

TRANS_NAMES = {"dissolve": "叠化", "push_in": "推近", "iris": "划像", "flash": "闪白", "none": "硬切"}


def extract_frames(video_path, count: int = 4) -> list[str]:
    """从成片均匀抽帧，返回 base64 列表。"""
    try:
        dur = float(subprocess.run(
            [settings.ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
             str(video_path)], capture_output=True, text=True, timeout=30).stdout.strip() or 1)
    except Exception:
        dur = 1.0
    frames = []
    with tempfile.TemporaryDirectory() as td:
        for k in range(count):
            jpg = Path(td) / f"f{k}.jpg"
            r = subprocess.run(
                [settings.ffmpeg, "-y", "-v", "error", "-ss", f"{dur * (k + 0.5) / count:.2f}",
                 "-i", str(video_path), "-frames:v", "1", "-vf", "scale=480:-2", str(jpg)],
                capture_output=True, timeout=30)
            if r.returncode == 0 and jpg.exists():
                frames.append(base64.b64encode(jpg.read_bytes()).decode())
    return frames


def review_summary(edl: EDL) -> str:
    """给审查的客观摘要：片段节奏 + 字幕 + 转场 + 客观指标。"""
    durs = [round((c.outMs - c.inMs) / 1000, 1) for c in edl.clips]
    subs = [c for c in edl.captions if c.style == "subtitle"]
    trans = [TRANS_NAMES.get(getattr(t.type, "value", t.type), str(t.type))
             for t in edl.transitions if t.type != TransitionType.none]
    lines = [
        f"片段时长(s)：{durs} · 总长 {sum(durs):.1f}s · 最短 {min(durs) if durs else 0}s / 最长 {max(durs) if durs else 0}s",
        f"转场：{'、'.join(trans) if trans else '硬切'}",
    ]
    if subs:
        lines.append(f"字幕/旁白 {len(subs)} 条，逐条(字/秒朗读密度)：")
        density = []
        for c in subs:
            w = max((c.endMs - c.startMs) / 1000, 0.5)
            density.append(round(len(c.text) / w, 1))
            lines.append(f"  [{c.startMs / 1000:.1f}-{c.endMs / 1000:.1f}s]{c.text}")
        over = sum(1 for d in density if d > 4.2)
        if over:
            lines.append(f"客观提示：{over} 条旁白朗读密度偏高（可能语速过快）")
    return "\n".join(lines)


class ReviewerAgent(BaseAgent):
    """一步智能体：抽帧→摘要→打分。结果 = {score, pass, comment, suggestions} 或 {"error": ...}。"""

    name = "reviewer"
    max_steps = 2

    def __init__(self, on_event=None):
        super().__init__(on_event=on_event)
        self.trace: dict = {}

    def step(self, request) -> None:
        edl, export_path, *rest = request
        user_id = rest[0] if rest else 1
        self.emit("AI 审查：抽帧分析成片…")
        frames = extract_frames(export_path)
        if not frames:
            self.result = {"error": "抽帧失败，跳过审查"}
            self.state = AgentState.FINISHED
            return
        prompt = reviewer_prompts.review_prompt(review_summary(edl))
        self.result = qwen_vl.review_cut(frames, prompt, user_id=user_id)
        self.state = AgentState.FINISHED
