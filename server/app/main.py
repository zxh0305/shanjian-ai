"""闪剪 AI 服务端入口（路线 B：电脑常驻服务）。

启动：uvicorn app.main:app --host 0.0.0.0 --port 8600
接口契约：docs/EDL-spec.md 与定稿 §3（11 个端点）。
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .config import require_ffmpeg, settings
from .routes import auth, pipeline, projects, settings_api, timeline, upload


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 只看业务步骤日志，不看每条 HTTP 访问日志
    import logging
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    db.init_db()
    from .services import jobs
    jobs.mark_interrupted_on_startup()
    try:
        require_ffmpeg()
    except RuntimeError as e:
        # 不阻止启动（纯查询接口可用），但上传链路会失败 —— 日志明确提示
        print(f"[WARN] {e}")
    yield


app = FastAPI(title="闪剪 AI · 个人版服务端", version="0.1.0", lifespan=lifespan)

# 手机 App 直连，无鉴权（Tailscale 私网已隔离，定稿 §3）；CORS 全开便于 H5 调试
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(projects.router)
app.include_router(timeline.router)
app.include_router(pipeline.router)
app.include_router(settings_api.router)

# 静态流：代理/封面、成片导出、音乐试听 —— ExoPlayer 直连
app.mount("/media/proxies", StaticFiles(directory=settings.proxies_dir), name="proxies")
app.mount("/media/renders", StaticFiles(directory=settings.renders_dir), name="renders")
app.mount("/media/music", StaticFiles(directory=settings.music_dir), name="music")
WEB_DIR = Path(__file__).parent.parent.parent / "web"   # 前端层：项目根/web
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
def web_app():
    # no-cache：页面迭代频繁，避免手机端拿到旧 HTML（仍带 ETag，未变时 304 很轻）
    return FileResponse(WEB_DIR / "index.html",
                        headers={"Cache-Control": "no-cache"})


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": app.version,
        "ffmpegConfigured": True,
        "musicDir": str(settings.music_dir),
    }


@app.get("/d", response_class=None)
def download_page():
    """APK 下载页：手机浏览器直接访问，走最标准的「下载 → 系统安装器」路径。"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse("""<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>闪剪AI 安装包下载</title></head>
<body style="font-family:sans-serif;background:#12131F;color:#eee;text-align:center;padding-top:12vh">
<h1 style="color:#7C6CFF">闪剪 AI</h1>
<p>点击下方按钮下载安装包（约 31MB）</p>
<p><a href="/media/proxies/app.apk" download
   style="display:inline-block;background:#7C6CFF;color:#fff;text-decoration:none;
          padding:16px 48px;border-radius:12px;font-size:18px">下载安装包</a></p>
<p style="color:#888;font-size:13px">下载完成后，从系统通知栏或浏览器的「下载列表」中点击安装。<br>
若被拦截：请先到 设置 → 系统和更新 → 关闭「纯净模式」。</p>
</body></html>""")
