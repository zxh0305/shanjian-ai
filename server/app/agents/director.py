"""剪辑总监智能体（by_order 固定流水线）：编排 剪辑师 → Vlog字幕 → 渲染 → 审片官。

一轮 = [EDIT] → [SUBS] → [RENDER] → [REVIEW]；审片不达标则带着意见回到 EDIT 重剪，
最多 max_rounds 轮（默认 3）。所有副作用（存快照/渲染/字幕）经 ctx 注入的回调执行，
本模块只做编排决策——依赖方向保持 agents → tools/core/repositories。
"""
from __future__ import annotations

from typing import Callable

from ..schemas.edl import EDL
from .base import AgentState, BaseAgent
from .editor_agent import EditorAgent
from .reviewer_agent import ReviewerAgent


class DirectorAgent(BaseAgent):
    name = "director"

    def __init__(self, ctx: dict, initial_edl: EDL | None = None, on_event=None):
        super().__init__(on_event=on_event)
        self.ctx = ctx
        self.max_steps = 6 + ctx.get("max_rounds", 1) * 3   # 每轮最多 3 步 + 余量
        self.edl: EDL | None = initial_edl
        self.review: dict | None = None
        self.review_note: str = ""
        self.sub_note: str = ""
        self.attempt = 1 if initial_edl is not None else 0
        self.phase = "subs" if initial_edl is not None else "edit"
        self._feedback = ""

    # ---- 各阶段 ----
    def _do_edit(self) -> None:
        self.attempt += 1
        if self.attempt > 1:
            self.emit(f"按审查意见优化（第 {self.attempt - 1} 次）")
        editor = EditorAgent(on_event=self._on_event)
        req = {**self.ctx, "prompt": self.ctx.get("prompt", ""), "_feedback": self._feedback}
        if self._feedback:
            from ..prompts import editor as editor_prompts
            req["prompt"] = (req["prompt"] + "\n" if req["prompt"] else "") + \
                "【上一版审查意见，这一版必须改进】" + self._feedback
        edl = editor.run(req)
        if editor.state == AgentState.ERROR or edl is None:
            raise RuntimeError(editor.error or "剪辑师未能产出方案")
        self.edl = edl
        if self.attempt > 1:
            self.ctx["save_new_version"](edl)   # 重剪产生新快照
        self.phase = "subs"

    def _do_subs(self) -> None:
        if self.ctx.get("mode") == "vlog" and self.ctx.get("apply_vlog_subs"):
            _, _, err = self.ctx["apply_vlog_subs"](self.edl)
            if err:
                self.sub_note = self.sub_note or err
            elif not [c for c in self.edl.captions if c.style == "subtitle"]:
                self.sub_note = self.sub_note or "Vlog 没有识别到语音/没生成字幕，可到编辑器「文字」页手动添加"
        self.ctx["save_snapshot"](self.edl)
        self.phase = "render"

    def _do_render(self) -> None:
        self.emit("渲染成片")
        self.ctx["render"](self.edl)      # 失败会抛，交由 BaseAgent 兜底为 ERROR
        self.phase = "review"

    def _do_review(self) -> None:
        if self.ctx.get("max_rounds", 1) <= 1:
            self.phase = "done"
            return
        self.emit(f"AI 审查（第 {self.attempt} 轮）")
        reviewer = ReviewerAgent(on_event=self._on_event)
        verdict = reviewer.run((self.edl, self.ctx["export_path"](), self.ctx.get("user_id", 1)))
        if not verdict or "error" in verdict:
            self.emit(f"审查失败（交付当前版本）：{(verdict or {}).get('error', '未知')}")
            self.phase = "done"
            return
        self.emit(f"评分 {verdict['score']} · {'通过' if verdict['pass'] else '不通过'} · {verdict['comment']}")
        for sug in verdict.get("suggestions", []):
            self.emit(f"   - {sug}")
        if verdict["pass"] or self.attempt >= self.ctx.get("max_rounds", 1):
            self.review = {**verdict, "rounds": self.attempt}
            self.ctx["save_snapshot"](self.edl, review=self.review)
            if not verdict["pass"]:
                self.review_note = (f"自检 {self.attempt} 轮后仍未达标（{verdict['score']} 分），"
                                    f"已交付最优版本，可手动微调")
            self.phase = "done"
        else:
            self._feedback = verdict.get("comment", "") + "\n" + "\n".join(verdict.get("suggestions", []))
            self.phase = "edit"

    def step(self, request=None) -> None:
        if self.ctx.get("cancelled") and self.ctx["cancelled"]():
            self.state = AgentState.ERROR
            self.error = "已取消"
            return
        {"edit": self._do_edit, "subs": self._do_subs,
         "render": self._do_render, "review": self._do_review}.get(self.phase, lambda: None)()
        if self.phase == "done":
            self.result = {"edl": self.edl, "review": self.review,
                           "review_note": self.review_note, "sub_note": self.sub_note,
                           "attempts": self.attempt}
            self.state = AgentState.FINISHED
