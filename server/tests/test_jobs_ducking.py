"""任务框架持久化与渲染 ducking 单测：重启中断标记、历史任务回读、ducking 包络进命令。"""
from __future__ import annotations

import json
import os
import tempfile
from types import SimpleNamespace as NS

os.environ.setdefault("SHANJIAN_DATA_DIR", tempfile.mkdtemp(prefix="shanjian_jobs_"))

from app.schemas.edl import Audio, Clip, EDL, Meta, Transition, TransitionType  # noqa: E402
from app.core import render as core_render  # noqa: E402
from app.services import jobs  # noqa: E402


def _mk_edl() -> EDL:
    return EDL(meta=Meta(title="t"),
               clips=[Clip(assetId=1, inMs=0, outMs=3000)],
               audio=Audio(musicId=7, ttsEnabled=True, ducking=True))


def test_jobs_persist_and_interrupt_on_restart():
    """任务状态落库；mark_interrupted_on_startup 把遗留 running 改为失败终态。"""
    from app.db import migrate
    migrate.init_db()                      # 独立测试目录下确保 jobs 表已建
    calls = {"ran": 0}

    def slow(job, cancelled):
        calls["ran"] += 1
        job["progress"] = 0.5
        job["message"] = "干到一半"
        if calls["ran"] == 1:
            raise RuntimeError("boom")   # 首个任务直接失败 → 落库 error

    j = jobs.submit(slow, "render")
    got = jobs.get(j["jobId"])
    while got["status"] in ("queued", "running"):
        got = jobs.get(j["jobId"])
    assert got["status"] == "error" and "boom" in got["error"]

    # 模拟重启：先让一个任务真实处于 running，再清内存表 + 启动收尾
    import threading
    hold, release = threading.Event(), threading.Event()

    def waiter(job, cancelled):
        hold.set()
        release.wait(2)

    j2 = jobs.submit(waiter, "render")
    assert hold.wait(2)                    # 任务已进入 running
    running_id = j2["jobId"]
    with jobs._lock:                      # 进程死亡 = 内存任务表消失
        jobs._jobs.clear()
    jobs.mark_interrupted_on_startup()

    row = jobs.get(running_id)             # 只剩库里那条 → 已被改成失败终态
    assert row and row["status"] == "error" and "服务重启" in (row["error"] or "")
    assert jobs.get("not-exist-xyz") is None
    release.set()


def _build_cmd(edl: EDL, tts_tracks):
    from pathlib import Path
    assets = {1: {"file_path": "a.mp4"}}
    cmd, _total = core_render.build_command(edl, assets, "/tmp/m.mp3", 720, 30,
                                            Path("/tmp/o.mp4"), tts_tracks)
    graph = cmd[cmd.index("-filter_complex") + 1]
    return graph


def test_ducking_envelope_in_command():
    """有配音+ducking → BGM 出现压低包络；关掉或无配音 → 不出现。"""
    tts = [(NS(__x="a"), 500, 2500, 1.0)]
    graph = _build_cmd(_mk_edl(), tts)
    assert "volume=volume='if(" in graph and "eval=frame" in graph
    # 关闭 ducking
    edl = _mk_edl()
    edl.audio.ducking = False
    assert "volume=volume='if(" not in _build_cmd(edl, tts)
    # 无配音
    assert "volume=volume='if(" not in _build_cmd(_mk_edl(), [])
