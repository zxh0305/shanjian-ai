"""AI 管线与渲染端点真实实现（W3–W7 MVP）。"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .. import db
from ..config import settings
from .auth import current_user, owned_project
from ..schemas.edl import EDL, Aspect, Audio, Caption, Clip, Meta, Transition, TransitionType, TransitionStyle, TargetDuration
from ..core import autocut, media_analysis as ma
from ..core.render import render_edl
from ..repositories import projects as projects_repo
from ..repositories import timelines as timelines_repo
from ..services import jobs, music_match
from ..services.cut_flow import (apply_vlog_subs, gen_narration_subs, gen_subtitles_for_edl,
                                 narration_style_text)
from ..agents.director import DirectorAgent
from ..agents.editor_agent import EditorAgent
from ..agents.runs.run import AgentRun
from ..core import llm as qwen_vl
from ..core import llm_config

router = APIRouter()

# project_id → job_id（分析/渲染各一，单用户内存态即可）
_analysis_jobs: dict[int, str] = {}
_render_jobs: dict[int, str] = {}


# ---------------- 分析 ----------------

def _run_analysis(job: dict, cancelled) -> None:
    project_id = job["_projectId"]
    uid = job.get("_userId", 1)
    assets = db.query(
        "SELECT * FROM assets WHERE project_id=? AND probe_status=1 ORDER BY id", (project_id,))
    if not assets:
        raise RuntimeError("没有已解析完成的素材，先等上传处理结束")
    db.execute(
        """INSERT INTO analysis_reports (project_id, status) VALUES (?,0)
           ON CONFLICT(project_id) DO UPDATE SET status=0, updated_at=datetime('now','localtime')""",
        (project_id,))

    results, total_steps = [], len(assets)
    use_vl = bool(llm_config.get_current_model(uid)["apiKey"])

    for i, a in enumerate(assets):
        if cancelled():
            job["status"] = "cancelled"
            return
        # 步骤1：本地信号分析（亮度/切镜/能量/BPM）
        job["message"] = f"信号分析 {i + 1}/{total_steps}"
        r = ma.analyze_asset(str(_asset_path(a)), a["duration_ms"])
        r["assetId"] = a["id"]

        # 步骤2：视觉大模型场景语义分析（当前所选模型）
        if use_vl:
            cur = llm_config.get_current_model(uid)
            cur_name = cur.get("name", "AI")
            job["message"] = f"AI 视觉理解 {i + 1}/{total_steps}（{cur_name}）"
            print(f"[AI] 视觉分析 素材{a['id']} → {cur_name}({cur.get('vl_model','?')}) ...", flush=True)
            try:
                frames = qwen_vl.extract_key_frames(str(_asset_path(a)), count=3)
                if frames:
                    t0 = time.time()
                    vl_result = qwen_vl.analyze_scenes_with_vl(str(_asset_path(a)), frames, user_id=uid)
                    dt = time.time() - t0
                    if "error" in vl_result:
                        print(f"[AI] ✗ 素材{a['id']} 分析失败({dt:.1f}s): {vl_result['error'][:120]}", flush=True)
                    else:
                        print(f"[AI] ✓ 素材{a['id']} 分析成功({dt:.1f}s): "
                              f"{vl_result.get('scene_type','?')} - {vl_result.get('description','')[:60]}", flush=True)
                    r["vlScene"] = vl_result
                    qwen_vl.cleanup_frames(frames)
                else:
                    print(f"[AI] ✗ 素材{a['id']} 抽帧失败，跳过视觉分析", flush=True)
            except Exception as e:
                print(f"[AI] ✗ 素材{a['id']} 调用异常: {str(e)[:150]}", flush=True)
                r["vlScene"] = {"error": str(e)}
        else:
            print(f"[AI] 未配置模型密钥，素材{a['id']} 仅本地分析", flush=True)

        results.append(r)
        job["progress"] = round((i + 1) / total_steps, 2)

    job["message"] = "汇总分析结果"
    report = {
        "assets": [{k: r[k] for k in ("assetId", "scenes", "sceneSummary") if k in r} | 
                    ({"vlScene": r["vlScene"]} if "vlScene" in r else {}) for r in results],
        "moodMix": ma.mood_mix(results),
        "tempoBpm": ma.overall_bpm(results),
        "energyCurve": [r["energyCurve"] for r in results],
        "clipCount": len(assets),
        "totalDurationMs": sum(a["duration_ms"] for a in assets),
    }
    report["paceAdvice"] = ma.pace_advice(report["tempoBpm"],
                                          {k: sum(1 for r in results for s in r["scenes"] if s["label"] == k)
                                           for k in report["moodMix"]})
    db.execute(
        """UPDATE analysis_reports SET status=1, scene_tags=?, mood_mix=?, tempo_bpm=?,
           energy_curve=?, updated_at=datetime('now','localtime') WHERE project_id=?""",
        (json.dumps(report["assets"], ensure_ascii=False), json.dumps(report["moodMix"], ensure_ascii=False),
         report["tempoBpm"], json.dumps({"paceAdvice": report["paceAdvice"]}, ensure_ascii=False), project_id))
    job["result"] = report
    print(f"[分析] 完成：{len(assets)} 段素材 · {report['clipCount']} 个镜头 · "
          f"{len(report['moodMix'])} 类情绪 · BPM {report['tempoBpm'] or '无'}", flush=True)


def _asset_path(a: dict):
    from ..config import settings
    return settings.assets_dir / a["file_path"]


@router.post("/projects/{project_id}/analysis")
def start_analysis(project_id: int, request: Request = None):
    user = current_user(request)
    owned_project(user, project_id)
    if project_id in _analysis_jobs:
        old = jobs.get(_analysis_jobs[project_id])
        if old and old["status"] in ("queued", "running"):
            return {"jobId": old["jobId"], "status": old["status"], "message": "分析进行中"}

    def _fn(job, cancelled):
        job["_projectId"] = project_id
        job["_userId"] = user["id"]
        _run_analysis(job, cancelled)

    job = jobs.submit(_fn, "analysis")
    _analysis_jobs[project_id] = job["jobId"]
    return job


@router.get("/projects/{project_id}/analysis")
def get_analysis(project_id: int, request: Request = None):
    owned_project(current_user(request), project_id)
    job_id = _analysis_jobs.get(project_id)
    job = jobs.get(job_id) if job_id else None
    report = db.query_one("SELECT * FROM analysis_reports WHERE project_id=?", (project_id,))
    out: dict = {"job": job}
    if report and report["status"] == 1:
        out["report"] = {
            "moodMix": json.loads(report["mood_mix"] or "{}"),
            "tempoBpm": report["tempo_bpm"],
            "assets": json.loads(report["scene_tags"] or "[]"),
            "meta": json.loads(report["energy_curve"] or "{}"),
        }
    return out


# ---------------- 配乐 ----------------

@router.get("/projects/{project_id}/music")
def music_candidates(project_id: int, refresh: int = 0, request: Request = None):
    owned_project(current_user(request), project_id)
    music_match.scan_library()
    music_match.ensure_tagged()
    rep = db.query_one("SELECT tempo_bpm FROM analysis_reports WHERE project_id=? AND status=1", (project_id,))
    total_ms = db.query_one(
        "SELECT COALESCE(SUM(duration_ms),0) AS t FROM assets WHERE project_id=?", (project_id,))["t"]
    need = int(total_ms * 0.6) or 120_000
    return {"candidates": music_match.candidates(rep["tempo_bpm"] if rep else None, need,
                                                 offset=max(refresh - 1, 0) * 4)}


# ---------------- 自动成片 ----------------

class NarrationBody(BaseModel):
    style: str = "humor"
    custom: str = ""
    edlVersion: int | None = None


class AutoCutBody(BaseModel):
    seed: int | None = None
    musicId: int | None = None
    assetIds: list[int] | None = None   # 参与本次成片的素材子集；None = 全部
    preference: dict = Field(default_factory=lambda: {"duration": "fit", "aspect": "9:16",
                                                      "transitionStyle": "gentle"})
    prompt: str = ""  # 用户自然语言剪辑指令
    height: int = 1080
    fps: int = 30
    render: bool = True
    review: bool = True   # 成片后 AI 自检，不达标自动重剪（最多 3 轮）


@router.post("/projects/{project_id}/auto-cut")
def auto_cut(project_id: int, body: AutoCutBody, request: Request = None):
    user = current_user(request)
    proj = owned_project(user, project_id)
    rep = db.query_one("SELECT scene_tags FROM analysis_reports WHERE project_id=? AND status=1", (project_id,))
    if not rep:
        raise HTTPException(400, "请先完成 AI 分析")

    asset_rows = {a["id"]: a for a in db.query("SELECT * FROM assets WHERE project_id=?", (project_id,))}
    analysis_list = json.loads(rep["scene_tags"])
    assets = []
    for ana in analysis_list:
        row = asset_rows.get(ana["assetId"])
        if row:
            assets.append({**row, "analysis": ana})
    if not assets:
        raise HTTPException(400, "素材数据缺失，请重新分析")
    # 只用勾选的素材参与本次成片
    if body.assetIds is not None:
        keep = set(body.assetIds)
        assets = [a for a in assets if a["id"] in keep]
    if not assets:
        raise HTTPException(400, "没有勾选任何素材，请至少选择一段参与成片")

    music = None
    if body.musicId:
        m = db.query_one("SELECT * FROM music_library WHERE id=? AND status=1", (body.musicId,))
        if m:
            total_ms = sum(a["duration_ms"] for a in assets)
            music = {"musicId": m["id"], "chorusMs": m["chorus_ms"] or 0,
                     "match": 96, "durationMs": m["duration_ms"]}

    # 剪辑方案：EditorAgent（LLM 优先，规则引擎兜底）——同步产出首版，保持接口返回语义
    use_llm = bool(llm_config.get_current_model(user["id"])["apiKey"])
    mode = body.preference.get("mode", "normal")
    editor_ctx = {"user_id": user["id"], "project_id": project_id, "title": proj["title"],
                  "assets": assets, "music": music, "preference": body.preference,
                  "prompt": body.prompt.strip(), "use_llm": use_llm, "seed": body.seed}
    editor = EditorAgent()
    edl = editor.run(editor_ctx)
    if editor.state.value == "error" or edl is None:
        raise HTTPException(500, f"剪辑方案生成失败：{editor.error}")
    # 模式与原声偏好落进 EDL，供「换个剪法」沿用
    edl.meta.preference = {**edl.meta.preference, "mode": mode}
    ov = body.preference.get("originalVoice", "auto")   # 原声：auto=配音开则关 / on / off
    if ov == "off":
        edl.audio.keepOriginal = False
    elif ov == "on":
        edl.audio.keepOriginal = True
    # 存首版快照（AI=1 / 换剪法=3）
    source = 3 if body.seed is not None else 1
    version = timelines_repo.max_version(project_id) + 1
    payload = edl.model_dump()
    payload["version"] = version
    timelines_repo.insert(project_id, version, source, json.dumps(payload, ensure_ascii=False))
    projects_repo.set_current_version(project_id, version)
    print(f"[剪辑] 项目{project_id} 方案v{version}：{len(edl.clips)} 段 · "
          f"{'Vlog口播' if mode == 'vlog' else '普通'} · 总长 {edl.total_duration_ms() / 1000:.1f}s"
          + (f" · 配乐 #{edl.audio.musicId}" if edl.audio.musicId else " · 无配乐"), flush=True)

    if not body.render:
        return {"edlVersion": version, "edl": payload, "jobId": None}

    sub_style = body.preference.get("subtitleStyle", "asr")
    max_rounds = 3 if (body.review and use_llm) else 1   # AI 自检：最多 3 轮（首版 + 2 次优化）
    state = {"version": version, "last_result": None}

    def _save_snapshot(edl_inner, review=None):
        if review is not None:
            edl_inner.meta.review = review
        snap = edl_inner.model_dump()
        snap["version"] = state["version"]
        timelines_repo.update_edl(project_id, state["version"], json.dumps(snap, ensure_ascii=False))

    def _save_new_version(edl_inner):
        state["version"] = timelines_repo.max_version(project_id) + 1
        timelines_repo.insert(project_id, state["version"], 3,
                              json.dumps({**edl_inner.model_dump(), "version": state["version"]},
                                         ensure_ascii=False))
        projects_repo.set_current_version(project_id, state["version"])

    def _render_step(edl_inner):
        """渲染当前 EDL（复用既有渲染任务函数，结果写 job["result"]）。"""
        job["_ctx"] = (project_id, edl_inner, body.height, body.fps)
        _run_render(job, cancelled_ref[0])
        state["last_result"] = job.get("result")

    cancelled_ref = [None]

    def _fn(job, cancelled):
        cancelled_ref[0] = cancelled
        ctx = {
            "user_id": user["id"], "project_id": project_id, "title": proj["title"],
            "assets": assets, "music": music, "preference": body.preference,
            "prompt": body.prompt.strip(), "use_llm": use_llm, "seed": body.seed,
            "mode": mode, "max_rounds": max_rounds,
            "apply_vlog_subs": lambda e: apply_vlog_subs(user["id"], project_id, e, sub_style,
                                                         use_llm, job, body.preference.get("originalVoice", "auto")),
            "save_snapshot": _save_snapshot,
            "save_new_version": _save_new_version,
            "render": _render_step,
            "export_path": lambda: settings.renders_dir / (state["last_result"] or {}).get("fileKey", ""),
            "cancelled": cancelled,
        }
        director = DirectorAgent(ctx, initial_edl=edl, on_event=None)
        run = AgentRun(director, job)
        out = run.execute() or {}
        result = job.get("result")
        if not isinstance(result, dict):
            result = {"version": state["version"]}
            job["result"] = result
        for src, dst in (("sub_note", "subtitleNote"), ("review", "review"), ("review_note", "reviewNote")):
            if out.get(src):
                result[dst] = out[src]

    job = jobs.submit(_fn, "render")
    _render_jobs[project_id] = job["jobId"]
    return {"edlVersion": version, "jobId": job["jobId"], "job": job}


@router.post("/projects/{project_id}/subtitles")
def gen_subtitles(project_id: int, request: Request = None):
    """手动触发：按最新时间线识别字幕，返回列表（前端合并进 EDL 后保存）。"""
    owned_project(current_user(request), project_id)
    row = db.query_one(
        "SELECT edl FROM timelines WHERE project_id=? ORDER BY version DESC LIMIT 1", (project_id,))
    if not row:
        raise HTTPException(404, "还没有时间线，先自动成片或保存一次编辑")
    edl = EDL(**json.loads(row["edl"]))

    def _fn(job, cancelled):
        subs = gen_subtitles_for_edl(project_id, edl, job, 0.0, 0.95)
        job["result"] = {"subtitles": [s.model_dump() for s in subs]}

    job = jobs.submit(_fn, "asr")
    return job


# ---------------- Vlog 字幕文案（风格化旁白） ----------------

@router.post("/projects/{project_id}/narration")
def gen_narration(project_id: int, body: NarrationBody, request: Request = None):
    """按风格为当前时间线的每段生成一句旁白字幕（前端合并进 EDL 后保存）。"""
    user = current_user(request)
    owned_project(user, project_id)
    row = (db.query_one("SELECT edl FROM timelines WHERE project_id=? AND version=?", (project_id, body.edlVersion))
           if body.edlVersion else
           db.query_one("SELECT edl FROM timelines WHERE project_id=? ORDER BY version DESC LIMIT 1", (project_id,)))
    if not row:
        raise HTTPException(404, "还没有时间线，先自动成片或保存一次编辑")
    edl = EDL(**json.loads(row["edl"]))
    style_text = body.custom.strip() or narration_style_text(body.style)

    def _fn(job, cancelled):
        subs = gen_narration_subs(user["id"], project_id, edl, style_text, job)
        job["result"] = {"subtitles": subs}

    return jobs.submit(_fn, "narration")


@router.get("/tts/voices")
def tts_voices():
    """可用中文配音音色（macOS say）。"""
    from ..core import tts as tts_svc
    return {"voices": tts_svc.list_voices(), "default": tts_svc.default_voice()}


def _run_render(job: dict, cancelled) -> None:
    project_id, edl, height, fps = job["_ctx"]
    if height not in (720, 1080, 2160) or fps not in (30, 60):
        raise RuntimeError("height 须为 720/1080/2160，fps 须为 30/60")
    result = render_edl(project_id, edl, height, fps,
                        register_proc=lambda p: job.update(_proc=p))
    if cancelled():
        job["status"] = "cancelled"
        return
    job["result"] = result


@router.post("/projects/{project_id}/render")
def start_render(project_id: int, body: RenderBody, request: Request = None):
    owned_project(current_user(request), project_id)
    if body.edlVersion is None:
        row = db.query_one(
            "SELECT edl FROM timelines WHERE project_id=? ORDER BY version DESC LIMIT 1", (project_id,))
    else:
        row = db.query_one("SELECT edl FROM timelines WHERE project_id=? AND version=?",
                           (project_id, body.edlVersion))
    if not row:
        raise HTTPException(404, "找不到时间线，先自动成片或 PUT 一份 EDL")
    edl = EDL(**json.loads(row["edl"]))

    def _fn(job, cancelled):
        job["_ctx"] = (project_id, edl, body.height, body.fps)
        _run_render(job, cancelled)

    job = jobs.submit(_fn, "render")
    _render_jobs[project_id] = job["jobId"]
    return job


@router.get("/renders/{job_id}")
def render_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在或服务已重启")
    return job


@router.post("/renders/{job_id}/cancel")
def render_cancel(job_id: str):
    if not jobs.request_cancel(job_id):
        raise HTTPException(404, "任务不存在")
    return {"cancelled": True}
