"""智能体层 · ToolCallAgent（react 模式）：think（LLM 选工具）→ act（执行）→ 循环。

特殊工具：Terminate 触发完成；AskHuman 表示需要人工确认（本机单人场景返回提示）。
供创意决策类智能体使用（如剪辑师的自由发挥环节）；固定流水线用 DirectorAgent。
"""
from __future__ import annotations

import json
from typing import Any

from ..tools.base import BaseTool, ToolCollection, ToolResult
from .base import AgentState, BaseAgent


class TerminateTool(BaseTool):
    name = "terminate"
    description = "任务完成时调用，结束当前智能体运行。"
    parameters = {"type": "object", "properties": {"summary": {"type": "string", "description": "完成说明"}}}

    def execute(self, summary: str = "") -> str:
        return summary or "done"


class AskHumanTool(BaseTool):
    name = "ask_human"
    description = "需要用户确认时调用（如删除素材、覆盖成片等破坏性操作）。"
    parameters = {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}

    def execute(self, question: str) -> str:
        raise RuntimeError(f"需要人工确认：{question}")


class ToolCallAgent(BaseAgent):
    """需要 llm 具备 chat.completions.create(tools=...) 能力（OpenAI 兼容客户端）。"""

    def __init__(self, llm_client, llm_model: str, tools: ToolCollection, on_event=None, max_steps: int = 10):
        super().__init__(on_event=on_event)
        self.max_steps = max_steps
        self.llm = llm_client
        self.llm_model = llm_model
        self.tools = ToolCollection(*tools.tools, TerminateTool(), AskHumanTool())
        self.messages: list[dict[str, Any]] = []

    def think(self) -> list[dict]:
        resp = self.llm.chat.completions.create(
            model=self.llm_model, messages=self.messages, tools=self.tools.to_params())
        msg = resp.choices[0].message
        self.messages.append(msg.model_dump() if hasattr(msg, "model_dump") else {"role": "assistant", "content": str(msg)})
        return [{"name": c.function.name, "arguments": c.function.arguments} for c in (msg.tool_calls or [])]

    def act(self, calls: list[dict]) -> list[ToolResult]:
        results = []
        for c in calls:
            try:
                args = json.loads(c["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            res = self.tools.execute(c["name"], args)
            results.append(res)
            self.messages.append({"role": "tool", "tool_call_id": c["name"], "content": res.output or res.error})
            if c["name"] == "terminate":
                self.result = res.output
                self.state = AgentState.FINISHED
            elif res.error:
                self.emit(f"工具 {c['name']} 失败：{res.error[:80]}")
        return results

    def step(self, request: Any) -> None:
        if not self.messages:
            self.messages = [{"role": "user", "content": str(request or "")}]
        calls = self.think()
        if not calls:
            self.state = AgentState.FINISHED  # 模型不再调工具即认为收尾
            return
        self.act(calls)
