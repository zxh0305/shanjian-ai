"""工具层 · 三件套（借鉴 OpenManus）：BaseTool / ToolCollection / ToolResult。

- BaseTool：name/description/parameters(JSON Schema)，execute() 抽象；
  to_param() 直出 OpenAI function-calling 格式——将来任何框架可直接接入；
- ToolResult：统一返回（output 文本 / error / preview_path 供多模态"看"结果）；
- ToolCollection：tool_map 分发 + 批量出 schema + execute(name, kwargs)。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ToolResult:
    """工具执行结果；支持 + 拼接（多步结果合并）。"""

    def __init__(self, output: str = "", error: str = "", preview_path: str = ""):
        self.output = output
        self.error = error
        self.preview_path = preview_path

    def __add__(self, other: "ToolResult") -> "ToolResult":
        return ToolResult(
            output="\n".join(x for x in (self.output, other.output) if x),
            error="\n".join(x for x in (self.error, other.error) if x),
            preview_path=other.preview_path or self.preview_path,
        )

    def __bool__(self) -> bool:
        return not self.error

    @classmethod
    def success(cls, output: str = "", preview_path: str = "") -> "ToolResult":
        return cls(output=output, preview_path=preview_path)

    @classmethod
    def failure(cls, error: str) -> "ToolResult":
        return cls(error=error)


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {"type": "object", "properties": {}}  # JSON Schema

    def to_param(self) -> dict[str, Any]:
        """OpenAI function-calling 格式。"""
        return {"type": "function", "function": {
            "name": self.name, "description": self.description, "parameters": self.parameters}}

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """执行并返回文本结果；异常由 __call__ 统一转 ToolResult.failure。"""

    def __call__(self, **kwargs) -> ToolResult:
        try:
            return ToolResult.success(self.execute(**kwargs))
        except Exception as e:  # noqa: BLE001 工具边界兜底
            return ToolResult.failure(f"{type(e).__name__}: {e}")


class ToolCollection:
    """工具集：声明式组合、按名分发。agent 只持有它，不认识具体工具。"""

    def __init__(self, *tools: BaseTool):
        self.tools = tuple(tools)
        self.tool_map = {t.name: t for t in tools}

    def to_params(self) -> list[dict[str, Any]]:
        return [t.to_param() for t in self.tools]

    def get(self, name: str) -> BaseTool | None:
        return self.tool_map.get(name)

    def execute(self, name: str, tool_input: dict[str, Any] | None = None) -> ToolResult:
        tool = self.tool_map.get(name)
        if not tool:
            return ToolResult.failure(f"工具不存在: {name}")
        return tool(**(tool_input or {}))
