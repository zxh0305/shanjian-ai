"""FFmpeg 渲染管线（W6–W7）：EDL → 成片 mp4。

支持：xfade 五种转场（叠化 fade / 推近 zoomin / 划像 circleopen / 闪白 fadewhite /
无转场=单帧硬切）、首尾淡入淡出、配乐副歌对齐与淡入淡出、画幅三档（9:16/16:9/1:1）、
分辨率三档（720P/1080P/4K）、片头标题与片尾署名字幕。
导出 v{n} 不覆盖：exports 表按 (project_id, version) 递增。
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from .. import db
from ..config import settings
from ..schemas.edl import EDL, Transition, TransitionType

# xfade 官方过渡名（ffmpeg 9 已验证支持 zoomin/circleopen/fadewhite）
XFADE_OF_TYPE = {
    TransitionType.dissolve: "fade",
    TransitionType.push_in: "zoomin",
    TransitionType.iris: "circleopen",
    TransitionType.flash: "fadewhite",
    TransitionType.none: "fade",        # 无转场 → 1 帧硬切（见 below）
}
CANVAS = {
    "9:16": {720: (720, 1280), 1080: (1080, 1920), 2160: (2160, 3840)},
    "16:9": {720: (1280, 720), 1080: (1920, 1080), 2160: (3840, 2160)},
    "1:1": {720: (720, 720), 1080: (1080, 1080), 2160: (2160, 2160)},
}
RES_TAG = {720: "720P", 1080: "1080P", 2160: "4K"}
FONT_CANDIDATES = ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc"]


def _font() -> str | None:
    for f in FONT_CANDIDATES:
        if Path(f).exists():
            return f
    return None


_drawtext_cache: bool | None = None


def _has_drawtext() -> bool:
    """当前 ffmpeg 是否支持 drawtext（无 freetype 的构建会没有）——不支持则跳过字幕。"""
    global _drawtext_cache
    if _drawtext_cache is None:
        try:
            out = subprocess.run([settings.ffmpeg, "-hide_banner", "-filters"],
                                 capture_output=True, text=True, timeout=30).stdout
            _drawtext_cache = " drawtext " in out
        except Exception:
            _drawtext_cache = False
    return _drawtext_cache


def _clip_durations_ms(edl: EDL) -> list[int]:
    return [c.outMs - c.inMs for c in edl.clips]


def build_command(edl: EDL, assets: dict[int, dict], music_path: str | None,
                  height: int, fps: int, out_path: Path,
                  tts_tracks: list[tuple[Path, int, int, float]] | None = None) -> tuple[list[str], float]:
    """组装 ffmpeg 命令。返回 (cmd, 预计总时长秒)。tts_tracks: [(音频文件, startMs, endMs, 语速tempo)]。"""
    tts_tracks = tts_tracks or []
    aspect = edl.meta.aspect.value
    cw, ch = CANVAS[aspect][height]
    cmd = [settings.ffmpeg, "-y", "-v", "error", "-stats"]
    parts: list[str] = []
    one_frame = round(1000 / fps)

    # 输入：每个片段 -ss 精确入点；无音轨的素材在视频输入后追加一条静音输入，
    # 保证音频流 [k:a] 一定存在（视频流仍用原输入）。
    video_idx: list[int] = []   # 片段 i 的视频输入序号
    audio_idx: list[int] = []   # 片段 i 的音频输入序号
    idx = 0
    import json as _json
    for c in edl.clips:
        a = assets[c.assetId]
        dur_s = (c.outMs - c.inMs) / 1000
        cmd += ["-ss", f"{c.inMs / 1000:.3f}", "-t", f"{dur_s:.3f}", "-i", str(settings.assets_dir / a["file_path"])]
        video_idx.append(idx)
        # 探测素材是否含音轨（assets 表未存，直接 ffprobe，素材数少开销可忽略）
        try:
            probe_out = subprocess.run(
                [settings.ffprobe, "-v", "error", "-print_format", "json", "-show_streams",
                 "-select_streams", "a", str(settings.assets_dir / a["file_path"])],
                capture_output=True, text=True, timeout=30).stdout
            has_audio = bool(_json.loads(probe_out).get("streams"))
        except Exception:
            has_audio = True  # 探测失败按有音轨处理，交给 ffmpeg 兜底报错
        if not has_audio:
            cmd += ["-f", "lavfi", "-t", f"{dur_s:.3f}", "-i", "anullsrc=r=44100:cl=stereo"]
            audio_idx.append(idx + 1)
            idx += 2
        else:
            audio_idx.append(idx)
            idx += 1
    music_idx = idx
    if music_path:
        cmd += ["-i", music_path]
        idx += 1
    tts_base = idx
    for aiff, _, _, _tp in tts_tracks:
        cmd += ["-i", str(aiff)]
        idx += 1

    # 视频链
    n = len(edl.clips)
    trans = {t.afterClip: t for t in edl.transitions}
    durs = _clip_durations_ms(edl)
    total_ms = sum(durs) - sum(
        t.durMs for t in edl.transitions if t.type != TransitionType.none)

    for i, c in enumerate(edl.clips):
        is_none = trans.get(i + 1, Transition(afterClip=i + 1, type=TransitionType.none)).type == TransitionType.none
        chain = (
            f"[{video_idx[i]}:v]scale={cw}:{ch}:force_original_aspect_ratio=increase,"
            f"crop={cw}:{ch},fps={fps},format=yuv420p,setsar=1"
        )
        if i == 0 and c.fadeInMs:
            chain += f",fade=t=in:st=0:d={c.fadeInMs / 1000:.2f}"
        chain += f"[v{i}]"
        parts.append(chain)

    if n == 1:
        last = "[v0]"
    else:
        # xfade 链标准公式：第 i 个剪辑点偏移 = Σ(durs[0..i]) − Σ(tdurs[0..i])
        sum_dur = 0
        sum_tdur = 0
        for i in range(n - 1):
            t = trans.get(i + 1)
            ttype = t.type if t else TransitionType.dissolve
            tdur = one_frame if ttype == TransitionType.none else (t.durMs if t else 600)
            sum_dur += durs[i]
            sum_tdur += tdur
            offset_ms = sum_dur - sum_tdur
            tname = XFADE_OF_TYPE[ttype]
            src = f"[x{i}]" if i > 0 else "[v0]"
            parts.append(
                f"{src}[v{i + 1}]xfade=transition={tname}:duration={tdur / 1000:.3f}:"
                f"offset={offset_ms / 1000:.3f}[x{i + 1}]"
            )
        last = f"[x{n - 1}]"

    vout = "[vpre]"
    parts.append(f"{last}null[vpre]")  # 无论有无尾淡出，先把 xfade 链接出
    if edl.clips[-1].fadeOutMs:
        st = max((total_ms - edl.clips[-1].fadeOutMs) / 1000, 0)
        parts.append(f"[vpre]fade=t=out:st={st:.3f}:d={edl.clips[-1].fadeOutMs / 1000:.2f}[vf]")
        vout = "[vf]"

    # 字幕：片头标题 + 片尾署名（ffmpeg 无 drawtext 时自动跳过，不让渲染失败）
    font = _font() if _has_drawtext() else None
    cap_parts = []
    cap_inputs = 0
    for cap in edl.captions:
        if not cap.text or font is None:
            continue
        cap_file = out_path.with_suffix(f".cap{cap_inputs}.txt")
        cap_file.write_text(cap.text, encoding="utf-8")
        style = ("fontsize=72" if cap.style == "title" else "fontsize=44")
        y = f"(h-text_h)/10" if cap.style == "title" else "(h-text_h)*9/10"
        cap_parts.append(
            f"drawtext=fontfile={font}:textfile={cap_file}:{style}:fontcolor=white:"
            f"borderw=2:bordercolor=black@0.6:x=(w-text_w)/2:y={y}:"
            f"enable='between(t,{cap.startMs / 1000:.2f},{cap.endMs / 1000:.2f})'"
        )
        cap_inputs += 1
    if cap_parts:
        parts.append(f"{vout}" + ",".join(cap_parts) + "[vout]")
        vout = "[vout]"
    else:
        parts.append(f"{vout}null[vout]")
        vout = "[vout]"

    # 音频链：原声（concat）、BGM、字幕配音（TTS）按需混音
    total_s = total_ms / 1000
    labels: list[str] = []
    need_voice = not music_path or (edl.audio.keepOriginal and edl.audio.originalVolume > 0)
    if need_voice:
        if n > 1:
            parts.append(f"{''.join(f'[{audio_idx[i]}:a]' for i in range(n))}concat=n={n}:v=0:a=1[voice]")
            vsrc = "[voice]"
        else:
            vsrc = f"[{audio_idx[0]}:a]"
        parts.append(f"{vsrc}volume={edl.audio.originalVolume},atrim=end={total_s:.3f},asetpts=PTS-STARTPTS[voc]")
        labels.append("[voc]")

    if music_path:
        off = edl.audio.offsetMs / 1000
        m = f"[{music_idx}:a]atrim=start={off:.3f},asetpts=PTS-STARTPTS"
        if edl.audio.fadeInMs:
            m += f",afade=t=in:st=0:d={edl.audio.fadeInMs / 1000:.2f}"
        if edl.audio.fadeOutMs:
            m += f",afade=t=out:st={max(total_s - edl.audio.fadeOutMs / 1000, 0):.3f}:d={edl.audio.fadeOutMs / 1000:.2f}"
        # Ducking：每条配音窗口把配乐压到约四成半，0.2s 缓入 / 0.3s 缓出（音量包络串联）
        if getattr(edl.audio, "ducking", True) and tts_tracks:
            duck = max(round(edl.audio.volume * 0.45, 2), 0.12)
            for _a, t_start, t_end, _t in tts_tracks:
                s, e = max(t_start / 1000, 0), min(t_end / 1000, total_s)
                if e - s < 0.3:
                    continue
                pre = min(0.2, s)
                m += (f",volume=volume='if(lt(t,{s - pre:.2f}),1,"
                      f"if(lt(t,{s:.2f}),{duck}+(1-{duck})*(t-{s - pre:.2f})/{pre:.2f},"
                      f"if(lt(t,{e:.2f}),{duck},"
                      f"if(lt(t,{e + 0.3:.2f}),{duck}+(1-{duck})*(t-{e:.2f})/0.3,1))))':eval=frame")
        m += f",volume={edl.audio.volume},atrim=end={total_s:.3f},asetpts=PTS-STARTPTS[mus]"
        parts.append(m)
        labels.append("[mus]")

    for k, (_aiff, t_start, t_end, tempo) in enumerate(tts_tracks):
        ad_ms = max(int(t_start), 0)   # adelay 单位是毫秒，传秒会被当个位数 → 三条配音全叠在片头
        speed = f"atempo={tempo:.3f}," if tempo and tempo > 1.01 else ""
        parts.append(
            f"[{tts_base + k}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
            f"{speed}adelay={ad_ms}|{ad_ms},apad,atrim=end={min(t_end / 1000 + 0.2, total_s):.3f}[tts{k}]")
        labels.append(f"[tts{k}]")

    if len(labels) == 1:
        parts.append(f"{labels[0]}anull[aout]")
    else:
        parts.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=first:dropout_transition=0,"
                     f"volume={min(len(labels), 3)}[aout]")

    cmd += ["-filter_complex", ";".join(parts),
            "-map", "[vout]", "-map", "[aout]",
            "-r", str(fps), "-s", f"{cw}x{ch}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
            "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart",
            str(out_path)]
    return cmd, total_ms / 1000


def render_edl(project_id: int, edl: EDL, height: int, fps: int,
               progress_cb=None, register_proc=None) -> dict:
    """执行渲染并登记 exports v{n}。由 jobs 线程调用。"""
    if not edl.clips:
        raise RuntimeError("EDL 没有片段")
    assets = {a["id"]: a for a in db.query(
        f"SELECT * FROM assets WHERE id IN ({','.join('?' * len(edl.clips))})",
        tuple(c.assetId for c in edl.clips))}
    missing = [c.assetId for c in edl.clips if c.assetId not in assets]
    if missing:
        raise RuntimeError(f"片段引用的素材不存在: {missing}")

    music_path = None
    if edl.audio.musicId:
        row = db.query_one("SELECT file_path FROM music_library WHERE id=?", (edl.audio.musicId,))
        if row:
            music_path = str(settings.music_dir / row["file_path"])

    version = (db.query_one(
        "SELECT MAX(version) AS v FROM exports WHERE project_id=?", (project_id,))["v"] or 0) + 1
    file_key = f"export_p{project_id}_v{version}.mp4"
    out_path = settings.renders_dir / file_key

    # 字幕配音：开启后为每条字幕合成语音，渲染完删除临时文件
    tts_tracks: list[tuple[Path, int, int]] = []
    _n_sub = sum(1 for c in edl.captions if getattr(c, "style", "") == "subtitle" and c.text)
    if getattr(edl.audio, "ttsEnabled", False) and _n_sub:
        print(f"[配音] 合成 {_n_sub} 条字幕（音色 {getattr(edl.audio, 'ttsVoice', '') or '默认'}）", flush=True)
        from . import tts as tts_svc
        import json as _json
        subs = [c for c in edl.captions if c.style == "subtitle" and c.text]
        rate = float(getattr(edl.audio, "ttsRate", 1.0) or 1.0)
        kept = []
        for cap in subs:
            aiff = out_path.with_suffix(f".tts{len(kept)}.aiff")
            try:
                tts_svc.synth(aiff, cap.text, getattr(edl.audio, "ttsVoice", "") or None, rate)
            except Exception as e:
                raise RuntimeError(f"字幕配音合成失败: {e}")
            # 量实际时长：比字幕窗口长就加速朗读去贴合画面（上限 1.35x）
            window_s = max((cap.endMs - cap.startMs) / 1000, 0.5)
            try:
                probe = subprocess.run(
                    [settings.ffprobe, "-v", "error", "-show_entries", "format=duration",
                     "-of", "json", str(aiff)], capture_output=True, text=True, timeout=30).stdout
                audio_s = float(_json.loads(probe)["format"]["duration"])
            except Exception:
                audio_s = window_s
            tempo = 1.0
            if audio_s > window_s * 1.02:
                tempo = min(audio_s / window_s, 1.35)
                if audio_s / 1.35 > window_s + 0.3:
                    print(f"[配音] 跳过一条（窗口{window_s:.1f}s 太短，语音{audio_s:.1f}s 装不下）：{cap.text[:18]}", flush=True)
                    aiff.unlink(missing_ok=True)
                    continue
                print(f"[配音] 加速 {tempo:.2f}x 贴合画面（语音{audio_s:.1f}s / 窗口{window_s:.1f}s）", flush=True)
            tts_tracks.append((aiff, cap.startMs, cap.endMs, tempo))
            kept.append(cap)

    print(f"[渲染] 开始 项目{project_id} v{version} · {len(edl.clips)} 段 · "
          f"{RES_TAG[height]} · {'含配音' if tts_tracks else '无配音'}", flush=True)
    try:
        cmd, est_total = build_command(edl, assets, music_path, height, fps, out_path, tts_tracks)
        t0 = time.time()
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if register_proc:
            register_proc(proc)
        _, stderr = proc.communicate()
    finally:
        for p, _, _, _tp in tts_tracks:
            Path(p).unlink(missing_ok=True)
    elapsed_ms = int((time.time() - t0) * 1000)
    if proc.returncode != 0:
        raise RuntimeError(f"渲染失败: {(stderr or '')[-400:]}")

    size_kb = out_path.stat().st_size // 1024
    print(f"[渲染] 完成 {file_key} · {RES_TAG[height]}/{fps}fps · {size_kb}KB · 耗时 {elapsed_ms / 1000:.1f}s", flush=True)
    db.execute(
        """INSERT INTO exports (project_id, version, file_key, resolution, fps, size_bytes, elapsed_ms)
           VALUES (?,?,?,?,?,?,?)""",
        (project_id, version, file_key, RES_TAG[height], fps, out_path.stat().st_size, elapsed_ms),
    )
    db.execute("UPDATE projects SET status=1, updated_at=datetime('now','localtime') WHERE id=? AND status=0",
               (project_id,))
    if progress_cb:
        progress_cb(1.0)
    return {"version": version, "fileKey": file_key,
            "url": f"/media/renders/{file_key}", "elapsedMs": elapsed_ms,
            "resolution": RES_TAG[height], "fps": fps}
