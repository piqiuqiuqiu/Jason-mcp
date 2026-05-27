"""
tool_network_utils - 网络工具
支持 ping / curl / dns / port_check
"""
import subprocess
import json
import socket

TOOL_NAME = "tool_network_utils"
TOOL_DESCRIPTION = "网络工具集。action: ping|curl|dns|port_check"
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["ping", "curl", "dns", "port_check"]},
        "host": {"type": "string", "description": "目标主机"},
        "port": {"type": "integer", "description": "port_check 的端口号"},
        "url": {"type": "string", "description": "curl 的目标 URL"},
        "method": {"type": "string", "description": "HTTP 方法，默认 GET"},
        "timeout": {"type": "integer", "description": "超时秒数，默认 10"}
    },
    "required": ["action"]
}


async def handle(arguments: dict) -> str:
    action = arguments["action"]
    timeout = arguments.get("timeout", 10)
    try:
        if action == "ping":
            host = arguments.get("host", "")
            if not host:
                return json.dumps({"status": "FAILED", "error": "host required"}, ensure_ascii=False)
            proc = subprocess.run(["ping", "-c", "4", "-W", str(timeout), host],
                                  capture_output=True, text=True, timeout=timeout+5)
            return json.dumps({
                "status": "SUCCESS" if proc.returncode == 0 else "FAILED",
                "output": proc.stdout[-2000:]
            }, ensure_ascii=False)

        elif action == "curl":
            url = arguments.get("url", "")
            method = arguments.get("method", "GET")
            if not url:
                return json.dumps({"status": "FAILED", "error": "url required"}, ensure_ascii=False)
            proc = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w",
                 '{"http_code":%{http_code},"time_total":%{time_total},"size_download":%{size_download}}',
                 "-X", method, "--max-time", str(timeout), url],
                capture_output=True, text=True, timeout=timeout+5
            )
            return json.dumps({"status": "SUCCESS", "result": proc.stdout}, ensure_ascii=False)

        elif action == "dns":
            host = arguments.get("host", "")
            if not host:
                return json.dumps({"status": "FAILED", "error": "host required"}, ensure_ascii=False)
            addrs = socket.getaddrinfo(host, None)
            ips = list(set(addr[4][0] for addr in addrs))
            return json.dumps({"status": "SUCCESS", "host": host, "ips": ips}, ensure_ascii=False)

        elif action == "port_check":
            host = arguments.get("host", "localhost")
            port = arguments.get("port")
            if not port:
                return json.dumps({"status": "FAILED", "error": "port required"}, ensure_ascii=False)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return json.dumps({
                "status": "SUCCESS",
                "host": host, "port": port,
                "open": result == 0
            }, ensure_ascii=False)

        else:
            return json.dumps({"status": "FAILED", "error": f"Unknown action: {action}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "FAILED", "error": str(e)}, ensure_ascii=False)
