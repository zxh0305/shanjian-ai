"""时间线读写：GET/PUT /projects/{id}/timeline —— EDL 快照管理（定稿 §3）。

PUT 用 pydantic 全量校验后保存为 v{n+1} 快照；GET 默认返回最新版，可 ?version= 回看。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request

from ..repositories import projects as projects_repo
from ..repositories import timelines as timelines_repo
from ..schemas.edl import EDL
from .auth import current_user, owned_project

router = APIRouter()

SOURCE_AI, SOURCE_MANUAL, SOURCE_REGENERATE = 1, 2, 3


def _row_to_dto(r: dict) -> dict:
    return {"version": r["version"], "source": r["source"], "edl": json.loads(r["edl"])}


@router.get("/projects/{project_id}/timeline")
def get_timeline(project_id: int, version: int | None = None, request: Request = None):
    owned_project(current_user(request), project_id)
    row = timelines_repo.get_version(project_id, version) if version is not None else timelines_repo.latest(project_id)
    if not row:
        raise HTTPException(404, "该项目还没有时间线，先调用自动成片或 PUT 保存一份 EDL")
    return _row_to_dto(row)


@router.put("/projects/{project_id}/timeline")
def put_timeline(project_id: int, edl: EDL, source: int = SOURCE_MANUAL, request: Request = None):
    owned_project(current_user(request), project_id)
    if source not in (SOURCE_AI, SOURCE_MANUAL, SOURCE_REGENERATE):
        raise HTTPException(400, "source 取值 1=AI / 2=手动 / 3=换剪法")

    new_version = timelines_repo.max_version(project_id) + 1

    payload = edl.model_dump()
    payload["version"] = new_version
    timelines_repo.insert(project_id, new_version, source, json.dumps(payload, ensure_ascii=False))
    projects_repo.set_current_version(project_id, new_version)
    return {"version": new_version, "source": source,
            "totalDurationMs": edl.total_duration_ms(),
            "transitionSummary": edl.transition_summary()}
