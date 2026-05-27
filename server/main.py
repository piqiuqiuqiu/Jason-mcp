"""
JasonMCP - FastMCP 主实例
只包含本地操作相关的 Tools（12 个）
"""
import logging
import sys
import os
import signal
import json
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent, Resource, Prompt, PromptMessage, PromptArgument
from server.config import SERVER_NAME, SERVER_VERSION, DOWNLOADS_DIR
from server.routes.monitor import record_call

# Setup Logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(SERVER_NAME)

# ── 僵尸进程回收器 ──
if hasattr(signal, "SIGCHLD"):
    def _reap_zombies(signum=None, frame=None):
        while True:
            try:
                pid, _ = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    break
            except ChildProcessError:
                break
    signal.signal(signal.SIGCHLD, _reap_zombies)
    _reap_zombies()

# ── MCP Server 实例 ──
server = Server(SERVER_NAME)

# ── Tool 注册表（自动发现） ──
from server.tools import shell_exec, file_ops, git_ops, docker_ops
from server.tools import process_mgr, sys_info, env_mgr, log_viewer
from server.tools import cron_mgr, network_utils, dir_tree, text_search
from server.tools import notion_fetch, template_copy, docx_validate

TOOL_REGISTRY = {
    # DevOps 核心
    shell_exec.TOOL_NAME: {"schema": shell_exec.TOOL_SCHEMA, "desc": shell_exec.TOOL_DESCRIPTION, "handler": shell_exec.handle},
    file_ops.FILE_READ_NAME: {"schema": file_ops.FILE_READ_SCHEMA, "desc": file_ops.FILE_READ_DESCRIPTION, "handler": file_ops.file_read},
    file_ops.FILE_WRITE_NAME: {"schema": file_ops.FILE_WRITE_SCHEMA, "desc": file_ops.FILE_WRITE_DESCRIPTION, "handler": file_ops.file_write},
    git_ops.TOOL_NAME: {"schema": git_ops.TOOL_SCHEMA, "desc": git_ops.TOOL_DESCRIPTION, "handler": git_ops.handle},
    docker_ops.TOOL_NAME: {"schema": docker_ops.TOOL_SCHEMA, "desc": docker_ops.TOOL_DESCRIPTION, "handler": docker_ops.handle},
    # 系统管理
    process_mgr.TOOL_NAME: {"schema": process_mgr.TOOL_SCHEMA, "desc": process_mgr.TOOL_DESCRIPTION, "handler": process_mgr.handle},
    sys_info.TOOL_NAME: {"schema": sys_info.TOOL_SCHEMA, "desc": sys_info.TOOL_DESCRIPTION, "handler": sys_info.handle},
    env_mgr.TOOL_NAME: {"schema": env_mgr.TOOL_SCHEMA, "desc": env_mgr.TOOL_DESCRIPTION, "handler": env_mgr.handle},
    log_viewer.TOOL_NAME: {"schema": log_viewer.TOOL_SCHEMA, "desc": log_viewer.TOOL_DESCRIPTION, "handler": log_viewer.handle},
    # 运维工具
    cron_mgr.TOOL_NAME: {"schema": cron_mgr.TOOL_SCHEMA, "desc": cron_mgr.TOOL_DESCRIPTION, "handler": cron_mgr.handle},
    network_utils.TOOL_NAME: {"schema": network_utils.TOOL_SCHEMA, "desc": network_utils.TOOL_DESCRIPTION, "handler": network_utils.handle},
    dir_tree.TOOL_NAME: {"schema": dir_tree.TOOL_SCHEMA, "desc": dir_tree.TOOL_DESCRIPTION, "handler": dir_tree.handle},
    text_search.TOOL_NAME: {"schema": text_search.TOOL_SCHEMA, "desc": text_search.TOOL_DESCRIPTION, "handler": text_search.handle},
    # Notion2Word 导出
    notion_fetch.TOOL_NAME: {"schema": notion_fetch.TOOL_SCHEMA, "desc": notion_fetch.TOOL_DESCRIPTION, "handler": notion_fetch.handle},
    template_copy.TOOL_NAME: {"schema": template_copy.TOOL_SCHEMA, "desc": template_copy.TOOL_DESCRIPTION, "handler": template_copy.handle},
    docx_validate.TOOL_NAME: {"schema": docx_validate.TOOL_SCHEMA, "desc": docx_validate.TOOL_DESCRIPTION, "handler": docx_validate.handle},
}

logger.info(f"[{SERVER_NAME}] Registered {len(TOOL_REGISTRY)} tools")


# ── MCP Handlers ──

@server.list_tools()
async def handle_list_tools():
    tools = [
        Tool(name="tool_health_check",
             description=f"检查 {SERVER_NAME} 运行状态。返回版本和状态。",
             inputSchema={"type": "object", "properties": {}})
    ]
    for name, info in TOOL_REGISTRY.items():
        tools.append(Tool(name=name, description=info["desc"], inputSchema=info["schema"]))
    return tools


