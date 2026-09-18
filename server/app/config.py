"""全局配置：路径、限制、ffmpeg/ffprobe 可执行文件。

数据全部落在 server/data/ 下，一张 SQLite 库 + 四个文件目录，
对应定稿计划 §1「电脑服务层/数据层」。
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # server/
DATA_DIR = Path(os.environ.get("SHANJIAN_DATA_DIR", BASE_DIR / "data"))


def _default_bin(name: str) -> str:
    """优先用 ffmpeg-full（含 drawtext 等完整滤镜），缺省回退 PATH 上的 ffmpeg。"""
    full = Path("/opt/homebrew/opt/ffmpeg-full/bin") / name
    if full.exists():
        return str(full)
    return shutil.which(name) or name


@dataclass
class Settings:
    host: str = "0.0.0.0"
    port: int = 8600

    db_path: Path = DATA_DIR / "shanjian.db"
    assets_dir: Path = DATA_DIR / "assets"      # 原片
    proxies_dir: Path = DATA_DIR / "proxies"    # 720p 代理 + 缩略图
    renders_dir: Path = DATA_DIR / "renders"    # 成片导出
    music_dir: Path = DATA_DIR / "music"        # 自备音乐库扫描根

    # 非功能口径（定稿 §2）：单段 ≤10min/2GB，单项目 ≤20 段
    max_clip_seconds: int = 600
    max_clip_bytes: int = 2 * 1024**3
    max_assets_per_project: int = 20

    proxy_height: int = 720  # 代理文件目标高度

    ffmpeg: str = field(default_factory=lambda: os.environ.get("FFMPEG_BIN") or _default_bin("ffmpeg"))
    ffprobe: str = field(default_factory=lambda: os.environ.get("FFPROBE_BIN") or _default_bin("ffprobe"))


settings = Settings()

for d in (DATA_DIR, settings.assets_dir, settings.proxies_dir, settings.renders_dir, settings.music_dir):
    d.mkdir(parents=True, exist_ok=True)


def require_ffmpeg() -> None:
    """启动与关键操作前检查 ffmpeg 可用，缺失时给出可执行的提示。"""
    missing = [name for name in (settings.ffmpeg, settings.ffprobe) if shutil.which(name) is None]
    if missing:
        raise RuntimeError(
            f"未找到 {', '.join(missing)}，请先安装：brew install ffmpeg "
            f"（或用 FFMPEG_BIN/FFPROBE_BIN 指定路径）"
        )
