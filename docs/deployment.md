# 闪剪 AI · 部署与数据存储方案

> 2026-09-18 定稿。回答三个问题：怎么部署（Docker 还是裸机）、数据存哪、外部用户怎么隔离。

## 一、结论速览

| 问题 | 结论 |
|---|---|
| 部署方式 | **现阶段：macOS 裸机常驻**（launchd 自启）；**对外/自部署到 Linux：Docker**（有前置条件，见 §3） |
| 数据存哪 | 全部收敛在一个 **data/ 运行时目录**（默认项目内，`SHANJIAN_DATA_DIR` 可重定向到任意路径），**不随 git**；启动时自动创建 |
| 外部用户视频 | 也存宿主机 data/，按用户隔离（DB 行级已有 + 文件按用户子目录 + 磁盘配额，见 §4） |

## 二、数据目录设计（已实现，本节为约定）

```
data/                          # 运行时根目录（git 忽略；启动自动创建）
├── shanjian.db                # SQLite（users/projects/assets/timelines/exports…）
├── assets/                    # 上传原片（按用户隔离时为 assets/{uid}/…）
├── proxies/                   # 720p 代理 + 封面缩略图
├── renders/                   # 成片导出 v{n}
├── music/                     # 自备曲库（全机共享）
└── configs/                   # 每用户模型配置 llm_config_{uid}.json
```

- **自部署用户**：`SHANJIAN_DATA_DIR=/你的路径` 即可把全部数据放本地任意位置（外置盘、家目录），
  什么都不配就落在项目内 `server/data/`；
- **重定向即备份**：data/ 自包含（库+文件），`rsync -a data/ 备份盘/` 或时间机器整体覆盖；
- git 不带走任何用户数据（`.gitignore` 已含 `server/data/`）。

## 三、两种部署形态

### 形态 A：macOS 裸机常驻（当前形态，推荐默认）

适合：自己用 + 家人局域网/Tailscale 访问。**选它的硬理由：TTS 用系统 `say`
（19 个中文神经音色，离线免费），这能力只有 macOS 有**；whisper CPU int8 与 ffmpeg
在 Mac 上开箱即用。

启动方式二选一：

```bash
# 1) 手动：server/start.sh（现状）

# 2) 开机自启：launchd（推荐）
cat > ~/Library/LaunchAgents/com.shanjian.ai.plist <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.shanjian.ai</string>
  <key>WorkingDirectory</key><string>/path/to/shanjian-ai/server</string>
  <key>ProgramArguments</key><array>
    <string>/path/to/shanjian-ai/server/.venv/bin/uvicorn</string>
    <string>app.main:app</string><string>--host</string><string>0.0.0.0</string><string>--port</string><string>8600</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>EnvironmentVariables</key><dict>
    <key>SHANJIAN_DATA_DIR</key><string>/path/to/shanjian-data</string>
  </dict>
  <key>StandardOutPath</key><string>/tmp/shanjian.log</string>
  <key>StandardErrorPath</key><string>/tmp/shanjian.err</string>
</dict></plist>
EOF
launchctl load ~/Library/LaunchAgents/com.shanjian.ai.plist
```

访问：局域网 `http://Mac的IP:8600`；外部经 Tailscale 私网（现状推荐）或域名+反代（见 §5）。

### 形态 B：Docker（对外提供服务 / 自部署到 Linux 服务器）

**前置条件（必须先做，否则容器里没有配音）**：`tts.py` 抽象 TTS 后端——
`SHANJIAN_TTS_ENGINE=say|piper|edge-tts`。容器内用
**Piper**（离线中文神经音色，镜像内自带模型）或 **edge-tts**（微软免费在线，音质好但依赖网络）；
macOS 宿主继续用 say。这是上 Docker 唯一的代码改动。

```dockerfile
# server/Dockerfile（示意）
FROM python:3.12-slim
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt . && RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV SHANJIAN_DATA_DIR=/data  SHANJIAN_TTS_ENGINE=piper
VOLUME /data
EXPOSE 8600
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8600"]
```

```yaml
# docker-compose.yml（对外服务）
services:
  shanjian:
    build: ./server
    volumes: ["./shanjian-data:/data"]     # 用户数据全在宿主机这块，备份=拷这个目录
    ports: ["8600:8600"]
    restart: unless-stopped
    environment: ["SHANJIAN_TTS_ENGINE=piper"]
```

## 四、外部用户的隔离与配额

现状已具备：账号体系（注册/登录/令牌）、DB 行级隔离（他人项目 404）、
每用户模型配置。**对外服务前需补三件事**（按优先级）：

1. **`/media/*` 静态流鉴权**（当前无鉴权，知道 URL 就能拉文件）：
   改为带签名的临时 URL（HMAC + 过期时间），渲染/上传时生成、前端播放用短链；
2. **文件按用户分目录**：`assets/{uid}/`、`renders/{uid}/`（uploads/exports 落盘时带 uid 前缀），
   清理与统计按人一刀切；DB 已有归属，此项是运维便利性增强；
3. **每用户磁盘配额**：登录/上传前 `SUM(size)` 对比配额（如每用户 20GB，env 可调），
   超限拒绝上传并提示。

## 五、对外暴露路径

| 场景 | 方案 |
|---|---|
| 自己/家人 | Tailscale（现状）：零端口暴露，手机装客户端直连 |
| 朋友用你的服务 | 域名 + **Caddy** 反代（自动 HTTPS）+ 上面的鉴权/配额三件套 |
| 完全公开 | 不建议（ffmpeg/LLM 成本敞口）；至少加上传频率限制 |

## 六、环境变量总表

| 变量 | 默认 | 说明 |
|---|---|---|
| `SHANJIAN_DATA_DIR` | 项目内 `server/data` | 数据根目录（自动创建） |
| `FFMPEG_BIN` / `FFPROBE_BIN` | PATH/homebrew | 二进制路径 |
| `SHANJIAN_ASR_MODEL` | `base` | whisper 模型（small 更准更慢） |
| `SHANJIAN_TTS_ENGINE` | `say`（macOS） | 待实现：say / piper / edge-tts |
