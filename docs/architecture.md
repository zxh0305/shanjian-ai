# 闪剪 AI · 分层架构说明

> 面向维护者的架构速览，与代码同步维护（2026-09-18 随智能体架构升级 P1–P3 + 模型网关更新）。
> 演进方案与阶段记录见 `plans/`（不入库）；目录规范见 `plans/2026-09-项目重组与开发方案.md`。

## 总体形态

局域网个人服务：Mac 常驻 FastAPI（`server/`），手机/电脑浏览器访问 H5（`web/`），
FFmpeg 负责重活（代理、渲染），大模型负责决策（分析/剪辑方案/文案/审查），
智能体层负责编排（剪辑总监固定流水线 + 审查迭代环）。

## 七层结构（server/app/）

```
routes(接口) → services(用例) → agents(编排) → tools(能力壳) → core(实现) → repositories(SQL) → db(连接/迁移)
                                       ↘ prompts(提示词资产，只被 agents 读)
层间只能向下依赖：tests/test_architecture.py 用 AST 强制，反向 import 即测试失败。
tools 只准包装 core（纯能力层，不碰库）；agents 不 import routes/services/db（副作用经 ctx 注入回调）。
```

| 层 | 位置 | 内容 |
|---|---|---|
| ① 前端 | `web/` | 单页 H5（index.html + app.css + app.js），hash 路由，BUILD 版本强刷 |
| ② 接口 | `routes/` | auth / upload / projects / timeline / pipeline / settings_api——只做校验→调 service→组装响应 |
| ③ 服务 | `services/` | jobs（任务框架+轮询）、music_match（配乐打分）、cut_flow（字幕/配音/文案业务） |
| ④ 智能体 | `agents/` | **base**（状态机主循环+卡死检测）、**toolcall**（react 选工具，暂未接入生产）、**runs**（AgentRun 事件持久化）、**director**（by_order 编排）、**editor_agent**（LLM 优先+硬校验+规则兜底）、**reviewer_agent**（抽帧+客观摘要→打分）；`prompts/` 每 agent 一个提示词模块 |
| ⑤ 工具 | `tools/` | BaseTool/ToolCollection/ToolResult 三件套 + media_tools（probe_media/transcribe_audio/synth_tts），输出 OpenAI function-calling schema；**`mcp/` 双领域 stdio server**（media-analysis 只读 / media-render 写），Claude 等外部宿主可直连 |
| ⑤′ 知识 | `skills/` | 流程性知识资产（SKILL.md：frontmatter 描述 + 正文），内置 narration-×4 / review-rubric / vlog-pacing；`data/skills/` 用户可覆盖新增、热加载；prompts/agents 只读不写 |
| ⑥ 实现 | `core/` | probe/proxy/render/asr/tts/media_analysis/autocut（纯函数实现）；**llm**（提示词组装与结果解析，不碰密钥）、**gateway**（模型网关）、**llm_config**（多模型注册表+按用户密钥） |
| ⑦ 数据 | `repositories/` + `db/` | 每表一文件（users/projects/assets/timelines/exports/analysis/usage）；db/ = connection + schema + 版本化迁移（基线钉死 0001/0002，新迁移对旧库真实执行） |

## 模型网关（core/gateway.py）

智能体/业务只喊任务名，不认识供应商与密钥：

```
chat("build_edl", …) / vision("review_cut", …, imgs)
   │ 路由链：环境变量 SHANJIAN_MODEL_<TASK> > 用户任务分配(taskModels) > 当前模型 > 备用模型
   │ 失败降级到链上下一个；429/超时等待重试；全败抛 GatewayError（不静默）
   └ 计量：tokens/耗时/成败 → llm_usage 表 → 设置页「本月用量」
四个任务：analyze_scenes(视觉) / build_edl(文本) / write_narration(文本) / review_cut(视觉)
```

配置按用户隔离（`llm_config_{uid}.json`）：模型+密钥+任务分配+备用模型，设置页三段式管理。

## 成片主流程（auto-cut，全程智能体驱动）

```
POST /projects/{id}/auto-cut
 ├─ EditorAgent 同步出首版 EDL（LLM→硬校验层→规则引擎兜底）→ 存快照 v{n}
 └─ DirectorAgent(by_order) 接管后台任务（AgentRun 驱动轮询进度）
     [edit] → [subs] Vlog字幕/配音(ASR 原话 或 LLM 文案, 文案自动开 TTS)
            → [render] FFmpeg（xfade 转场/字幕烧录/三轨混音/TTS atempo 贴合）
            → [review] ReviewerAgent 抽帧打分(<80 带意见回 edit 重剪, ≤3 轮)
     结论写 edl.meta.review → 预览页「AI 自检报告」卡
```

无 LLM 密钥时优雅降级：规则引擎剪辑、ASR 字幕、跳过审查。react 自主编排（ToolCallAgent）
已建成未接入，对应「工具化自主编排」演进项。

## MCP 对外暴露（tools/mcp/）

```
claude mcp add shanjian-media-analysis -- server/scripts/mcp_analysis.sh   # probe/抽帧/转写（只读）
claude mcp add shanjian-media-render  -- server/scripts/mcp_render.sh      # render_edl/TTS（写、长耗时）
```

一个领域一个 server、工具=原子操作、动词_宾语命名；实现全在 core/，MCP 壳零业务；
stdio 传输适合本地个人机（已用 JSON-RPC initialize/tools/list 实测握手）。

## 数据层

- SQLite 九表：projects / assets / analysis_reports / timelines / exports / music_library /
  users / auth_tokens / llm_usage（调用计量）；
- `data/` 四目录：assets（原片）/ proxies（代理缩略）/ renders（成片）/ music（曲库）；
- **EDL 是唯一数据源**：自动成片生成它 → 编辑器改它 → 渲染消费它；字段规格见 `docs/EDL-spec.md`；
- 密钥与模型配置不入库（`llm_config_{uid}.json`）。

## 已知约束

- `/media/*` 静态流无鉴权（局域网信任模型）——对外暴露前必须补签名 URL；
- 上传无断点续传（局域网场景优先级低）；
- 审查环最多 3 轮、TTS 加速上限 1.35x、窗口过短自动跳过该条配音（防截断）；
- ducking：EDL `audio.ducking`（默认开），配音窗口把配乐压到约三成，0.2s/0.3s 缓入缓出；
- jobs 状态已落库（0004）：重启后轮询得到「服务重启，任务已中断」终态而非 404；
- 安卓端（`app-android/`）二期挂起：仓库不含签名密钥与 APK，
  构建需在 `local.properties` 配 `shanjian.storePassword/keyPassword`。
