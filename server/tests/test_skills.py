"""Skill 层与 MCP 薄壳单测：渐进披露/用户覆盖热加载/风格解析回退；MCP 工具清单与 schema。"""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

os.environ.setdefault("SHANJIAN_DATA_DIR", tempfile.mkdtemp(prefix="shanjian_skills_"))

from app.skills import loader  # noqa: E402


def test_builtin_skills_listed():
    names = {s["name"] for s in loader.list_skills()}
    assert {"narration-humor", "narration-serious", "narration-warm", "narration-literary",
            "review-rubric", "vlog-pacing"} <= names
    assert all(s["description"] for s in loader.list_skills())   # 渐进披露：常驻只有描述


def test_get_skill_body_and_fallback():
    body = loader.get_skill("review-rubric")
    assert body and "硬性扣分项" in body
    assert loader.get_skill("no-such-skill") is None
    assert loader.skill_text("no-such-skill", fallback="兜底") == "兜底"


def test_narration_style_resolution():
    four = {loader.narration_style_text(k) for k in ("humor", "serious", "warm", "literary")}
    assert len(four) == 4                              # 四种风格互不相同
    assert "玩梗" in loader.narration_style_text("humor")
    assert loader.narration_style_text("unknown-key") == loader.narration_style_text("humor")


def test_user_dir_overrides_and_hot_reload(tmp_path, monkeypatch):
    """用户目录同名覆盖 + 新增即生效（热加载）。"""
    monkeypatch.setattr(loader, "DATA_DIR", tmp_path)
    user_skill = tmp_path / "skills" / "narration-humor" / "SKILL.md"
    user_skill.parent.mkdir(parents=True)
    user_skill.write_text(
        "---\nname: narration-humor\ndescription: 用户自定义毒舌风\n---\n嘴替模式：怎么损怎么来。",
        encoding="utf-8")

    src = {s["name"]: s["source"] for s in loader.list_skills()}
    assert src["narration-humor"] == "user"            # 同名覆盖内置
    assert "毒舌" in loader.narration_style_text("humor")

    # 热加载：再写一个全新 skill，下一次调用即可见
    extra = tmp_path / "skills" / "narration-roast" / "SKILL.md"
    extra.parent.mkdir(parents=True)
    extra.write_text("---\nname: narration-roast\ndescription: 烤串风\n---\n正文。",
                     encoding="utf-8")
    assert any(s["name"] == "narration-roast" for s in loader.list_skills())
    assert "烤串风" in loader.narration_style_text("roast")


def test_consumers_read_skills():
    """提示词资产确实从 skills 取材（评审含评分表正文、vlog 含节奏规范）。"""
    from app.prompts import editor, reviewer
    assert "硬性扣分项" in reviewer.review_prompt("摘要")
    assert "2.5 秒" in editor.build_edit_prompt("", "vlog")
    assert "2.5 秒" not in editor.build_edit_prompt("", "normal")   # 非 vlog 不注入


def _tools(mod):
    return asyncio.run(mod.mcp.list_tools())


def test_mcp_servers_expose_tools():
    """两个领域 server 的工具清单与必填参数（注册 Claude 等宿主前的契约自检）。"""
    from app.tools.mcp import server_analysis, server_render

    ana = {t.name: t.inputSchema.get("required", []) for t in _tools(server_analysis)}
    ren = {t.name: t.inputSchema.get("required", []) for t in _tools(server_render)}
    assert set(ana) == {"probe_media", "extract_keyframes", "transcribe_audio"}
    assert set(ren) == {"render_edl", "synth_tts"}
    assert ana["probe_media"] == ["path"]
    assert ren["render_edl"] == ["project_id", "edl_json"]
