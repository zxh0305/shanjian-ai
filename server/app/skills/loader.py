"""Skill 层 · 流程性知识资产（兼容 Anthropic SKILL.md 形态）。

- 内置：app/skills/builtin/<name>/SKILL.md（随代码走，git 管理）；
- 用户：<data_dir>/skills/<name>/SKILL.md（可自定义，改完即生效——热加载）；
- 同名时用户覆盖内置；
- 渐进式披露：list_skills 只给 name+description，正文 get_skill 时才读。
SKILL.md 形态：YAML 迷你 frontmatter（name/description 两行）+ markdown 正文。
"""
from __future__ import annotations

import re
from pathlib import Path

from ..config import DATA_DIR

BUILTIN_DIR = Path(__file__).resolve().parent / "builtin"

_FM = re.compile(r"\A---\s*\nname:\s*(\S+)\s*\ndescription:\s*(.+?)\s*\n(---\s*\n)?", re.S)


def _user_dir() -> Path:
    return Path(DATA_DIR) / "skills"


def _parse(skill_md: Path) -> tuple[str, str, str] | None:
    """返回 (name, description, body)；解析失败返回 None。"""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _FM.match(text.strip())
    if not m:
        return None
    name, desc = m.group(1), m.group(2)
    body = text.strip()[m.end():].strip()
    return name, desc, body


def _all_skills() -> dict[str, tuple[str, str, str, str]]:
    """name -> (description, body, source, path)。用户覆盖内置。"""
    out: dict[str, tuple[str, str, str, str]] = {}
    for base, source in ((BUILTIN_DIR, "builtin"), (_user_dir(), "user")):
        if not base.is_dir():
            continue
        for md in sorted(base.glob("*/SKILL.md")):
            parsed = _parse(md)
            if parsed:
                name, desc, body = parsed
                out[name] = (desc, body, source, str(md))
    return out


def list_skills() -> list[dict]:
    """全部 skill 的名字与描述（渐进式披露：正文按需再取）。"""
    return [{"name": n, "description": d, "source": src}
            for n, (d, _, src, _) in sorted(_all_skills().items())]


def get_skill(name: str) -> str | None:
    """读正文；不存在返回 None。"""
    item = _all_skills().get(name)
    return item[1] if item else None


def skill_text(name: str, fallback: str = "") -> str:
    """消费方入口：有 skill 用正文，没有退回代码内置文案（行为不回归的保险）。"""
    return get_skill(name) or fallback


def narration_style_text(key: str) -> str:
    """文案风格解析：narration-{key} skill 的「描述 + 正文」，并追加口语化底线；未知名退回幽默。"""
    skills = _all_skills()
    name = f"narration-{(key or 'humor').strip().lower()}"
    if name not in skills:
        name = "narration-humor"
    desc, body = skills[name][0], skills[name][1]
    style = f"{desc}。{body}" if body else desc
    baseline = skills.get("narration-baseline")
    if baseline and baseline[1]:
        style += "\n\n" + baseline[1]
    return style
