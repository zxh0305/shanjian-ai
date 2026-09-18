"""审片官智能体 · 提示词资产（评分标准资产化为 skills/review-rubric，缺失时退回内置文案）。"""
from ..skills import loader

PASS_SCORE = 80

# 兜底：skill 资产缺失时保持行为不回归（正常情况读 skills/builtin/review-rubric）
_RUBRIC_FALLBACK = """## 评分维度（0-100）
1. 节奏：片段长短分布是否张弛有度，有没有拖沓或过于碎片化
2. 画面：开头是否抓人、段落衔接是否顺、结尾是否收得住
3. 字幕/旁白：与画面内容是否匹配、语言是否自然（若有配音，考虑朗读节奏）"""

REVIEW_PROMPT = """你是严苛的短视频剪辑总监，审查下面这支成片（按时间顺序的关键帧）。

{rubric}

成片数据摘要：
{summary}

要求：打分 0-100；{pass_score} 分及以上且无硬伤才算通过。只输出 JSON：
{{"score": 78, "pass": false, "comment": "一句话总评", "suggestions": ["具体可执行的改进建议", ...]}}（suggestions 最多 3 条）"""


def review_prompt(summary: str) -> str:
    return REVIEW_PROMPT.format(rubric=loader.skill_text("review-rubric", _RUBRIC_FALLBACK),
                                summary=summary, pass_score=PASS_SCORE)
