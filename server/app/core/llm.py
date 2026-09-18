"""LLM 调用的提示词与结果解析层。

流程：抽帧（带时间戳）→ 视觉模型按时段理解内容 → LLM 综合内容语义+用户提示词生成EDL。
所有模型调用经 core/gateway（任务路由/重试/降级/计量），本模块不接触密钥与供应商。
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path

from ..config import settings


def _gw():
    from . import gateway  # 惰性导入：网关内部会回调本模块构造 client
    return gateway


def extract_key_frames(video_path: str | Path, count: int = 6) -> list[dict]:
    """从视频中均匀抽取 N 帧作为关键帧。

    返回 [{path, timeMs}]，带时间戳，供内容时段分析。
    """
    video_path = str(video_path)
    ffprobe = settings.ffprobe

    out = subprocess.run(
        [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", video_path],
        capture_output=True, text=True, timeout=30,
    )
    duration = float(json.loads(out.stdout)["format"]["duration"]) if out.stdout.strip() else 0
    if duration <= 0:
        return []

    tmp_dir = tempfile.mkdtemp(prefix="qwen_frames_")
    frames = []
    for i in range(count):
        t = duration * (i + 0.5) / count
        out_path = os.path.join(tmp_dir, f"frame_{i:02d}.jpg")
        subprocess.run(
            [settings.ffmpeg, "-y", "-ss", f"{t:.2f}", "-i", video_path,
             "-frames:v", "1", "-q:v", "3", out_path],
            capture_output=True, timeout=30,
        )
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            frames.append({"path": out_path, "timeMs": int(t * 1000)})
    return frames


def _image_to_data_url(path: str) -> str:
    """图片转 base64 data URL。"""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/jpeg;base64,{b64}"


def _parse_json(text: str) -> dict | None:
    """解析 LLM 返回的 JSON，容错 markdown 代码块。"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def analyze_scenes_with_vl(asset_path: str, frames: list[dict], user_id: int = 1) -> dict:
    """调用视觉模型按时段理解视频内容。

    frames: [{path, timeMs}]，返回:
    {scene_type, description, mood, colors, movement, suggested_pacing,
     segments: [{startMs, endMs, description, highlight(0-10 精彩程度), keep(bool)}]}
    """
    content_text = (
            "这是一个视频按时间顺序抽取的关键帧，每帧下方标注了它在视频中的时间点（毫秒）。"
            "请按时段理解视频内容，返回JSON：\n"
            "{\n"
            '  "scene_type": "场景类型(自然风光/城市建筑/人物活动/美食/运动/室内/夜景等)",\n'
            '  "description": "整体内容一句话",\n'
            '  "mood": "情绪基调(欢快/宁静/紧张/温馨/神秘/活力等)",\n'
            '  "colors": ["主色调"],\n'
            '  "movement": "画面动态(高/中/低)",\n'
            '  "suggested_pacing": "建议节奏(快切/中速/慢摇)",\n'
            '  "segments": [\n'
            '    {"startMs": 0, "endMs": 3000, "description": "该时段画面内容", '
            '"highlight": 8, "keep": true}\n'
            "  ]\n"
            "}\n"
            "segments 按时间顺序覆盖整个视频；highlight 是该时段的精彩程度评分(0-10，"
            "模糊/晃动/无意义画面给低分，主体清晰/有故事性给高分)；"
            "keep 表示是否值得出现在成片里。只返回纯JSON。"
        )
    imgs = [_image_to_data_url(f["path"]).split("base64,", 1)[-1] for f in frames]
    times = "".join(f"[t={f['timeMs']}ms]" for f in frames)
    out = _gw().vision("analyze_scenes", content_text + "\n关键帧时间点：" + times, imgs,
                       user_id=user_id, temperature=0.3)
    result = _parse_json(out["text"])
    if not result:
        return {"scene_type": "未知", "description": out["text"][:200],
                "mood": "未知", "colors": [], "movement": "低",
                "suggested_pacing": "中速", "segments": []}
    result.setdefault("segments", [])
    return result


