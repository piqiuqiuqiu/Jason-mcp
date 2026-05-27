"""
tool_process_mgr - 进程管理与系统诊断
"""
import json
import psutil

TOOL_NAME = "tool_process_mgr"
TOOL_DESCRIPTION = "进程管理与系统诊断。action: ps|top|kill|ports|connections"
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["ps", "top", "kill", "ports", "connections"]},
        "filter": {"type": "string"},
        "pid": {"type": "integer"},
        "sort_by": {"type": "string", "enum": ["cpu", "memory", "pid"]},
        "top_n": {"type": "integer"}
    },
    "required": ["action"]
}

async def handle(arguments: dict) -> str:
    action = arguments["action"]
    try:
        if action == "ps":
            keyword = arguments.get("filter", "")
            procs = []
            for p in psutil.process_iter(["pid", "name", "status", "memory_info"]):
                info = p.info
                if keyword and keyword.lower() not in (info["name"] or "").lower():
                    continue
                mem = info.get("memory_info")
                procs.append({"pid": info["pid"], "name": info["name"], "status": info["status"],
                              "mem_mb": round(mem.rss / 1024 / 1024, 1) if mem else 0})
            return json.dumps({"status": "SUCCESS", "count": len(procs), "processes": procs[:50]}, ensure_ascii=False)
        elif action == "top":
            sort_by = arguments.get("sort_by", "memory")
            top_n = arguments.get("top_n", 10)
            procs = []
            for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
                info = p.info
                mem = info.get("memory_info")
                procs.append({"pid": info["pid"], "name": info["name"], "cpu%": info.get("cpu_percent", 0),
                              "mem_mb": round(mem.rss / 1024 / 1024, 1) if mem else 0})
            key = "cpu%" if sort_by == "cpu" else "mem_mb" if sort_by == "memory" else "pid"
            procs.sort(key=lambda x: x[key], reverse=True)
            return json.dumps({"status": "SUCCESS", "top": procs[:top_n]}, ensure_ascii=False)
        elif action == "kill":
            pid = arguments.get("pid")
            if not pid:
                return json.dumps({"status": "FAILED", "error": "pid required"}, ensure_ascii=False)
            p = psutil.Process(pid)
            name = p.name()
            p.terminate()
            return json.dumps({"status": "SUCCESS", "message": f"Process {pid} ({name}) terminated"}, ensure_ascii=False)
        elif action == "ports":
            keyword = arguments.get("filter", "")
            conns = psutil.net_connections(kind="inet")
            listeners = [{"addr": f"{c.laddr.ip}:{c.laddr.port}", "pid": c.pid}
                         for c in conns if c.status == "LISTEN" and (not keyword or keyword in str(c.laddr.port))]
            return json.dumps({"status": "SUCCESS", "listeners": listeners}, ensure_ascii=False)
        elif action == "connections":
            conns = psutil.net_connections(kind="inet")
            result = [{"local": f"{c.laddr.ip}:{c.laddr.port}",
                        "remote": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "",
                        "status": c.status, "pid": c.pid} for c in conns[:50]]
            return json.dumps({"status": "SUCCESS", "count": len(conns), "connections": result}, ensure_ascii=False)
        else:
            return json.dumps({"status": "FAILED", "error": f"Unknown action: {action}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "FAILED", "error": str(e)}, ensure_ascii=False)
