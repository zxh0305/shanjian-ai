"""业务服务 · 成片流水线（字幕/配音/文案/审查）。

从 routes/pipeline 下沉：这些是剪辑业务编排，路由层只做校验与提交任务。
公开函数去掉下划线前缀；pipeline 内的调用点同步改名。
"""
from __future__ import annotations

import base64
import json
import subprocess
import tempfile
from pathlib import Path

from pydantic import BaseModel

from ..config import settings
from ..core.asr import transcribe_window
from ..repositories import analysis as analysis_repo
from ..repositories import assets as assets_repo
from ..schemas.edl import EDL, Caption, TransitionType
from ..core import llm as qwen_vl

def gen_subtitles_for_edl(project_id: int, edl: EDL, job=None, p0: float = 0.0, p1: float = 1.0) -> list[Caption]:
    """按 EDL 各片段的保留区间逐段 ASR，映射到时间线坐标，返回 subtitle 字幕列表。"""
    if not edl.clips:
        return []
    _rows = {a["id"]: a for a in assets_repo.for_project(project_id)}
    assets = {cid: _rows[cid] for cid in {c.assetId for c in edl.clips} if cid in _rows}
    trans = {t.afterClip: t for t in edl.transitions}
    starts: list[int] = []
    s = 0
    for i, c in enumerate(edl.clips):
        starts.append(s)
        s += c.outMs - c.inMs
        t = trans.get(i + 1)
        if t and t.type != TransitionType.none:
            s -= t.durMs
    subs: list[Caption] = []
    for i, c in enumerate(edl.clips):
        a = assets.get(c.assetId)
        if not a:
            continue
        if job:
            job["message"] = f"识别字幕 {i + 1}/{len(edl.clips)}"
            job["progress"] = round(p0 + (p1 - p0) * i / len(edl.clips), 2)
        segs = transcribe_window(settings.assets_dir / a["file_path"], c.inMs, c.outMs)
        for g in segs:
            if not g["text"]:
                continue
            start = starts[i] + g["startMs"]
            end = min(starts[i] + g["endMs"], starts[i] + (c.outMs - c.inMs))
            if end - start < 200:
                continue
            subs.append(Caption(text=g["text"], startMs=start, endMs=end, style="subtitle"))
    return subs

from ..prompts.editor import NARRATION_STYLE_TEXT as NARRATION_STYLES  # noqa: E402 单源于提示词资产

def timeline_starts_ms(edl: EDL) -> list[int]:
    trans = {t.afterClip: t for t in edl.transitions}
    starts, s = [], 0
    for i, c in enumerate(edl.clips):
        starts.append(s)
        s += c.outMs - c.inMs
        t = trans.get(i + 1)
        if t and t.type != TransitionType.none:
            s -= t.durMs
    return starts

def gen_narration_subs(user_id: int, project_id: int, edl: EDL, style_text: str,
                        job=None) -> list[dict]:
    rep = analysis_repo.get_done(project_id)
    ana_by_asset = {}
    if rep:
        for a in json.loads(rep["scene_tags"] or "[]"):
            ana_by_asset[a.get("assetId")] = a
    assets = {a["id"]: a for a in assets_repo.for_project(project_id)}
    starts = timeline_starts_ms(edl)
    clips_info = []
    for i, c in enumerate(edl.clips):
        ana = ana_by_asset.get(c.assetId, {})
        vl = ana.get("vlScene", {}) or {}
        desc = vl.get("description") or (ana.get("sceneSummary") or {}).get("label") or \
            (assets.get(c.assetId) or {}).get("file_name", "")
        clips_info.append({"index": i + 1, "durationS": round((c.outMs - c.inMs) / 1000, 1),
                           "description": desc, "note": c.note or ""})
    if job:
        job["message"] = "AI 正在撰写风格文案"
    res = qwen_vl.generate_narration(clips_info, style_text, edl.meta.title or "", user_id=user_id)
    if "error" in res:
        raise RuntimeError(res["error"])
    # 排期：一句话对应一段画面（不跨镜头）；窗口不够长由渲染端自动加速朗读贴合；
    # 转场会让相邻片段窗口交叠 → 每句结束截到下一句开始之前，杜绝字幕/配音重叠
    raw = []
    for i, (c, line) in enumerate(zip(edl.clips, res["lines"])):
        line = (line or "").strip()
        if not line:
            continue
        start = starts[i] + 100
        end = starts[i] + (c.outMs - c.inMs) - 60
        raw.append((start, max(end, start + 500), line))
    subs = []
    for k, (start, end, line) in enumerate(raw):
        if k + 1 < len(raw):
            end = min(end, raw[k + 1][0] - 80)
        if end - start < 400:
            continue
        subs.append({"text": line, "startMs": start, "endMs": end})
    return subs

def apply_vlog_subs(user_id: int, project_id: int, edl: EDL, sub_style: str,
                     use_llm: bool, job=None, original_voice: str = "auto"):
    """Vlog 字幕 + 配音开关；返回 (subs, narrated, 错误或None)。"""
    try:
        narrated = False
        if sub_style and sub_style != "asr" and use_llm:
            subs = [Caption(text=x["text"], startMs=x["startMs"], endMs=x["endMs"], style="subtitle")
                    for x in gen_narration_subs(user_id, project_id, edl,
                                                 NARRATION_STYLES.get(sub_style, NARRATION_STYLES["humor"]),
                                                 job)]
            narrated = bool(subs)
        else:
            subs = gen_subtitles_for_edl(project_id, edl, job, 0.0, 0.35)
            if not subs and use_llm:
                # 识别不到语音（画面无口播）→ 自动改用 AI 按画面生成文案兜底
                subs = [Caption(text=x["text"], startMs=x["startMs"], endMs=x["endMs"], style="subtitle")
                        for x in gen_narration_subs(user_id, project_id, edl,
                                                     NARRATION_STYLES["humor"], job)]
                narrated = bool(subs)
        edl.captions = [c for c in edl.captions if c.style != "subtitle"] + subs
        # 配音默认只给「AI 文案/兜底旁白」开；原话字幕的原声本身就是配音
        edl.audio.ttsEnabled = bool(narrated)
        # 原声 auto：旁白配音开启时自动关掉原声，避免两个声音打架
        if narrated and original_voice == "auto":
            edl.audio.keepOriginal = False
        print(f"[字幕] Vlog 生成 {len(subs)} 条（配音{'已开启' if narrated else '关闭，原声即配音'}"
              f"{'，原声已自动关闭' if narrated and original_voice == 'auto' and edl.audio.keepOriginal is False else ''}）：", flush=True)
        for c in subs:
            print(f"  [{c.startMs / 1000:.1f}-{c.endMs / 1000:.1f}s] {c.text}", flush=True)
        return subs, narrated, None
    except Exception as e:
        import traceback
        traceback.print_exc()
        return [], False, f"Vlog 字幕生成失败：{str(e)[:80]}；可到编辑器「文字」页手动添加"

