"""智能体层单测：BaseAgent 状态机/卡死/终止、ToolCallAgent 工具循环、DirectorAgent 流水线与重剪。"""
from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace as NS

os.environ.setdefault("SHANJIAN_DATA_DIR", tempfile.mkdtemp(prefix="shanjian_agents_"))

from app.agents.base import AgentState, BaseAgent  # noqa: E402
from app.agents.director import DirectorAgent  # noqa: E402
from app.agents.toolcall import TerminateTool, ToolCallAgent  # noqa: E402
from app.schemas.edl import Clip, EDL, Meta  # noqa: E402
from app.tools.base import BaseTool, ToolCollection  # noqa: E402


class _Counter(BaseAgent):
    name = "counter"
    max_steps = 5

    def step(self, request=None):
        self.count = getattr(self, "count", 0) + 1
        if self.count >= 3:
            self.result = self.count
            self.state = AgentState.FINISHED


class _Stuck(BaseAgent):
    name = "stuck"
    max_steps = 8

    def step(self, request=None):
        pass  # 永不完成、状态不变 → 应被判卡死


def test_base_run_and_stuck():
    assert _Counter().run() == 3
    a = _Stuck()
    a.run()
    assert a.state == AgentState.ERROR and "卡死" in a.error


class _EchoTool(BaseTool):
    name = "echo"
    description = "回声"
    parameters = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}

    def execute(self, text: str) -> str:
        return f"echo:{text}"


class _FakeLLM:
    """第一次返回 echo 调用，第二次返回 terminate。"""

    def __init__(self):
        self.calls = 0

        class _Fn:
            def __init__(self, outer):
                self.outer = outer

            def create(self, **kwargs):
                self.outer.calls += 1
                if self.outer.calls == 1:
                    tc = NS(function=NS(name="echo", arguments='{"text":"hi"}'))
                else:
                    tc = NS(function=NS(name="terminate", arguments='{"summary":"完成"}'))
                msg = NS(tool_calls=[tc], model_dump=lambda: {"role": "assistant", "content": ""})
                return NS(choices=[NS(message=msg)])

        self.chat = NS(completions=_Fn(self))


def test_toolcall_agent_loop():
    agent = ToolCallAgent(_FakeLLM(), "m", ToolCollection(_EchoTool()))
    out = agent.run("干活")
    assert agent.state == AgentState.FINISHED and out == "完成"
    assert any("echo:hi" == m.get("content") for m in agent.messages if m["role"] == "tool")


def _mk_edl(n: int = 1) -> EDL:
    return EDL(meta=Meta(title="t"), clips=[Clip(assetId=1, inMs=0, outMs=2000 * i + 2000) for i in range(n)])


def test_director_pipeline_and_revision():
    """首轮审查 55 分不通过 → 重剪（新版本）→ 88 分通过；回调注入验证。"""
    calls = {"subs": 0, "render": 0, "snapshot": 0, "new_version": 0, "edit": 0}
    verdicts = [{"score": 55, "pass": False, "comment": "拖沓", "suggestions": ["缩短"]},
                {"score": 88, "pass": True, "comment": "好", "suggestions": []}]

    def fake_review_agent_run(self, request):
        self.result = verdicts[min(calls["render"] - 1, 1)]
        self.state = AgentState.FINISHED
        return self.result

    import app.agents.director as d

    def fake_edit(self, ctx):
        calls["edit"] += 1
        self.result = _mk_edl()
        self.state = AgentState.FINISHED
        return self.result

    ctx = {
        "mode": "vlog", "max_rounds": 3, "cancelled": lambda: False,
        "apply_vlog_subs": lambda e: (calls.__setitem__("subs", calls["subs"] + 1), [], False, None)[1:],
        "save_snapshot": lambda e, review=None: calls.__setitem__("snapshot", calls["snapshot"] + 1),
        "save_new_version": lambda e: calls.__setitem__("new_version", calls["new_version"] + 1),
        "render": lambda e: calls.__setitem__("render", calls["render"] + 1),
        "export_path": lambda: "/tmp/x.mp4",
    }
    import unittest.mock as mock
    with mock.patch.object(d.ReviewerAgent, "run", fake_review_agent_run), \
         mock.patch.object(d.EditorAgent, "run", fake_edit):
        director = DirectorAgent(ctx, initial_edl=_mk_edl())
        out = director.run()
    assert director.state == AgentState.FINISHED
    assert calls["render"] == 2 and calls["new_version"] == 1, calls
    assert out["review"]["pass"] and out["review"]["rounds"] == 2
