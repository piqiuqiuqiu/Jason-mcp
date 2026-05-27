"""
tool_env_mgr - 环境变量管理
查看、搜索环境变量（修改 .env 需确认）
"""
import json
import os

TOOL_NAME = "tool_env_mgr"
TOOL_DESCRIPTION = "管理环境变量。action: list(列出)|get(获取)|search(搜索)|dotenv_read(读取.env文件)|dotenv_update(更新.env文件)"
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["list", "get", "search", "dotenv_read", "dotenv_update"]},
        "key": {"type": "string", "description": "环境变量名"},
        "filter": {"type": "string", "description": "搜索关键词"},
        "env_file": {"type": "string", "description": ".env 文件路径"},
        "updates": {"type": "string", "description": "JSON 对象字符串 {key: value}"}
    },
    "required": ["action"]
}

# 敏感变量关键词（值将被遮掩）
SENSITIVE_KEYS = ["token", "secret", "password", "key", "auth", "credential"]


def _mask(key: str, value: str) -> str:
    if any(s in key.lower() for s in SENSITIVE_KEYS):
        return value[:4] + "***" + value[-4:] if len(value) > 8 else "***"
    return value


async def handle(arguments: dict) -> str:
    action = arguments["action"]
    try:
        if action == "list":
            keyword = arguments.get("filter", "")
            env_vars = {}
            for k, v in sorted(os.environ.items()):
                if keyword and keyword.lower() not in k.lower():
                    continue
                env_vars[k] = _mask(k, v)
            return json.dumps({"status": "SUCCESS", "count": len(env_vars), "env": env_vars}, ensure_ascii=False)

        elif action == "get":
            key = arguments.get("key", "")
            value = os.environ.get(key)
            if value is None:
                return json.dumps({"status": "FAILED", "error": f"Variable {key} not found"}, ensure_ascii=False)
            return json.dumps({"status": "SUCCESS", "key": key, "value": _mask(key, value)}, ensure_ascii=False)

        elif action == "search":
            keyword = arguments.get("filter", "")
            matches = {k: _mask(k, v) for k, v in os.environ.items() if keyword.lower() in k.lower() or keyword.lower() in v.lower()}
            return json.dumps({"status": "SUCCESS", "count": len(matches), "matches": matches}, ensure_ascii=False)

        elif action == "dotenv_read":
            env_file = arguments.get("env_file", "/app/.env")
            if not os.path.exists(env_file):
                return json.dumps({"status": "FAILED", "error": f"File not found: {env_file}"}, ensure_ascii=False)
            with open(env_file, "r") as f:
                lines = f.readlines()
            entries = {}
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    entries[k.strip()] = _mask(k.strip(), v.strip())
            return json.dumps({"status": "SUCCESS", "file": env_file, "entries": entries}, ensure_ascii=False)

        elif action == "dotenv_update":
            return json.dumps({"status": "FAILED", "error": "dotenv_update 需要通过 file_write 工具修改 .env 文件，并请先向用户确认"}, ensure_ascii=False)

        else:
            return json.dumps({"status": "FAILED", "error": f"Unknown action: {action}"}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "FAILED", "error": str(e)}, ensure_ascii=False)
