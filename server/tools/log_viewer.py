"""
tool_log_viewer - 日志查看器
支持 tail / search / list 操作
"""
import json
import os
import glob
from server.config import LOGS_DIR, BASE_DIR

TOOL_NAME = "tool_log_viewer"
TOOL_DESCRIPTION = "日志查看器。action: tail(查看末尾)|search(搜索关键词)|list(列出日志文件)"
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["tail", "search", "list"]},
        "file": {"type": "string", "description": "日志文件路径"},
        "lines": {"type": "integer", "description": "tail 行数，默认 50"},
        "keyword": {"type": "string", "description": "search 关键词"}
    },
    "required": ["action"]
}


async def handle(arguments: dict) -> str:
    action = arguments["action"]
    try:
        if action == "list":
            log_files = []
            for pattern in ["**/*.log", "**/*.txt"]:
                for f in glob.glob(str(LOGS_DIR / pattern), recursive=True):
                    stat = os.stat(f)
                    log_files.append({
                        "path": f,
                        "size_kb": round(stat.st_size / 1024, 1),
                        "modified": os.path.getmtime(f),
                    })
            log_files.sort(key=lambda x: x["modified"], reverse=True)
            return json.dumps({"status": "SUCCESS", "files": log_files[:20]}, ensure_ascii=False)

        elif action == "tail":
            file_path = arguments.get("file", "")
            lines = arguments.get("lines", 50)
            if not file_path or not os.path.exists(file_path):
                return json.dumps({"status": "FAILED", "error": f"File not found: {file_path}"}, ensure_ascii=False)
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            tail = all_lines[-lines:]
            return json.dumps({"status": "SUCCESS", "lines": len(tail), "content": "".join(tail)}, ensure_ascii=False)

        elif action == "search":
            file_path = arguments.get("file", "")
            keyword = arguments.get("keyword", "")
            if not file_path or not keyword:
                return json.dumps({"status": "FAILED", "error": "file and keyword required"}, ensure_ascii=False)
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                matches = [(i+1, line.strip()) for i, line in enumerate(f) if keyword.lower() in line.lower()]
            return json.dumps({"status": "SUCCESS", "count": len(matches), "matches": matches[:50]}, ensure_ascii=False)

        else:
            return json.dumps({"status": "FAILED", "error": f"Unknown action: {action}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "FAILED", "error": str(e)}, ensure_ascii=False)
