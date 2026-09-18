#!/bin/bash
# 闪剪 AI 服务端一键启动（电脑端常驻）
cd "$(dirname "$0")"
if [ ! -x .venv/bin/uvicorn ]; then
  echo "首次运行：初始化虚拟环境…"
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
echo "闪剪 AI 服务端 → http://0.0.0.0:8600（本机 IP 见 系统设置-Wi-Fi-详细信息）"
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8600
