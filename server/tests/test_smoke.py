"""冒烟测试：合成测试视频 → 上传 → 元数据解析 → 代理生成 → EDL 保存。

ffmpeg/ffprobe 未安装时自动跳过媒体相关用例（EDL 校验用例不受影响）。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

# 数据目录由 tests/conftest.py 在导入前统一锁定
_TMP = os.environ["SHANJIAN_DATA_DIR"]

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402

HAS_FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")


import pytest  # noqa: E402


@pytest.fixture()
def client():
    # with 上下文确保 lifespan（init_db）执行；注册（已注册则登录）测试账号
    with TestClient(app) as c:
        r = c.post("/auth/register", json={"name": "pytest", "password": "pytest123"})
        if r.status_code != 200:
            r = c.post("/auth/login", json={"name": "pytest", "password": "pytest123"})
        assert r.status_code == 200, r.text
        c.headers.update({"Authorization": "Bearer " + r.json()["token"]})
        yield c


def _make_test_video(name: str, seconds: int = 3) -> Path:
    """合成一段 testsrc 视频作为测试素材。"""
    out = Path(_TMP) / name
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
         f"testsrc=duration={seconds}:size=1280x720:rate=30",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
         "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest",
         str(out)],
        check=True, capture_output=True,
    )
    return out


@pytest.mark.skipif(not HAS_FFMPEG, reason="需要 ffmpeg/ffprobe")
def test_upload_pipeline(client):
    video = _make_test_video("clip_a.mp4")

    # 1. 上传（不带 project_id → 自动建项目）
    with video.open("rb") as f:
        r = client.post("/upload", files={"file": ("海边日落.mp4", f, "video/mp4")})
    assert r.status_code == 200, r.text
    body = r.json()
    pid, aid = body["projectId"], body["assetId"]

    # TestClient 下 BackgroundTasks 已同步跑完：元数据与代理应就绪
    r = client.get(f"/projects/{pid}")
    assert r.status_code == 200
    asset = r.json()["assets"][0]
    assert asset["assetId"] == aid
    assert asset["durationMs"] == 3000
    assert asset["resolution"] == "1280x720"
    assert asset["probeStatus"] == 1 and asset["proxyStatus"] == 1
    assert (settings.proxies_dir / asset["proxyUrl"].rsplit("/", 1)[-1]).exists()

    # 2. 项目列表带统计
    r = client.get("/projects")
    proj = next(p for p in r.json()["projects"] if p["projectId"] == pid)
    assert proj["assetCount"] == 1 and proj["totalDurationMs"] == 3000


VALID_EDL = {
    "meta": {"title": "周末出走计划", "aspect": "9:16", "fps": 30,
             "preference": {"duration": "fit", "transitionStyle": "gentle"}},
    "clips": [
        {"assetId": 1, "inMs": 0, "outMs": 18000, "note": "开场 · 片头淡入", "fadeInMs": 800},
        {"assetId": 1, "inMs": 2000, "outMs": 24000, "note": "夜景 · 节奏收紧"},
        {"assetId": 1, "inMs": 1000, "outMs": 35000, "note": "情绪高点 · 对齐鼓点"},
        {"assetId": 1, "inMs": 500, "outMs": 38500, "note": "收尾 · 片尾淡出", "fadeOutMs": 1200},
    ],
    "transitions": [
        {"afterClip": 1, "type": "dissolve", "durMs": 800, "beatAligned": True},
        {"afterClip": 2, "type": "dissolve", "durMs": 800, "beatAligned": True},
        {"afterClip": 3, "type": "push_in", "durMs": 600, "beatAligned": False},
    ],
    "audio": {"musicId": None, "volume": 0.65, "offsetMs": 0, "fadeInMs": 1500, "fadeOutMs": 2000},
    "captions": [{"text": "周末出走计划", "startMs": 109000, "endMs": 112000, "style": "ending_credit"}],
}


def test_timeline_snapshot_versioning(client):
    pid = client.post(
        "/upload", files={"file": ("x.mp4", b"\x00" * 16, "video/mp4")}).json()["projectId"]
    # 无效文件 probe 会失败，但不影响时间线接口

    r = client.put(f"/projects/{pid}/timeline", json=VALID_EDL)
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 1
    # 演示口径：Σ(18+22+34+38s) − (800+800+600ms) = 112000 − 2200
    assert r.json()["totalDurationMs"] == 112000 - 2200
    assert "叠化×2" in r.json()["transitionSummary"]

    r = client.put(f"/projects/{pid}/timeline", json={**VALID_EDL, "version": 99})
    assert r.json()["version"] == 2  # 服务端管版本号，客户端传的无效

    r = client.get(f"/projects/{pid}/timeline")
    assert r.json()["version"] == 2
    r = client.get(f"/projects/{pid}/timeline?version=1")
    assert r.json()["version"] == 1  # 历史快照可回看


def test_edl_validation_rejects_bad_transitions(client):
    pid = client.post(
        "/upload", files={"file": ("y.mp4", b"\x00" * 16, "video/mp4")}).json()["projectId"]
    bad = {**VALID_EDL, "transitions": [{"afterClip": 9, "type": "iris", "durMs": 500}]}
    assert client.put(f"/projects/{pid}/timeline", json=bad).status_code == 422
    bad2 = {**VALID_EDL, "clips": [{**VALID_EDL["clips"][0], "inMs": 5000, "outMs": 5000}]}
    assert client.put(f"/projects/{pid}/timeline", json=bad2).status_code == 422


def test_pipeline_endpoints(client):
    """分析/配乐/自动成片已实现：POST analysis 返回任务；music 返回候选；未分析 auto-cut 400。"""
    pid = client.post(
        "/upload", files={"file": ("z.mp4", b"\x00" * 16, "video/mp4")}).json()["projectId"]
    r = client.post(f"/projects/{pid}/analysis")
    assert r.status_code == 200 and "jobId" in r.json()
    assert client.get(f"/projects/{pid}/music").status_code == 200
    assert client.post(f"/projects/{pid}/auto-cut", json={}).status_code == 400


def test_project_endpoint_with_exports(client):
    """回归：项目页 exports 曾因对已映射的 DTO 再取 size_bytes（蛇形键）而 KeyError。"""
    from app.repositories import exports as exports_repo
    pid = client.post(
        "/upload", files={"file": ("e.mp4", b"\x00" * 16, "video/mp4")}).json()["projectId"]
    exports_repo.add(pid, 1, "export_test_v1.mp4", "1080x1920", 30, 12345, 999)

    r = client.get(f"/projects/{pid}")
    assert r.status_code == 200, r.text
    exp = r.json()["exports"]
    assert len(exp) == 1 and exp[0]["sizeBytes"] == 12345 and exp[0]["version"] == 1
    assert client.get(f"/projects/{pid}/exports").status_code == 200
