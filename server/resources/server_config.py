"""
服务器配置资源：环境变量、网络配置、磁盘用量
"""
import json
import os
import psutil
from server.config import SERVER_NAME, SERVER_VERSION, BASE_DIR

RESOURCES = [
    {"uri": "server://info", "name": "服务器信息", "description": "MCP V0.2 服务器运行信息"},
    {"uri": "server://disk", "name": "磁盘用量", "description": "各挂载点磁盘使用情况"},
    {"uri": "server://network", "name": "网络接口", "description": "网络接口与 IP 地址"},
]

# 敏感变量关键词
_SENSITIVE = ["token", "secret", "password", "key", "auth"]

def _mask(k, v):
    if any(s in k.lower() for s in _SENSITIVE):
        return v[:4] + "***" if len(v) > 4 else "***"
    return v


async def read(uri: str) -> str:
    if uri == "server://info":
        import time
        boot = psutil.boot_time()
        uptime = int(time.time() - boot)
        mem = psutil.virtual_memory()
        return json.dumps({
            "name": SERVER_NAME, "version": SERVER_VERSION,
            "uptime_hours": round(uptime / 3600, 1),
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(mem.total / 1024**3, 2),
            "memory_used_percent": mem.percent,
            "base_dir": str(BASE_DIR),
        }, ensure_ascii=False, indent=2)

    elif uri == "server://disk":
        partitions = psutil.disk_partitions()
        disks = []
        for p in partitions:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                disks.append({
                    "mount": p.mountpoint, "device": p.device, "fstype": p.fstype,
                    "total_gb": round(usage.total / 1024**3, 2),
                    "used_gb": round(usage.used / 1024**3, 2),
                    "percent": usage.percent,
                })
            except:
                pass
        return json.dumps(disks, ensure_ascii=False, indent=2)

    elif uri == "server://network":
        addrs = psutil.net_if_addrs()
        result = {}
        for iface, addr_list in addrs.items():
            result[iface] = [{"family": str(a.family), "address": a.address, "netmask": a.netmask} for a in addr_list]
        return json.dumps(result, ensure_ascii=False, indent=2)

    raise ValueError(f"Unknown server resource: {uri}")
