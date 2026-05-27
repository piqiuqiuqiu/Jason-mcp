#!/usr/bin/env python3
"""
JasonMCP 启动入口
"""
import sys
import uvicorn

if __name__ == "__main__":
    if "--stdio" in sys.argv:
        import asyncio
        from mcp.server.stdio import stdio_server
        from server.main import server

        async def run_stdio():
            async with stdio_server() as (read_stream, write_stream):
                await server.run(read_stream, write_stream, server.create_initialization_options())

        asyncio.run(run_stdio())
    else:
        from server.main import app
        uvicorn.run(app, host="0.0.0.0", port=8000)
