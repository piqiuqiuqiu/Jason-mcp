"""
监控路由 - 提供运行状态和统计信息
"""
import time
import psutil
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from server.config import SERVER_NAME, SERVER_VERSION

router = APIRouter()
_start_time = time.time()
_call_stats = {}  # tool_name -> {"success": N, "failed": N}


def record_call(tool_name: str, status: str = "success"):
    if tool_name not in _call_stats:
        _call_stats[tool_name] = {"success": 0, "failed": 0}
    _call_stats[tool_name][status] += 1


@router.get("/monitor/json")
async def monitor_json():
    mem = psutil.virtual_memory()
    uptime = int(time.time() - _start_time)
    return {
        "server": SERVER_NAME,
        "version": SERVER_VERSION,
        "uptime_seconds": uptime,
        "uptime_human": f"{uptime // 3600}h {(uptime % 3600) // 60}m",
        "memory_used_mb": round(psutil.Process().memory_info().rss / 1024 / 1024, 1),
        "system_memory_percent": mem.percent,
        "call_stats": _call_stats,
    }


@router.get("/monitor", response_class=HTMLResponse)
async def monitor_page():
    data = await monitor_json()
    rows = ""
    for tool, stats in data.get("call_stats", {}).items():
        rows += f"<tr><td>{tool}</td><td>{stats['success']}</td><td>{stats['failed']}</td></tr>"

    return f"""<!DOCTYPE html>
<html><head><title>{SERVER_NAME} Monitor</title>
<style>bodyfont-family:system-ui;max-width:800px;margin:40px auto;padding:0 20px
tablewidth:100%;border-collapse:collapseth,tdpadding:8px 12px;border:1px solid #ddd;text-align:left
thbackground:#f5f5f5.statdisplay:inline-block;margin:10px 20px 10px 0;padding:12px 20px;background:#f8f8f8;border-radius:8px
.stat .valfont-size:24px;font-weight:bold;color:#333.stat .labelfont-size:12px;color:#666</style></head>
<body><h1>🖥️ {SERVER_NAME} v{data['version']}</h1>
<div><div class="stat"><div class="val">{data['uptime_human']}</div><div class="label">Uptime</div></div>
<div class="stat"><div class="val">{data['memory_used_mb']} MB</div><div class="label">Memory</div></div>
<div class="stat"><div class="val">{data['system_memory_percent']}%</div><div class="label">System Mem</div></div></div>
<h2>Tool Calls</h2><table><tr><th>Tool</th><th>Success</th><th>Failed</th></tr>{rows}</table>
</body></html>"""
