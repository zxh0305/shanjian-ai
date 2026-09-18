"""EDL（剪辑决策列表）schema —— 全局唯一数据源（定稿 §3）。

自动成片生成它、轻编辑改它、FFmpeg 渲染消费它。
字段规格见 docs/EDL-spec.md，演示口径：4 段 18+22+34+38s、叠化×2+推近×1、82 BPM。
"""
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Clip(BaseModel):
    assetId: int
    inMs: int = Field(ge=0, description="原片入点（毫秒）")
    outMs: int = Field(gt=0, description="原片出点（毫秒），> inMs")
    note: str = ""  # 生成依据，支撑「AI 是这么排的」页，如「开场 · 片头淡入」

    fadeInMs: int = Field(default=0, ge=0)
    fadeOutMs: int = Field(default=0, ge=0)


class TransitionType(str, Enum):
    none = "none"
    dissolve = "dissolve"    # 叠化
    push_in = "push_in"      # 推近
    iris = "iris"            # 划像
    flash = "flash"          # 闪白


class Transition(BaseModel):
    afterClip: int = Field(ge=1, description="第几个剪辑点之后（1-based）")
    type: TransitionType
    durMs: int = Field(default=600, ge=100, le=2000)
    beatAligned: bool = False  # 切点是否吸附鼓点（82 BPM → 732ms 拍间隔 ±150ms）


class Audio(BaseModel):
    musicId: Optional[int] = None
    volume: float = Field(default=0.65, ge=0, le=1)
    offsetMs: int = Field(default=0, ge=0, description="音乐起点；副歌对齐时非 0")
    fadeInMs: int = Field(default=1500, ge=0)
    fadeOutMs: int = Field(default=2000, ge=0)
    keepOriginal: bool = Field(default=True, description="是否保留原声")
    originalVolume: float = Field(default=1.0, ge=0, le=1, description="原声音量")
    ttsEnabled: bool = Field(default=False, description="字幕配音：渲染时把字幕朗读出来（macOS say）")
    ttsVoice: str = Field(default="", description="配音音色（macOS say 语音名，空=自动选默认中文音色）")
    ttsRate: float = Field(default=1.0, ge=0.6, le=1.6, description="配音语速倍率，1.0=正常")
    ducking: bool = Field(default=True, description="有配音时自动压低配乐（缓入缓出到约三成）")


class Caption(BaseModel):
    text: str
    startMs: int = Field(ge=0)
    endMs: int = Field(gt=0)
    style: Literal["ending_credit", "subtitle", "title"] = "ending_credit"


class TargetDuration(str, Enum):
    s45 = "45s"
    full = "full"
    fit = "fit"  # 原型「1 分 52 秒」这类 AI 适配值


class Aspect(str, Enum):
    landscape = "16:9"
    portrait = "9:16"
    square = "1:1"


class TransitionStyle(str, Enum):
    gentle = "gentle"    # 中慢速：叠化为主（82 BPM 素材的推荐档）
    dynamic = "dynamic"  # 卡点快切
    minimal = "minimal"  # 硬切


class Meta(BaseModel):
    title: str = ""
    aspect: Aspect = Aspect.portrait
    fps: Literal[30, 60] = 30
    seed: Optional[int] = None          # 「换个剪法」= 固定 audio、换 seed 重排
    review: Optional[dict] = None       # AI 自检结论：{score, pass, comment, suggestions, rounds}
    preference: dict = Field(
        default_factory=lambda: {"duration": TargetDuration.fit, "transitionStyle": TransitionStyle.gentle},
        description="成片偏好三参数：duration/aspect 同步到本层，transitionStyle 参与转场决策",
    )


class EDL(BaseModel):
    version: int = 1
    meta: Meta = Field(default_factory=Meta)
    clips: list[Clip] = Field(min_length=1)
    transitions: list[Transition] = Field(default_factory=list)
    audio: Audio = Field(default_factory=Audio)
    captions: list[Caption] = Field(default_factory=list)

    @field_validator("clips")
    @classmethod
    def _check_order(cls, v: list[Clip]) -> list[Clip]:
        for c in v:
            if c.outMs <= c.inMs:
                raise ValueError(f"clip outMs({c.outMs}) 必须大于 inMs({c.inMs})")
        return v

    @field_validator("transitions")
    @classmethod
    def _check_transition_range(cls, v: list[Transition], info):
        clips = info.data.get("clips", [])
        if clips:
            for t in v:
                if t.afterClip >= len(clips):
                    raise ValueError(
                        f"transitions.afterClip={t.afterClip} 超出片段数 {len(clips)}（最后一个片段后无剪辑点）"
                    )
        return v

    # ---- 供信息卡与渲染直接消费的派生量 ----
    def total_duration_ms(self) -> int:
        base = sum(c.outMs - c.inMs for c in self.clips)
        overlap = sum(t.durMs for t in self.transitions if t.type != TransitionType.none)
        return base - overlap

    def trimmed_ms(self) -> int:
        """演示口径「裁掉 1 分 23 秒」：原素材总长 - 使用部分。素材总长由调用方传入资产表计算。"""
        return sum(c.inMs for c in self.clips)

    def transition_summary(self) -> str:
        names = {"dissolve": "叠化", "push_in": "推近", "iris": "划像", "flash": "闪白", "none": "无"}
        from collections import Counter
        counts = Counter(t.type for t in self.transitions)
        return " · ".join(f"{names[k.value]}×{n}" for k, n in counts.items() if k != TransitionType.none)
