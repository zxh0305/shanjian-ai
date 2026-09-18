"""智能体层 · BaseAgent（借鉴 OpenManus）：主循环 + 状态机 + 步数上限 + 卡死检测。

子类只实现 step()：每步做一件事，做完置 state=FINISHED 并写 self.result。
DirectorAgent 用它跑固定流水线（by_order），ToolCallAgent 用它跑 LLM 选工具（react）。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable


class AgentState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"


class BaseAgent(ABC):
    name = "agent"
    max_steps = 10

    def __init__(self, on_event: Callable[[str, dict], None] | None = None):
        self.state = AgentState.IDLE
        self.step_count = 0
        self.result: Any = None
        self.error: str = ""
        self._recent_signatures: list[str] = []
        self._on_event = on_event

    # ---- 子类实现 ----
    @abstractmethod
    def step(self, request: Any) -> None:
        """执行一步；完成时 self.state = FINISHED 并写 self.result。"""

    # ---- 通用能力 ----
    def emit(self, message: str, progress: float | None = None) -> None:
        if self._on_event:
            self._on_event(message, {"progress": progress} if progress is not None else {})

    def _signature(self) -> str:
        """进度签名：状态 + 子类可选 phase（不含步数，否则永不重复）。"""
        return f"{self.state}:{getattr(self, 'phase', '')}"

    def run(self, request: Any = None) -> Any:
        """主循环：跑 step() 直到完成 / 出错 / 触顶；连续 3 步无变化判卡死。"""
        self.state = AgentState.RUNNING
        try:
            while self.state == AgentState.RUNNING and self.step_count < self.max_steps:
                self.step_count += 1
                self.step(request)
                sig = self._signature()
                self._recent_signatures.append(sig)
                if len(self._recent_signatures) > 6:
                    self._recent_signatures.pop(0)
                if self._recent_signatures[-3:] == [sig] * 3:
                    self.state = AgentState.ERROR
                    self.error = f"{self.name} 连续 3 步无进展（疑似卡死）"
                    break
        except Exception as e:  # noqa: BLE001 智能体边界兜底
            self.state = AgentState.ERROR
            self.error = f"{type(e).__name__}: {e}"
        if self.state == AgentState.RUNNING:  # 触顶未完成
            self.state = AgentState.ERROR
            self.error = self.error or f"{self.name} 超过步数上限 {self.max_steps}"
        return self.result
