# 闪剪 AI · 安卓个人版

把相册里的碎片视频交给 AI：自动分析场景与节奏、匹配本机音乐、生成竖屏成片，支持轻编辑与导出。
另支持：多账号登录（数据互相隔离）、Vlog 口播模式（faster-whisper 本地识别语音并自动烧录字幕，编辑器可改/可加字幕）。
**个人自用，不上线。** 架构为「路线 B」：手机 App 当客户端，这台电脑当后端。

- 定稿计划：`../闪剪AI-安卓个人版-开发计划定稿.md`（12 周排期，第 7 周末可用线）
- EDL 字段规格：`docs/EDL-spec.md`（全局唯一数据源）

## 目录结构

```
shanjian-ai/
├── web/                # ★ 前端层：手机 H5 单页应用（index.html + app.css + app.js）
├── docs/               # 规格与架构文档（EDL-spec / architecture）；plans/ 为开发方案（git 忽略）
├── server/             # ★ 服务层（FastAPI）
│   ├── app/
│   │   ├── main.py     # 入口：路由挂载 + web/ 托管 + /media 静态流
│   │   ├── config.py   # 路径/限制/ffmpeg 路径
│   │   ├── db.py       # SQLite 八表 + 迁移
│   │   ├── routes/     # 接口层：auth / upload / projects / timeline / pipeline / settings
│   │   ├── schemas/    # EDL pydantic 模型（全局唯一数据源契约）
│   │   └── services/   # 服务层：媒体(probe/proxy) 智能(qwen_vl/asr/tts) 剪辑(autocut/renderer) 支撑(jobs/db/music)
│   ├── data/           # 运行时数据（git 忽略）
│   ├── scripts/ tests/ # e2e 自测 / 冒烟测试
│   └── requirements.txt · start.sh
└── app-android/        # 手机原生端（二期占位）
```

分层与数据流详见 `docs/architecture.md`；目录规范与开发路线见 `docs/plans/`；
**部署方式与数据存储（macOS 常驻 / Docker、数据目录重定向、对外隔离）见 `docs/deployment.md`**。
`git init` 后 `.gitignore` 已就绪（venv/运行数据/构建产物/plans 方案均忽略）。

## 快速开始（server）

```bash
# 0) 依赖 ffmpeg（核心依赖）
brew install ffmpeg

# 1) 虚拟环境
cd server
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2) 启动（默认 0.0.0.0:8600，手机与电脑同一 Wi-Fi 即可访问）
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8600

# 3) 验证
curl http://localhost:8600/health
open http://localhost:8600/docs        # Swagger

多用户：浏览器打开 `http://电脑IP:8600` 先注册账号再使用；第一个注册的账号自动认领升级前的历史项目，
各账号的素材/项目/成片完全隔离，音乐库共享、AI 模型配置与密钥也按账号独立。Vlog 口播模式首次使用会下载语音模型
（默认 small ≈240MB，可用环境变量 `SHANJIAN_ASR_MODEL=base` 换更小的）。
```

数据全部落在 `server/data/`（SQLite 库 + assets/proxies/renders/music 四目录）。
可用环境变量覆盖：`SHANJIAN_DATA_DIR`、`FFMPEG_BIN`、`FFPROBE_BIN`。

## 运行测试

```bash
cd server && .venv/bin/pytest tests/ -v
```

## 当前进度（对照定稿排期）

| 排期 | 状态 |
|---|---|
| W1–W2 服务端骨架：FastAPI + 上传 + ffprobe + 720p 代理 + EDL schema + SQLite 六表 | ✅ |
| W3–W5 AI 分析 / 音乐库匹配 / 自动剪辑规则引擎（ffmpeg 统计 + numpy 轻量实现） | ✅ MVP 版 |
| W6–W7 FFmpeg 渲染（xfade 四种转场 / 淡入淡出 / 三档画幅分辨率 / v{n} 不覆盖） | ✅ |
| W8–W10 Android App（Compose 三页：导入 / 分析 / 预览导出） | ✅ APK 已出 |
| W9–W10 端侧兜底导出（Media3 Transformer）、轻编辑器、mDNS | ⬜ 二期 |
| 多用户登录隔离 + Vlog 口播自动字幕（faster-whisper 本地 ASR + drawtext 烧录） | ✅ |
| 端到端验证：`server/.venv/bin/python scripts/e2e.py`（合成素材跑通全链路） | ✅ 通过 |

## 安装 App（手机）

1. 电脑执行 `server/start.sh` 启动服务端；把音乐文件放进 `server/data/music/`。
2. 把 `闪剪AI-debug.apk` 传到手机安装（AirDrop / 微信传文件都行）。
3. 打开 App，首页填电脑的局域网地址（如 `http://192.168.1.5:8600`）→ 点「连接」。
4. 相册选几段视频 → AI 分析 → 挑配乐 → 开始智能成片 → 预览/存相册/分享。

注意：系统可能提示「未知来源应用」，允许安装即可（debug 签名，仅自用）。
