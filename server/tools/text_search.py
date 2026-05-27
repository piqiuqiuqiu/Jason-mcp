"""
tool_text_search - 递归文件搜索（grep-like）
"""
import json, os, re
from pathlib import Path
from server.config import ALLOWED_WORKDIRS

TOOL_NAME = "tool_text_search"
TOOL_DESCRIPTION = "在目录中递归搜索文本或正则。支持文件类型过滤、上下文行。"
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "pattern": {"type": "string"},
        "path": {"type": "string"},
        "file_pattern": {"type": "string"},
        "is_regex": {"type": "boolean"},
        "ignore_case": {"type": "boolean"},
        "context_lines": {"type": "integer"},
        "max_results": {"type": "integer"}
    },
    "required": ["pattern"]
}
EXCLUDE = {".git", "__pycache__", "node_modules", ".venv"}

async def handle(arguments: dict) -> str:
    pattern = arguments["pattern"]
    root = arguments.get("path", "/app")
    file_pat = arguments.get("file_pattern", "")
    is_regex = arguments.get("is_regex", False)
    ignore_case = arguments.get("ignore_case", False)
    ctx = arguments.get("context_lines", 0)
    max_r = arguments.get("max_results", 50)
    flags = re.IGNORECASE if ignore_case else 0
    regex = re.compile(pattern if is_regex else re.escape(pattern), flags)
    results = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in EXCLUDE]
        for fn in fns:
            if file_pat and not Path(fn).match(file_pat):
                continue
            fp = os.path.join(dp, fn)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                for i, line in enumerate(lines):
                    if regex.search(line):
                        results.append({"file": fp, "line": i+1, "match": line.strip()[:200]})
                        if len(results) >= max_r:
                            return json.dumps({"status": "SUCCESS", "count": len(results), "truncated": True, "results": results}, ensure_ascii=False)
            except (OSError, UnicodeDecodeError):
                continue
    return json.dumps({"status": "SUCCESS", "count": len(results), "results": results}, ensure_ascii=False)
