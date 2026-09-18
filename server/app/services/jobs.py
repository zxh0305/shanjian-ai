"""轻量任务框架：线程池 + 内存任务表（单机单人，无需持久化队列）。

状态机: queued → running → done / error / cancelled
"""
from __future__ import annotations

import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Callable

_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="job")
_jobs: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def submit(fn: Callable[[dict, Callable[[], bool]], Any], kind: str) -> dict:
    job_id = uuid.uuid4().hex[:12]
    job = {
        "jobId": job_id, "kind": kind, "status": "queued",
        "progress": 0.0, "message": "", "result": None,
        "error": None, "createdAt": datetime.now().isoformat(timespec="seconds"),
        "_cancel": threading.Event(), "_proc": None,
    }
    with _lock:
        _jobs[job_id] = job

    def _run():
        if job["_cancel"].is_set():
            job["status"] = "cancelled"
            return
        job["status"] = "running"
        try:
            fn(job, job["_cancel"].is_set)
            if job["status"] == "running":  # 任务函数正常返回且未自行标记 → 完成
                job["status"] = "done"
        except Exception as e:  # noqa: BLE001 任务线程兜底
            job["status"] = "error"
            job["error"] = f"{e}"
            traceback.print_exc()

    _pool.submit(_run)
    return {k: v for k, v in job.items() if not k.startswith("_")}


def get(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        return {k: v for k, v in job.items() if not k.startswith("_")}


def request_cancel(job_id: str) -> bool:
    with _lock:
        job = _jobs.get(job_id)
    if not job:
        return False
    job["_cancel"].set()
    proc = job.get("_proc")
    if proc is not None:
        try:
            proc.terminate()
        except Exception:
            pass
    return True
