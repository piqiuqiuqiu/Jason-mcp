"""
tool_sys_info - 系统信息收集
提供 CPU、内存、磁盘、网络、系统概览
"""
import json
import platform
import psutil

TOOL_NAME = "tool_sys_info"
TOOL_DESCRIPTION = "收集系统信息。action: overview(系统概览)|cpu|memory|disk|network|uptime"
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["overview", "cpu", "memory", "disk", "network", "uptime"]}
    },
    "required": ["action"]
}


async def handle(arguments: dict) -> str:
    action = arguments["action"]
    try:
        if action == "overview":
            return json.dumps({
                "status": "SUCCESS",
                "system": platform.system(),
                "node": platform.node(),
                "release": platform.release(),
                "python": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(psutil.virtual_memory().total / 1024**3, 2),
                "disk_total_gb": round(psutil.disk_usage("/").total / 1024**3, 2),
            }, ensure_ascii=False)

        elif action == "cpu":
            return json.dumps({
                "status": "SUCCESS",
                "cpu_count_logical": psutil.cpu_count(),
                "cpu_count_physical": psutil.cpu_count(logical=False),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "cpu_freq_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else None,
                "load_avg": list(psutil.getloadavg()),
            }, ensure_ascii=False)

        elif action == "memory":
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            return json.dumps({
                "status": "SUCCESS",
                "total_gb": round(mem.total / 1024**3, 2),
                "available_gb": round(mem.available / 1024**3, 2),
                "used_gb": round(mem.used / 1024**3, 2),
                "percent": mem.percent,
                "swap_total_gb": round(swap.total / 1024**3, 2),
                "swap_used_gb": round(swap.used / 1024**3, 2),
            }, ensure_ascii=False)

        elif action == "disk":
            usage = psutil.disk_usage("/")
            return json.dumps({
                "status": "SUCCESS",
                "total_gb": round(usage.total / 1024**3, 2),
                "used_gb": round(usage.used / 1024**3, 2),
                "free_gb": round(usage.free / 1024**3, 2),
                "percent": usage.percent,
            }, ensure_ascii=False)

        elif action == "network":
            io = psutil.net_io_counters()
            return json.dumps({
                "status": "SUCCESS",
                "bytes_sent_mb": round(io.bytes_sent / 1024**2, 2),
                "bytes_recv_mb": round(io.bytes_recv / 1024**2, 2),
                "packets_sent": io.packets_sent,
                "packets_recv": io.packets_recv,
            }, ensure_ascii=False)

        elif action == "uptime":
            import time
            boot = psutil.boot_time()
            uptime_sec = time.time() - boot
            hours = int(uptime_sec // 3600)
            minutes = int((uptime_sec % 3600) // 60)
            return json.dumps({
                "status": "SUCCESS",
                "uptime": f"{hours}h {minutes}m",
                "boot_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(boot)),
            }, ensure_ascii=False)

        else:
            return json.dumps({"status": "FAILED", "error": f"Unknown action: {action}"}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "FAILED", "error": str(e)}, ensure_ascii=False)
