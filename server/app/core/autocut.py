"""自动剪辑规则引擎（W5）：素材分析结果 + 配乐 + 成片偏好 → EDL。

叙事结构（对应原型「AI 是这么排的」）：
  开场(片头淡入) → 收集节奏段 → 情绪高点(对齐鼓点) → 收尾(片尾淡出)
选段：画质分 + 能量峰值排序；排序：按场景标签与能量曲线起伏。
MVP 确定性：同 seed 同结果，换个剪法 = 换 seed。
"""
from __future__ import annotations

import random

from ..schemas.edl import (Aspect, Audio, Caption, Clip, EDL, Meta, TargetDuration,
                           Transition, TransitionStyle, TransitionType)

_TRANS_OF_STYLE = {
    TransitionStyle.gentle: TransitionType.dissolve,
    TransitionStyle.dynamic: TransitionType.flash,
    TransitionStyle.minimal: TransitionType.none,
}


def build_edl(
    project_title: str,
    assets: list[dict],          # db assets 行（含 analysis 场景数据 key: analysis）
    music: dict | None,          # music_match.candidates()[0] 形状
    preference: dict,
    seed: int | None = None,
) -> EDL:
    rng = random.Random(seed)
    pref_duration = preference.get("duration", "fit")
    pref_style = TransitionStyle(preference.get("transitionStyle", "gentle"))
    pref_aspect = Aspect(preference.get("aspect", "9:16"))

    # ---- 选段：每个素材取最优镜头（画质 × 能量峰值），质量差的整段淘汰 ----
    scored_assets = []
    for a in assets:
        ana = a["analysis"]
        best_scene = max(
            ana["scenes"],
            key=lambda s: (s["endMs"] - s["startMs"]) * (a.get("qualityScore") or 0.5),
        )
        seg_len = best_scene["endMs"] - best_scene["startMs"]
        # 段长控制在 8–38s：太长取能量子窗，太短放宽
        if seg_len > 38_000:
            start = best_scene["startMs"] + (rng.randrange(0, seg_len - 38_000) if seed is not None else 0)
            best_scene = {**best_scene, "startMs": start, "endMs": start + 38_000}
        scored_assets.append({**a, "scene": best_scene})

    scored_assets.sort(key=lambda a: (a.get("qualityScore") or 0.5) * (a["scene"]["endMs"] - a["scene"]["startMs"]),
                       reverse=True)
    max_clips = 4 if pref_duration != TargetDuration.full.value else min(len(scored_assets), 6)
    picked = scored_assets[:max_clips]

    # ---- 排序叙事：开场(亮/稳) → 中段 → 高点(高动态) → 收尾(舒缓) ----
    def rank(a):
        label = a["analysis"]["sceneSummary"]["label"]
        order = {"明亮舒缓": 0, "日常记录": 1, "暗调氛围": 2, "高动态": 3}
        return order.get(label, 1)
    picked_sorted = [p for p in picked if rank(p) in (0, 1)] + [p for p in picked if rank(p) == 2]
    high = [p for p in picked if rank(p) == 3]
    if high:
        tail = picked_sorted[-1] if picked_sorted else None
        picked_sorted = picked_sorted[:-1] + high + ([tail] if tail and tail not in high else [])
    picked = picked_sorted

    # ---- 时长适配 ----
    # 每段时长不超过素材实际可用长度
    natural = []
    for a in picked:
        s = a["scene"]
        avail = (s["endMs"] - s["startMs"]) // 1000
        natural.append(max(avail, 2))

    if pref_duration == TargetDuration.s45.value:
        target_total, weights = 45, natural
    elif pref_duration == TargetDuration.full.value:
        target_total, weights = sum(natural), natural
    else:  # fit：取自然长度的 0.8，不低于 8s 但不超实际素材总长
        src_total = sum(natural)
        target_total = max(8, min(int(src_total * 0.8), src_total))
        weights = natural
    scale = target_total / max(sum(weights), 1)
    durations = []
    for i, n in enumerate(natural):
        d = max(int(n * scale), 2)
        durations.append(min(d, natural[i]))  # 不超实际可用长度

    # ---- 组装 clips + 转场 ----
    clips: list[Clip] = []
    total_now = 0
    for i, (a, dur_s) in enumerate(zip(picked, durations)):
        s = a["scene"]
        role = _role(i, len(picked))
        fade_in = 800 if i == 0 else 0
        fade_out = 1200 if i == len(picked) - 1 else 0
        clips.append(Clip(
            assetId=a["id"], inMs=s["startMs"], outMs=s["startMs"] + dur_s * 1000,
            note=role, fadeInMs=fade_in, fadeOutMs=fade_out,
        ))
        total_now += dur_s

    trans_dur = 800 if pref_style == TransitionStyle.gentle else 400
    base_type = _TRANS_OF_STYLE[pref_style]
    transitions = []
    for i in range(len(clips) - 1):
        t = Transition(afterClip=i + 1, type=base_type, durMs=trans_dur,
                       beatAligned=pref_style != TransitionStyle.minimal)
        # 情绪高点前一个剪辑点用推近（对应原型「推近×1」）
        if i + 2 == len(clips) and len(clips) >= 3:
            t = Transition(afterClip=i + 1, type=TransitionType.push_in, durMs=trans_dur,
                           beatAligned=pref_style != TransitionStyle.minimal)
        transitions.append(t)

    audio = Audio()
    if music:
        audio = Audio(musicId=music["musicId"], volume=0.65,
                      offsetMs=music.get("chorusMs") or 0, fadeInMs=1500, fadeOutMs=2000)

    total_ms = sum(c.outMs - c.inMs for c in clips) - sum(
        t.durMs for t in transitions if t.type != TransitionType.none)
    captions = [
        Caption(text=project_title, startMs=0, endMs=min(3000, total_ms), style="title"),
        Caption(text=f"{project_title} · 闪剪AI", startMs=max(total_ms - 3000, 0),
                endMs=total_ms, style="ending_credit"),
    ]
    meta = Meta(title=project_title, aspect=pref_aspect, seed=seed,
                preference={"duration": pref_duration, "transitionStyle": pref_style.value,
                            "aspect": pref_aspect.value})

    return EDL(meta=meta, clips=clips, transitions=transitions, audio=audio, captions=captions)


def _role(i: int, n: int) -> str:
    if i == 0:
        return "开场 · 片头淡入"
    if i == n - 1:
        return "收尾 · 片尾淡出"
    if i == n - 2 and n >= 3:
        return "情绪高点 · 对齐鼓点"
    return "节奏段 · 跟随配乐"
