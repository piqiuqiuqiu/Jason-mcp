#!/bin/bash
# JasonMCP Container Entrypoint
echo "🚀 [JasonMCP] Starting..."

# 启动 MCP Server
exec python run.py
