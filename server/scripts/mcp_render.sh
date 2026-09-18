#!/bin/bash
# MCP stdio 启动器：媒体渲染（写、长耗时）。
cd "$(dirname "$0")/.."
exec .venv/bin/python -m app.tools.mcp.server_render
