"""素材上传：POST /upload —— multipart 整传，落盘后后台解析元数据并生成代理。

对应定稿 W1–W2。分片/断点续传为后续增强，单人先整传。
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile

from ..repositories import assets as assets_repo
from ..repositories import projects as projects_repo
from ..config import settings
from .auth import current_user, owned_project
from ..core import probe as probe_svc
from ..core import proxy as proxy_svc

router = APIRouter()

SAFE_NAME = re.compile(r"[^\w.\-\u4e00-\u9fff]+")  # 保留中文、字母数字、点横线


def _safe_name(name: str) -> str:
    return SAFE_NAME.sub("_", Path(name).name) or "unnamed.mp4"


def _process_asset(asset_id: int) -> None:
    """后台任务：ffprobe 解析 → 720p 代理 + 封面。任何一步失败只标记状态，不影响上传成功。"""
    row = assets_repo.get(asset_id)
    if not row:
        return
    src = settings.assets_dir / row["file_path"]

    try:
        meta = probe_svc.probe(str(src))
    except probe_svc.ProbeError:
        assets_repo.mark_probe_failed(asset_id)
        print(f"[素材] {row['file_name']} 解析失败", flush=True)
        return

    score = proxy_svc.estimate_quality(meta["width"], meta["height"], meta["duration_ms"], meta["size_bytes"])
    assets_repo.save_probe(asset_id, meta, score)

    proxy_key = f"p_{asset_id}.mp4"
    thumb_key = f"t_{asset_id}.jpg"
    try:
        proxy_svc.generate_proxy(src, proxy_key, thumb_key)
    except proxy_svc.ProxyError:
        assets_repo.mark_proxy_failed(asset_id)
        return

    assets_repo.save_proxy(asset_id, proxy_key, thumb_key)
    print(f"[素材] {row['file_name']} 就绪 · {meta['duration_ms'] / 1000:.1f}s · "
          f"{meta['width']}x{meta['height']}", flush=True)


@router.post("/upload")
async def upload(
    background: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    project_id: int | None = Form(default=None, alias="projectId"),
    title: str | None = Form(default=None),
):
    user = current_user(request)
    if project_id is not None:
        owned_project(user, project_id)
        count = assets_repo.count_in_project(project_id)
        if count >= settings.max_assets_per_project:
            raise HTTPException(400, f"单项目素材上限 {settings.max_assets_per_project} 段")

    if project_id is None:
        project_id = projects_repo.create(title, user["id"])

    fname = _safe_name(file.filename or "unnamed.mp4")
    key = f"a_{uuid.uuid4().hex[:8]}_{fname}"
    dest = settings.assets_dir / key

    size = 0
    with dest.open("wb") as f:
        while chunk := await file.read(4 * 1024 * 1024):
            size += len(chunk)
            if size > settings.max_clip_bytes:
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"单段素材上限 {settings.max_clip_bytes // 1024**3}GB")
            f.write(chunk)
    if size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, "空文件")

    asset_id = assets_repo.add(project_id, fname, key, size)
    background.add_task(_process_asset, asset_id)

    return {
        "projectId": project_id,
        "assetId": asset_id,
        "fileName": fname,
        "sizeBytes": size,
        "probeStatus": 0,
        "proxyStatus": 0,
        "message": "已上传，元数据解析与 720p 代理生成进行中（GET /projects/{id} 查询状态）",
    }
