"""项目查询：GET /projects、GET /projects/{id}/exports、DELETE /projects/{id}。"""
from __future__ import annotations

import os
from fastapi import APIRouter, HTTPException, Request

from ..config import settings
from ..repositories import analysis as analysis_repo
from ..repositories import assets as assets_repo
from ..repositories import exports as exports_repo
from ..repositories import projects as projects_repo
from .auth import current_user, owned_project

router = APIRouter()


def _asset_dto(a: dict) -> dict:
    return {
        "assetId": a["id"],
        "fileName": a["file_name"],
        "durationMs": a["duration_ms"],
        "resolution": f'{a["width"]}x{a["height"]}' if a["width"] else None,
        "fps": a["fps"],
        "sizeBytes": a["size_bytes"],
        "shotAt": a["shot_at"],
        "qualityScore": a["quality_score"],
        "qualityGood": bool(a["quality_score"] and a["quality_score"] >= 0.8),  # 「画质佳」
        "thumbUrl": f"/media/proxies/{a['thumb_key']}" if a["thumb_key"] else None,
        "proxyUrl": f"/media/proxies/{a['proxy_key']}" if a["proxy_key"] else None,
        "probeStatus": a["probe_status"],
        "proxyStatus": a["proxy_status"],
    }


@router.get("/projects")
def list_projects(request: Request):
    user = current_user(request)
    rows = projects_repo.list_for_user(user["id"])
    out = []
    for p in rows:
        assets = assets_repo.for_project(p["id"])
        exports = [
            {"version": e["version"], "resolution": e["resolution"], "fps": e["fps"],
             "size_bytes": e["size_bytes"], "created_at": e["created_at"]}
            for e in exports_repo.for_project(p["id"])
        ]
        out.append({
            "projectId": p["id"],
            "title": p["title"],
            "status": p["status"],
            "note": p["note"],
            "currentVersion": p["current_version"],
            "coverUrl": f"/media/proxies/{assets[0]['thumb_key']}" if assets and assets[0]["thumb_key"] else None,
            "assetCount": len(assets),
            "totalDurationMs": sum(a["duration_ms"] or 0 for a in assets),
            "exports": [
                {"version": e["version"], "resolution": e["resolution"], "fps": e["fps"],
                 "sizeBytes": e["size_bytes"], "createdAt": e["created_at"]}
                for e in exports
            ],
            "updatedAt": p["updated_at"],
        })
    return {"projects": out}


@router.get("/projects/{project_id}")
def get_project(project_id: int, request: Request):
    user = current_user(request)
    p = owned_project(user, project_id)
    assets = [_asset_dto(a) for a in assets_repo.for_project(project_id)]
    exports = [
        {"version": e["version"], "resolution": e["resolution"], "fps": e["fps"],
         "sizeBytes": e["size_bytes"], "createdAt": e["created_at"]}
        for e in exports_repo.for_project(project_id)
    ]
    return {
        "projectId": p["id"], "title": p["title"], "status": p["status"], "note": p["note"],
        "currentVersion": p["current_version"], "assets": assets,
        "exports": [
            {"version": e["version"], "resolution": e["resolution"], "fps": e["fps"],
             "sizeBytes": e["size_bytes"], "createdAt": e["created_at"]}
            for e in exports
        ],
        "updatedAt": p["updated_at"],
    }


@router.get("/projects/{project_id}/exports")
def list_exports(project_id: int, request: Request):
    user = current_user(request)
    owned_project(user, project_id)
    rows = exports_repo.for_project(project_id)
    _title = exports_repo.project_title(project_id)
    return {"exports": [{
        "version": r["version"],
        "fileName": f'{_title}_v{r["version"]}.mp4',
        "url": f"/media/renders/{r['file_key']}",
        "resolution": r["resolution"], "fps": r["fps"],
        "sizeBytes": r["size_bytes"], "elapsedMs": r["elapsed_ms"],
        "savedToAlbum": bool(r["saved_to_album"]),
        "createdAt": r["created_at"],
    } for r in rows]}


@router.delete("/projects/{project_id}/assets/{asset_id}")
def delete_asset(project_id: int, asset_id: int, request: Request):
    """移除单段素材：删 DB 行 + 原片/代理/缩略图文件，并作废旧分析报告。"""
    user = current_user(request)
    owned_project(user, project_id)
    a = assets_repo.get(asset_id)
    if a and a["project_id"] != project_id:
        a = None
    if not a:
        raise HTTPException(404, "素材不存在")

    removed = 0
    for key, base in ((a["file_path"], settings.assets_dir),
                      (a["proxy_key"], settings.proxies_dir),
                      (a["thumb_key"], settings.proxies_dir)):
        if not key:
            continue
        path = base / key
        if path.exists():
            path.unlink()
            removed += 1

    assets_repo.delete(asset_id)
    # 素材集变化后旧分析报告已失真，删掉让「开始 AI 分析」自动重跑
    analysis_repo.invalidate(project_id)
    projects_repo.bump_updated(project_id)
    return {"deleted": True, "assetId": asset_id, "filesRemoved": removed}


@router.delete("/projects/{project_id}/exports/{version}")
def delete_export(project_id: int, version: int, request: Request):
    """删除单个成片版本：删 DB 行 + 渲染文件。"""
    user = current_user(request)
    owned_project(user, project_id)
    row = exports_repo.get_version(project_id, version)
    if not row:
        raise HTTPException(404, "成片不存在")
    path = settings.renders_dir / row["file_key"]
    if path.exists():
        path.unlink()
    exports_repo.delete(project_id, version)
    return {"deleted": True, "version": version}


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, request: Request):
    user = current_user(request)
    p = owned_project(user, project_id)

    # Collect file keys before deleting DB rows
    assets = assets_repo.for_project(project_id)
    renders = exports_repo.for_project(project_id)

    # Delete DB rows (cascade handles assets, analysis, timelines, exports)
    projects_repo.delete(project_id)

    # Delete physical files
    deleted = 0
    for a in assets:
        for key in (a["file_path"], a["proxy_key"], a["thumb_key"]):
            if key:
                path = settings.assets_dir / key if a["file_path"] == key else settings.proxies_dir / key
                if not path.exists():
                    path = settings.proxies_dir / key
                if path.exists():
                    path.unlink()
                    deleted += 1
    for r in renders:
        key = r["file_key"]
        if key:
            path = settings.renders_dir / key
            if path.exists():
                path.unlink()
                deleted += 1

    return {"deleted": True, "projectId": project_id, "filesRemoved": deleted}
