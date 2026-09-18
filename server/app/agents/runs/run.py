"""智能体层 · AgentRun：一次运行的载体（对应 OpenHands 的 Conversation）。

拥有循环（委托 agent.run）、事件列表（可回放进度）、与既有 jobs 框架对接：
job["message"]/job["progress"] 同步、cancelled 透传。服务重启丢任务状态的老约束不变。
"""
from __future__ import annotations

from typing import Any

from ..base import AgentState


class AgentRun:
    def __init__(self, agent, job: dict | None = None):
        self.agent = agent
        self.job = job
        self.events: list[dict] = []
        agent._on_event = self._on_event

    def _on_event(self, message: str, extra: dict) -> None:
        self.events.append({"message": message, **extra})
        if self.job is not None:
            self.job["message"] = message
            if extra.get("progress") is not None:
                self.job["progress"] = extra["progress"]

    def log(self, message: str, progress: float | None = None) -> None:
        self._on_event(message, {"progress": progress} if progress is not None else {})

    def cancelled(self) -> bool:
        return bool(self.job and self.job.get("_cancel") and self.job["_cancel"].is_set())

    def execute(self, request: Any = None) -> Any:
        result = self.agent.run(request)
        if self.agent.state == AgentState.ERROR:
            raise RuntimeError(self.agent.error)
        return result