def generate_smart_edl(project_title: str, scenes: list[dict], preference: dict,
                       prompt: str = "", user_id: int = 1) -> dict:
    """调用 LLM 按内容理解 + 用户提示词生成 EDL（剪辑决策列表）。

    scenes: [{assetId, durationMs, sceneType, description, mood, movement,
              suggestedPacing, segments:[{startMs,endMs,description,highlight,keep}], ...}]
    preference: {duration, aspect, transitionStyle}
    prompt: 用户自然语言剪辑指令（如"节奏快一点，只保留海边镜头，总长30秒内"）
    返回: {clips: [{assetId, inMs, outMs, note}], transitions: [{afterClip, type, durMs}], reason}
    """
    scene_desc = json.dumps(scenes, ensure_ascii=False, indent=2)
    pref_desc = json.dumps(preference, ensure_ascii=False)
    prompt_block = (f"\n## 用户剪辑要求（最高优先级，必须遵守）\n{prompt}\n"
                    "用户要求与默认规则冲突时，以用户要求为准。比如用户要求只保留某类画面、"
                    "指定总时长、指定节奏时，必须严格执行。\n") if prompt else ""

    prompt_text = f"""你是专业视频剪辑师。下面是 AI 视觉模型对每个素材的分时段内容理解，
请据此生成剪辑方案：智能裁掉低质量/无意义片段，保留精彩内容，按叙事排布。

## 素材列表（含分时段内容、精彩度评分）
{scene_desc}
{prompt_block}
## 成片偏好
{pref_desc}

## 规则
1. 从素材的 segments 中挑选值得保留的时段（highlight 高、keep=true 优先），
   inMs/outMs 应落在对应时段内，可多次使用同一素材的不同时段
2. 每段 outMs-inMs 不超过素材 durationMs，也不超过该 segment 的 endMs
3. 总时长严格遵循 preference.duration：fit=素材精彩内容自然长度，45s=45秒内，full=完整保留所有素材（不裁剪，成片总时长≈素材总时长）。
   用户填了剪辑要求时，提示词优先级最高；没填时，duration选项必须严格执行。
4. 转场类型: dissolve(叠化) / push_in(推近) / flash(闪白) / none(硬切)
5. 每段 note 用一句话说明"为什么留这段"
6. 【重要】每个片段时长建议 3~10 秒，一般不要低于 2 秒（用户明确要求快节奏/卡点除外）。
   不要把素材切成大量一两秒的碎片段。
7. 【重要】用户指令理解：
   - "保持原时长 / 不裁剪 / 完整保留" = 每个素材完整保留（inMs=0，outMs=durationMs），
     只调整播放顺序和转场，成片总时长≈所有素材总时长
   - "总长N秒/N秒内" = 所有片段总时长控制在 N 秒附近
   - "只保留XX" = 仅保留含 XX 内容的时段，其余全部裁掉
8. 输出纯JSON，格式：
{{
  "clips": [
    {{"assetId": 1, "inMs": 0, "outMs": 5000, "note": "开场 · 海边全景，画面稳定色彩好"}}
  ],
  "transitions": [
    {{"afterClip": 1, "type": "dissolve", "durMs": 800}}
  ],
  "reason": "简述剪辑思路"
}}

只返回JSON。"""

    out = _gw().chat("build_edl", [{"role": "user", "content": prompt_text}],
                     user_id=user_id, temperature=0.4)
    result = _parse_json(out["text"])
    if not result or not result.get("clips"):
        # 降级：返回最简单的串联方案
        clips = [{"assetId": s["assetId"], "inMs": 0,
                  "outMs": s["durationMs"], "note": "默认串联"}
                 for s in scenes]
        transitions = [{"afterClip": i + 1, "type": "dissolve", "durMs": 800}
                       for i in range(len(clips) - 1)]
        return {"clips": clips, "transitions": transitions,
                "reason": "LLM解析失败，使用默认串联"}
    return result


def cleanup_frames(frames: list[dict]) -> None:
    """清理临时帧文件。"""
    for f in frames:
        try:
            path = f["path"] if isinstance(f, dict) else f
            os.remove(path)
            d = os.path.dirname(path)
            if os.path.isdir(d) and not os.listdir(d):
                os.rmdir(d)
        except OSError:
            pass


def generate_narration(clips: list[dict], style_text: str, project_title: str = "", user_id: int = 1) -> dict:
    """按风格为每段视频写一句旁白字幕（短视频文案）。

    clips: [{index, durationS, description}] → {"lines": ["...", ...]}，条数与 clips 一致。
    style_text：风格规范全文（来自 skills/narration-*，经 cut_flow.narration_style_text 解析）。
    """

    prompt = f"""你是短视频旁白文案师。按下面的风格规范，为每一段视频写一句旁白字幕。

## 风格规范
{style_text}

要求：
- 每句 8~20 个字，口语化、可直接朗读
- 与该段画面内容呼应，连起来有连贯的叙事感
- 视频标题：「{project_title or '无'}」
- 只输出 JSON：{{"lines": ["第一句", "第二句", ...]}}，lines 条数必须等于 {len(clips)}

分段视频：
{json.dumps(clips, ensure_ascii=False, indent=1)}"""
    try:
        out = _gw().chat("write_narration", [{"role": "user", "content": prompt}],
                         user_id=user_id, temperature=0.8, max_tokens=2000)
        text = out["text"]
    except Exception as e:
        return {"error": f"文案生成调用失败: {str(e)[:180]}"}
    import re as _re
    m = _re.search(r"\{[\s\S]*\}", text)
    if not m:
        return {"error": "模型未返回有效 JSON，请重试"}
    try:
        lines = json.loads(m.group(0)).get("lines", [])
    except json.JSONDecodeError:
        return {"error": "文案 JSON 解析失败，请重试"}
    lines = [str(x).strip() for x in lines][:len(clips)]
    while len(lines) < len(clips):
        lines.append("")
    return {"lines": lines}


def review_cut(frames_b64: list[str], prompt_text: str, user_id: int = 1) -> dict:
    """剪辑总监自检：看成片抽帧 → verdict。提示词由 prompts/reviewer（review-rubric skill）组装。"""
    try:
        out = _gw().vision("review_cut", prompt_text, frames_b64, user_id=user_id, max_tokens=2000)
        text = out["text"]
    except Exception as e:
        return {"error": f"审查调用失败: {str(e)[:160]}"}
    import re as _re
    # 容错解析：模型可能带 ```json 围栏或前后解说文字
    if "```" in text:
        fenced = _re.findall(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fenced:
            text = fenced[0]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return {"error": f"审查未返回有效 JSON（原文: {text[:120]}）"}
    try:
        d = json.loads(text[start:end + 1])
        return {"score": int(d.get("score", 0)), "pass": bool(d.get("pass")),
                "comment": str(d.get("comment", ""))[:120],
                "suggestions": [str(x)[:150] for x in (d.get("suggestions") or [])][:3]}
    except Exception:
        return {"error": f"审查结果解析失败（原文: {text[start:start + 120]}）"}
