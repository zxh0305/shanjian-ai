"""剪辑师智能体 · 提示词资产。"""

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

NARRATION_STYLE_TEXT = {
    "humor": "幽默风趣，像朋友聊天吐槽，可以适度玩梗调侃画面",
    "serious": "认真严谨，像纪录片解说，客观陈述有信息量",
    "warm": "温暖治愈，语气柔和，带一点生活感悟",
    "literary": "文艺清新，有画面感和诗意",
}


def build_edit_prompt(user_prompt: str, mode: str, feedback: str = "") -> str:
    """拼装最终剪辑指令：用户要求 + Vlog 规则 + 序号规则 +（重剪时的）审查意见。"""
    parts = []
    if user_prompt:
        parts.append(user_prompt)
    if mode == "vlog":
        parts.append(VLOG_MODE_RULE)
    parts.append(ASSET_NUMBER_RULE)
    if feedback:
        parts.append("【上一版审查意见，这一版必须改进】" + feedback)
    return "\n".join(parts)


def narration_prompt(style_text: str, clips: list[dict], project_title: str = "") -> str:
    """旁白文案（每段一句）提示词。"""
    import json
    return f"""你是短视频旁白文案师。为下面每一段视频写一句{style_text}风格的旁白字幕。

要求：
- 每句 8~20 个字，口语化、可直接朗读
- 与该段画面内容呼应，连起来有连贯的叙事感
- 视频标题：「{project_title or '无'}」
- 只输出 JSON：{{"lines": ["第一句", "第二句", ...]}}，lines 条数必须等于 {len(clips)}

分段视频：
{json.dumps(clips, ensure_ascii=False, indent=1)}"""
