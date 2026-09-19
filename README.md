# 闪剪 AI · 个人版

把相册里的碎片视频交给 AI：自动分析场景与节奏、匹配本机音乐、生成竖屏成片，支持轻编辑与导出。
另支持：多账号登录（数据互相隔离）、Vlog 口播模式（faster-whisper 本地识别语音并自动烧录字幕，编辑器可改/可加字幕）、
AI 自检审查环（渲染→审片打分→按意见自动重剪，≤3 轮）。
**个人自用，不上线。** 局域网架构：手机/电脑浏览器当客户端，这台 Mac 当服务端；
成片流程由智能体驱动（剪辑总监编排 → 剪辑师/审片官协作），大模型调用经进程内网关统一路由与计量。

- 分层架构与数据流：`docs/architecture.md`
- EDL 字段规格（全局唯一数据源契约）：`docs/EDL-spec.md`
- 部署与数据存储：`docs/deployment.md`
- 开发方案/排期：`docs/plans/`（本地维护，git 忽略，不入库）

## 目录结构

```
shanjian-ai/
├── web/                # ★ 前端层：手机 H5 单页应用（index.html + app.css + app.js）
├── docs/               # 规格与架构文档（EDL-spec / architecture / deployment）；plans/ 为开发方案（git 忽略）
├── server/             # ★ 服务层（FastAPI）
│   ├── app/
│   │   ├── main.py     # 入口：路由挂载 + web/ 托管 + /media 静态流
│   │   ├── config.py   # 路径/限制/ffmpeg 路径
│   │   ├── routes/     # ② 接口层：auth / upload / projects / timeline / pipeline / settings_api
│   │   ├── services/   # ③ 服务层：jobs(任务) / music_match / cut_flow(字幕配音文案)
│   │   ├── agents/     # ④ 智能体层：base(状态机) director(编排) editor/reviewer + runs/ + prompts/
│   │   ├── skills/     # 知识资产层：SKILL.md 风格/评分表/节奏规范（data/skills/ 可覆盖、热加载）
│   │   ├── tools/      # ⑤ 工具层：BaseTool 三件套 + media_tools + mcp/(Claude 等宿主直连)
│   │   ├── core/       # ⑥ 实现层：probe/proxy/render/asr/tts/autocut + llm + gateway(模型网关) + llm_config
│   │   ├── repositories/ + db/  # ⑦ 每表一文件 SQL / 连接+schema+版本化迁移
│   │   └── schemas/    # EDL pydantic 模型（全局唯一数据源契约）
│   ├── data/           # 运行时数据（git 忽略）
│   ├── scripts/ tests/ # e2e 自测 / 单测与架构契约（33 例）
│   └── requirements.txt · start.sh
└── app-android/        # 手机原生端（二期挂起；签名密钥不入库）
```

层间依赖单向向下（`routes → services → agents → tools → core → repositories → db`），
由 `tests/test_architecture.py` 强制，反向 import 直接测试失败。

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
# 或一键：./start.sh

# 3) 验证
curl http://localhost:8600/health
open http://localhost:8600/docs        # Swagger
```

多用户：浏览器打开 `http://电脑IP:8600` 先注册账号再使用；各账号的素材/项目/成片/模型配置完全隔离，
音乐库共享；第一个注册的账号自动认领升级前的历史项目。Vlog 口播模式首次使用会下载语音模型
（默认 base，可用环境变量 `SHANJIAN_ASR_MODEL` 调整）。

数据全部落在 `server/data/`（SQLite 库 + assets/proxies/renders/music 四目录）。
可用环境变量覆盖：`SHANJIAN_DATA_DIR`、`FFMPEG_BIN`、`FFPROBE_BIN`。

## 运行测试

```bash
cd server && .venv/bin/pytest tests/ -v    # 33 例：冒烟/工具/智能体/网关/迁移/Skill/MCP/架构契约
```

## MCP 接入（Claude 等外部宿主直连本机剪辑能力）

```bash
claude mcp add shanjian-media-analysis -- /绝对路径/server/scripts/mcp_analysis.sh  # 探针/抽帧/语音转写（只读）
claude mcp add shanjian-media-render  -- /绝对路径/server/scripts/mcp_render.sh    # EDL 渲染/TTS（写、长耗时）
```

## 当前进度

**定稿排期（12 周）——功能全部上线并端到端验证：**

| 排期 | 状态 |
|---|---|
| W1–W2 服务端骨架：FastAPI + 上传 + ffprobe + 720p 代理 + EDL schema | ✅ |
| W3–W5 AI 分析 / 音乐库匹配 / 自动剪辑规则引擎 | ✅ |
| W6–W7 FFmpeg 渲染（xfade 四种转场 / 淡入淡出 / 三档画幅 / v{n} 不覆盖） | ✅ |
| W8–W10 Android App（Compose 三页） | ✅ 已出包，现挂起二期 |
| W9–W10 端侧兜底导出（Media3）、轻编辑器、mDNS | ⬜ 二期 |
| 多用户登录隔离 + Vlog 口播自动字幕（本地 ASR + 烧录） | ✅ |
| 端到端验证：`server/.venv/bin/python scripts/e2e.py` | ✅ 通过 |

**智能体架构升级（2026-09）：**

| 阶段 | 状态 |
|---|---|
| P1 数据层分家（db/ + repositories/） | ✅ |
| P2 工具层（core/ 纯实现 + tools/ 三件套） | ✅ |
| P3 智能体层（BaseAgent/Director/Editor/Reviewer + prompts 资产） | ✅ |
| 模型网关（任务路由/降级/计量 + 设置页任务分配与用量） | ✅ |
| P4 MCP stdio server（双领域）+ Skill 层（风格/评分/节奏资产化） | ✅ |
| P0 加固：jobs 状态落库（重启不丢任务） | ✅ |
| P1 体验：配乐 ducking（配音自动压低 BGM）/ 字幕时间轴拖拽 / 相册直存 | ✅ |
| 拟人化配音：TTS 双引擎（微软神经音色 edge-tts，离线 say 兜底）+ 文案口语化底线 | ✅ |
| 大文件上传断点续传 | ⬜ 局域网优先级低 |
| P5 前端 features 化（web/js/features/ 按域拆分） | ⬜ 渐进 |

## 安装 App（手机）

安卓 App 二期挂起，仓库不再附带安装包（签名密钥与 APK 均不入库）。现阶段直接用手机浏览器
访问服务端即可（就是本项目的 Web 界面）。二期恢复构建时：在 `app-android/local.properties`
配置 `shanjian.storePassword / shanjian.keyPassword` 后执行 `./gradlew assembleRelease`。
