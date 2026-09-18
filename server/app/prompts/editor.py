"""剪辑师智能体 · 提示词资产。

风格与节奏类知识已资产化为 skills/（内置 narration-*、vlog-pacing，用户可在
data/skills/ 覆盖或新增）；本模块只保留结构性规则与 skill 缺失时的兜底文案。
"""
from ..skills import loader

# 兜底：skill 资产缺失时保持行为不回归（正常情况读 skills/builtin/vlog-pacing）
VLOG_MODE_RULE = (
    "【Vlog 口播模式】素材含口播语音：必须保持语音连贯，禁止在人说话的句子中间切断；"
    "优先按语音叙事顺序编排片段，宁可少剪也不要裁掉说话内容；"
    "硬性要求：每个片段的保留时长不低于 2.5 秒（素材本身更短才允许例外），"
    "片段总数宁少勿多——段太短旁白读不完。"
)

ASSET_NUMBER_RULE = (
    "素材列表每项带「序号」字段（与页面上素材卡片的编号一致）；"
    "用户要求里的「第N段」即序号为 N 的素材，例如「只用第1、3段」表示只采用序号 1 和 3 的素材。"
)

KEEP_FULL_KEYWORDS = ("保持原时长", "不裁剪", "不裁", "完整保留", "原时长", "保持原样", "不要裁剪")


def build_edit_prompt(user_prompt: str, mode: str, feedback: str = "") -> str:
    """拼装最终剪辑指令：用户要求 + Vlog 节奏规范(skill) + 序号规则 +（重剪时的）审查意见。"""
    parts = []
    if user_prompt:
        parts.append(user_prompt)
    if mode == "vlog":
        parts.append(loader.skill_text("vlog-pacing", VLOG_MODE_RULE))
    parts.append(ASSET_NUMBER_RULE)
    if feedback:
        parts.append("【上一版审查意见，这一版必须改进】" + feedback)
    return "\n".join(parts)