@server.list_resources()
async def handle_list_resources():
    from server.resources import docker_config, server_config
    resources = []
    for mod in [docker_config, server_config]:
        for r in mod.RESOURCES:
            resources.append(Resource(uri=r["uri"], name=r["name"], description=r["description"], mimeType="application/json"))
    return resources


@server.read_resource()
async def handle_read_resource(uri: str):
    uri_str = str(uri)
    from server.resources import docker_config, server_config
    if uri_str.startswith("docker://"):
        return await docker_config.read(uri_str)
    if uri_str.startswith("server://"):
        return await server_config.read(uri_str)
    raise ValueError(f"Unknown resource: {uri_str}")


@server.list_prompts()
async def handle_list_prompts():
    from server.prompts.devops import PROMPTS
    return [
        Prompt(
            name=p["name"], description=p["description"],
            arguments=[PromptArgument(name=a["name"], description=a["description"], required=a.get("required", False)) for a in p["arguments"]]
        ) for p in PROMPTS
    ]


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict = None):
    from server.prompts.devops import PROMPTS
    for p in PROMPTS:
        if p["name"] == name:
            args = arguments or {}
            # 填充默认值
            for a in p["arguments"]:
                if a["name"] not in args:
                    args[a["name"]] = f"<{a['name']}>"
            text = p["template"].format(**args)
            record_call(f"prompt:{name}")
            return PromptMessage(role="user", content=TextContent(type="text", text=text))
    raise ValueError(f"Prompt not found: {name}")


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    try:
        if name == "tool_health_check":
            record_call("tool_health_check")
            return [TextContent(type="text", text=f"Status: OK, Version: {SERVER_VERSION}")]

        if name in TOOL_REGISTRY:
            result = await TOOL_REGISTRY[name]["handler"](arguments)
            record_call(name)
            return [TextContent(type="text", text=result)]

        raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        record_call(name, "failed")
        raise e


# ── FastAPI App ──
app = FastAPI(title=SERVER_NAME, version=SERVER_VERSION, redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# MCP SSE 传输
sse = SseServerTransport("/mcp/messages")
# V02 专用 SSE 传输（使用 /mcp-v02/messages 路径）
sse_v02 = SseServerTransport("/mcp-v02/messages")


@app.api_route("/mcp", methods=["GET", "OPTIONS"])
@app.api_route("/mcp/", methods=["GET", "OPTIONS"])
async def handle_mcp_sse(request: Request):
    if request.method == "OPTIONS":
        return Response(status_code=204)
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
    return Response()


@app.api_route("/mcp/messages", methods=["POST", "OPTIONS"])
@app.api_route("/mcp/messages/", methods=["POST", "OPTIONS"])
async def handle_mcp_messages(request: Request):
    if request.method == "OPTIONS":
        return Response(status_code=204)
    await sse.handle_post_message(request.scope, request.receive, request._send)
    return Response()


# REST 路由
from server.routes.health import router as health_router
from server.routes.monitor import router as monitor_router
app.include_router(health_router)
app.include_router(monitor_router)

# ── MCP-V02 前缀路由（支持 Cloudflare Tunnel 路径） ──
# 这些路由与上面的路由相同，但添加了 /mcp-v02 前缀

@app.api_route("/mcp-v02", methods=["GET", "OPTIONS"])
@app.api_route("/mcp-v02/", methods=["GET", "OPTIONS"])
async def handle_mcp_v02_sse(request: Request):
    """MCP V02 SSE 端点 - 供 Cloudflare Tunnel 使用"""
    if request.method == "OPTIONS":
        return Response(status_code=204)
    async with sse_v02.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
    return Response()


@app.api_route("/mcp-v02/messages", methods=["POST", "OPTIONS"])
@app.api_route("/mcp-v02/messages/", methods=["POST", "OPTIONS"])
async def handle_mcp_v02_messages(request: Request):
    """MCP V02 消息端点"""
    if request.method == "OPTIONS":
        return Response(status_code=204)
    await sse_v02.handle_post_message(request.scope, request.receive, request._send)
    return Response()


@app.get("/mcp-v02/health")
async def health_v02():
    """健康检查 - V02 前缀"""
    return {"status": "ok", "name": SERVER_NAME, "version": SERVER_VERSION}


@app.get("/mcp-v02/tools")
async def list_tools_v02():
    """工具列表 - V02 前缀"""
    tools = await handle_list_tools()
    return [{"name": t.name, "description": t.description} for t in tools]


# 工具列表 REST 端点（调试用）
@app.get("/tools")
async def list_tools_rest():
    tools = await handle_list_tools()
    return [{"name": t.name, "description": t.description} for t in tools]


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
