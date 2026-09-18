"""轻量任务框架：线程池 + 内存任务表，状态镜像落 SQLite（重启不丢任务历史）。

状态机: queued → running → done / error / cancelled；服务重启时把遗留的
queued/running 标记为 error（"服务重启，任务已中断"），前端轮询得到明确终态而非 404。
"""
from __future__ import annotations

import json
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Callable

from ..db import execute, query_one

_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="job")
_jobs: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def _persist(job: dict) -> None:
    """状态变更时镜像到库（进度不逐次落库——重启后一律视为中断，没必要）。"""
    execute(
        """INSERT INTO jobs (job_id, kind, status, progress, message, result, error, created_at)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(job_id) DO UPDATE SET
             status=excluded.status, progress=excluded.progress, message=excluded.message,
             result=excluded.result, error=excluded.error,
             updated_at=datetime('now','localtime')""",
        (job["jobId"], job["kind"], job["status"], job["progress"], job["message"],
         json.dumps(job["result"], ensure_ascii=False) if job["result"] is not None else None,
         job["error"], job["createdAt"]))


def mark_interrupted_on_startup() -> None:
    """启动时收尾：上次进程遗留的未完成任务 → 明确的失败终态。"""
    execute("UPDATE jobs SET status='error',"
            " error='服务重启，任务已中断，请重新发起',"
            " updated_at=datetime('now','localtime')"
            " WHERE status IN ('queued','running')")


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
    _persist(job)

    def _run():
        if job["_cancel"].is_set():
            job["status"] = "cancelled"
            _persist(job)
            return
        job["status"] = "running"
        _persist(job)
        try:
            fn(job, job["_cancel"].is_set)
            if job["status"] == "running":  # 任务函数正常返回且未自行标记 → 完成
                job["status"] = "done"
        except Exception as e:  # noqa: BLE001 任务线程兜底
            job["status"] = "error"
            job["error"] = f"{e}"
            traceback.print_exc()
        _persist(job)

    _pool.submit(_run)
    return {k: v for k, v in job.items() if not k.startswith("_")}


def get(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        if job is not None:
            return {k: v for k, v in job.items() if not k.startswith("_")}
    # 重启后的历史任务：从库里回（启动时已把未完成改成终态）
    row = query_one("SELECT * FROM jobs WHERE job_id=?", (job_id,))
    if not row:
        return None
    return {
        "jobId": row["job_id"], "kind": row["kind"], "status": row["status"],
        "progress": row["progress"], "message": row["message"],
        "result": json.loads(row["result"]) if row["result"] else None,
        "error": row["error"], "createdAt": row["created_at"],
    }


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
