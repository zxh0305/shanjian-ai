#!/bin/bash
# MCP stdio 启动器：媒体分析（只读）。宿主直接指向本脚本即可，无需关心 cwd/PYTHONPATH。
cd "$(dirname "$0")/.."
exec .venv/bin/python -m app.tools.mcp.server_analysis
