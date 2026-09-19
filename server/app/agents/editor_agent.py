"""剪辑师智能体：产出 EDL —— LLM 优先（带硬校验层），规则引擎兜底。

对应原 pipeline._build_edl_with_llm；提示词资产来自 prompts/editor.py。
"""
from __future__ import annotations

import time

from ..core import autocut
from ..prompts import editor as editor_prompts
from ..repositories import assets as assets_repo
from ..schemas.edl import Aspect, Audio, Caption, Clip, EDL, Meta, Transition, TransitionStyle, TransitionType
from ..core import llm as qwen_vl
from ..core import llm_config
from .base import AgentState, BaseAgent

_TRANS_MAP = {
    "dissolve": TransitionType.dissolve, "push_in": TransitionType.push_in,
    "flash": TransitionType.flash, "none": TransitionType.none, "iris": TransitionType.iris,
}


class EditorAgent(BaseAgent):
    """输入 ctx（dict），输出 EDL。ctx 键：user_id/project_id/title/assets/music/preference/prompt/use_llm。"""

    name = "editor"
    max_steps = 2

    def __init__(self, on_event=None):
        super().__init__(on_event=on_event)
        self.used_llm = False

    def step(self, ctx: dict) -> None:
        pref = dict(ctx.get("preference") or {})
        mode = pref.get("mode", "normal")
        prompt = editor_prompts.build_edit_prompt(ctx.get("prompt", ""), mode)
        if ctx.get("use_llm"):
            try:
                self.result = self._build_with_llm(ctx, pref, mode, prompt)
                self.used_llm = True
                self.state = AgentState.FINISHED
                return
            except Exception as e:  # noqa: BLE001 LLM 失败 → 规则引擎兜底
                self.emit(f"AI 剪辑方案失败（{str(e)[:60]}），改用本地规则引擎")
        rule_pref = {**pref, "duration": "full"} if mode == "vlog" else pref
        self.result = autocut.build_edl(ctx["title"], ctx["assets"], ctx.get("music"), rule_pref, seed=ctx.get("seed"))
        self._apply_voice_pref(self.result, pref, mode)
        self.state = AgentState.FINISHED

    def _apply_voice_pref(self, edl: EDL, pref: dict, mode: str) -> None:
        """原声 off/on 在每次出方案时落位（重剪轮不丢）；auto 由字幕阶段按是否有配音决定。"""
        ov = (pref or {}).get("originalVoice", "auto")
        if ov == "off":
            edl.audio.keepOriginal = False
        elif ov == "on":
            edl.audio.keepOriginal = True
        edl.meta.preference["mode"] = mode

    # ---- LLM 路径（含硬校验层：明确性要求不依赖 AI 自觉） ----
    def _build_with_llm(self, ctx: dict, pref: dict, mode: str, prompt: str) -> EDL:
        project_id, assets = ctx["project_id"], ctx["assets"]
        number_of = {a["id"]: i + 1 for i, a in enumerate(assets_repo.for_project(project_id))}
        scenes = []
        for a in assets:
            ana = a.get("analysis", {})
            vl = ana.get("vlScene", {})
            scenes.append({
                "assetId": a["id"], "序号": number_of.get(a["id"], len(scenes) + 1),
                "durationMs": a.get("duration_ms") or 0,
                "sceneType": vl.get("scene_type", ana.get("sceneSummary", {}).get("label", "未知")),
                "description": vl.get("description", ""), "mood": vl.get("mood", ""),
                "movement": vl.get("movement", ""), "suggestedPacing": vl.get("suggested_pacing", ""),
                "segments": vl.get("segments", []),
                "localLabel": ana.get("sceneSummary", {}).get("label", ""),
                "brightness": ana.get("sceneSummary", {}).get("brightness", 128),
            })
        llm_pref = {"duration": pref.get("duration", "fit"), "aspect": pref.get("aspect", "9:16"),
                    "transitionStyle": pref.get("transitionStyle", "gentle"), "mode": mode}
        cur = llm_config.get_current_model(ctx["user_id"])
        self.emit(f"生成剪辑方案 → {cur.get('name')}({cur.get('llm_model', '?')}) …")
        t0 = time.time()
        llm_result = qwen_vl.generate_smart_edl(ctx["title"], scenes, llm_pref, prompt=prompt, user_id=ctx["user_id"])
        self.emit(f"剪辑方案生成完毕({time.time() - t0:.1f}s)：{len(llm_result.get('clips', []))} 个片段")

        # 硬校验 1：要求完整保留 → 全素材不裁剪
        keep_full_kw = any(kw in ctx.get("prompt", "") for kw in editor_prompts.KEEP_FULL_KEYWORDS)
        if keep_full_kw or pref.get("duration") == "full":
            llm_result["clips"] = [{"assetId": s["assetId"], "inMs": 0, "outMs": s["durationMs"],
                                    "note": "按用户要求完整保留"} for s in scenes]
        # 硬校验 2：45s 且无提示词 → 等比压缩
        elif pref.get("duration") == "45s" and not ctx.get("prompt"):
            clips_raw = llm_result.get("clips", [])
            total = sum(max(0, c.get("outMs", 0) - c.get("inMs", 0)) for c in clips_raw)
            if total > 45_500:
                ratio = 45_000 / total
                for c in clips_raw:
                    c["outMs"] = c.get("inMs", 0) + max(500, int((c.get("outMs", 0) - c.get("inMs", 0)) * ratio))

        clips = []
        for idx, c in enumerate(llm_result.get("clips", [])):
            row = next((a for a in assets if a["id"] == c["assetId"]), None)
            if not row:
                continue
            max_ms = row.get("duration_ms") or 0
            in_ms = max(0, c.get("inMs", 0))
            out_ms = min(c.get("outMs", max_ms), max_ms)
            if out_ms <= in_ms:
                out_ms = min(in_ms + 2000, max_ms)
            clips.append(Clip(assetId=c["assetId"], inMs=in_ms, outMs=out_ms, note=c.get("note", ""),
                              fadeInMs=800 if idx == 0 else 0,
                              fadeOutMs=1200 if idx == len(llm_result["clips"]) - 1 else 0))
        if not clips:
            raise RuntimeError("LLM 未生成有效片段")

        style = TransitionStyle(pref.get("transitionStyle", "gentle"))
        transitions = [Transition(afterClip=t["afterClip"],
                                  type=_TRANS_MAP.get(t.get("type", "dissolve"), TransitionType.dissolve),
                                  durMs=min(max(t.get("durMs", 800), 200), 2000),
                                  beatAligned=style != TransitionStyle.minimal)
                       for t in llm_result.get("transitions", [])]

        music = ctx.get("music")
        audio = Audio(musicId=music["musicId"], volume=0.65, offsetMs=music.get("chorusMs") or 0,
                      fadeInMs=1500, fadeOutMs=2000) if music else Audio()
        total_ms = sum(c.outMs - c.inMs for c in clips) - sum(
            t.durMs for t in transitions if t.type != TransitionType.none)
        aspect = Aspect(pref.get("aspect", "9:16"))
        captions = [
            Caption(text=ctx["title"], startMs=0, endMs=min(3000, total_ms), style="title"),
            Caption(text=f"{ctx['title']} · 闪剪AI", startMs=max(total_ms - 3000, 0), endMs=total_ms,
                    style="ending_credit"),
        ]
        return self._apply_voice_pref(
            EDL(meta=Meta(title=ctx["title"], aspect=aspect,
                          preference={"duration": llm_pref["duration"],
                                      "transitionStyle": style.value, "aspect": aspect.value}),
                clips=clips, transitions=transitions, audio=audio, captions=captions),
            pref, mode)
