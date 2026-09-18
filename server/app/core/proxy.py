"""代理生成：720p 低码率 mp4（预览/编辑用，4K 原片不参与手机端）+ 封面缩略图。

W1–W2 范围；跑在 asyncio.to_thread 里，不阻塞事件循环。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from ..config import settings


class ProxyError(RuntimeError):
    pass


def generate_proxy(src: Path, proxy_key: str, thumb_key: str) -> tuple[Path, Path]:
    """生成 720p 代理与首帧之后的封面帧。返回 (代理文件, 缩略图文件)。"""
    proxy_path = settings.proxies_dir / proxy_key
    thumb_path = settings.proxies_dir / thumb_key

    cmd_proxy = [
        settings.ffmpeg, "-y", "-v", "error",
        "-i", str(src),
        "-vf", f"scale=-2:{settings.proxy_height}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "27",
        "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart",
        str(proxy_path),
    ]
    cmd_thumb = [
        settings.ffmpeg, "-y", "-v", "error",
        "-ss", "1", "-i", str(src),          # 跳过首帧黑屏，取 1s 处
        "-frames:v", "1", "-vf", "scale=360:-2",
        str(thumb_path),
    ]
    for cmd, out in ((cmd_proxy, proxy_path), (cmd_thumb, thumb_path)):
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=True)
        except FileNotFoundError as e:
            raise ProxyError(f"找不到 {settings.ffmpeg}，请先安装 ffmpeg（brew install ffmpeg）") from e
        except subprocess.CalledProcessError as e:
            raise ProxyError(f"ffmpeg 失败: {e.stderr.strip()[:200]}") from e
    return proxy_path, thumb_path


def estimate_quality(width: int, height: int, duration_ms: int, size_bytes: int) -> float:
    """W1–W2 的简化画质分：分辨率档位 + 码率。

    >=0.8 前端显示「画质佳」。真实画质模型（清晰度/曝光/稳定性）在 W3–W4 随 AI 管线升级。
    """
    if duration_ms <= 0 or size_bytes <= 0:
        return 0.0
    pixels = width * height
    res_score = min(pixels / (1920 * 1080), 2.0)          # 1080P=1.0，4K=2.0（封顶）
    bitrate_kbps = size_bytes * 8 / (duration_ms / 1000) / 1000
    br_score = min(bitrate_kbps / 8000, 1.0)               # ≥8Mbps 视为满档
    return round(min(0.4 * res_score + 0.6 * br_score, 1.0), 3)
