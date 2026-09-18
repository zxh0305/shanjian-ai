# 闪剪 AI · 分层架构说明

> 面向维护者的架构速览。目录规范与开发路线见 `plans/2026-09-项目重组与开发方案.md`。

## 总体形态

局域网个人服务：Mac 常驻 FastAPI（`server/`），手机/电脑浏览器访问 H5（`web/`），
FFmpeg 负责重活（代理、渲染），大模型负责决策（分析/剪辑方案/文案/审查）。

## 前端层（web/）

- 单页应用，无框架。`index.html` 骨架 + `app.css` 样式 + `app.js` 逻辑；
- hash 路由：`#/`(首页) `#/project/{id}`(素材) `#/analyze/{id}`(分析与配乐)
  `#/preview/{id}[/{v}]` `#/editor/{id}`(暗色) `#/export/{id}/{v}` `#/works[/{pid}]`(作品文件夹)
  `#/me` `#/settings` `#/login`；
- 关键状态：`anState`（分析页）、`tlState`（编辑器）、`_cutSel`（素材勾选跨页共享）、
  `_backCtx`（返回上下文：从哪进回哪去）；
- 与服务端通过 REST + Bearer token；长任务（分析/渲染/审查/识别）用 `GET /renders/{jobId}` 轮询；
- 版本管理：`BUILD` 常量 + 资源引用 `?v=`，改版递增即可强刷缓存。

## 接口层（server/app/routes/）

| 文件 | 职责 |
|---|---|
| auth.py | 注册/登录/登出，`current_user`/`owned_project` 两道校验被其余路由复用 |
| upload.py | multipart 上传 → 落盘 → 后台解析+代理 |
| projects.py | 项目/素材/成片 CRUD（含单素材移除、单成片删除） |
| timeline.py | EDL 快照读写（PUT 存 v{n+1}，历史可回溯） |
| pipeline.py | 分析 / 配乐候选 / auto-cut（含 Vlog 字幕配音 + AI 审查环）/ 渲染 / 字幕文案 / TTS 音色 |
| settings_api.py | 模型配置（**按用户隔离**，`llm_config_{uid}.json`） |

## 服务层（server/app/services/）

- **core/（纯函数实现层）**：probe（ffprobe 解析）、proxy（720p 代理+封面）、render（FFmpeg 渲染）、asr（whisper）、tts（say）、media_analysis（本地信号）、autocut（规则引擎）——FastAPI 与未来 MCP 共用一套实现；
- **tools/（工具层）**：BaseTool/ToolCollection/ToolResult 三件套 + 首批工具（probe_media/transcribe_audio/synth_tts），薄壳包装 core/；
- **services/**：jobs（任务框架）、llm_config（按用户模型配置）、music_match（配乐打分）、qwen_vl（LLM 调用）；
- **智能**：qwen_vl（VL 场景分析 / EDL 生成 / 旁白文案 / 成片审查，统一 `_get_client(user_id)`）；
  asr（faster-whisper 本地识别，含幻觉过滤）；tts（macOS say，19 个中文音色，语速+自动加速贴合）；
  llm_config（多模型注册表+按用户密钥）；media_analysis（本地信号：场景切镜/情绪/BPM）；
- **剪辑**：autocut（无 LLM 时的规则引擎兜底）、renderer（FFmpeg 命令组装：xfade 转场链、
  drawtext 字幕烧录、三轨混音（原声/BGM/TTS）、TTS atempo 适配）；


## 数据层

- SQLite 八表：projects / assets / analysis_reports / timelines / exports / music_library / users / auth_tokens；
- 代码分层：`routes > services > tools > core > repositories > db`（tests/test_architecture.py 强制，反向依赖即测试失败）；
- `data/` 四目录：assets（原片）/ proxies（代理缩略）/ renders（成片）/ music（曲库）；
- **EDL 是唯一数据源**：自动成片生成它 → 编辑器改它 → 渲染消费它；字段规格见 `docs/EDL-spec.md`；
- 模型配置不入库（`llm_config_{uid}.json`，旧全局文件已自动迁移给首个账号）。

## AI 管线（auto-cut 内部）

```
LLM/规则引擎 出 EDL ──► Vlog: 字幕(ASR 原话 或 LLM 风格文案, 无语音时文案兜底)
                    ──► TTS 开关(仅文案旁白自动开; 原声 auto 档联动)
                    ──► 渲染(抽帧审查: 评分<80 → 意见回灌重剪, ≤3 轮)
                    ──► 结论写 edl.meta.review, 预览页出报告卡
```

无 LLM 密钥时全部优雅降级：规则引擎剪辑、ASR 字幕、跳过审查。

## 已知约束

- jobs 内存态：服务重启丢任务状态（前端会轮询到 404）；
- `/media/*` 静态流无鉴权（局域网信任模型）；
- 审查环最多 3 轮、TTS 加速上限 1.35x、窗口过短自动跳过该条配音。
