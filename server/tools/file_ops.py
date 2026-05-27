"""
tool_file_read / tool_file_write - 容器内文件读写
支持全量写入和 patch 模式精确替换
"""
import json
import os
from pathlib import Path
from server.config import ALLOWED_WORKDIRS

# ── file_read ────────────────────────────────────────

FILE_READ_NAME = "tool_file_read"
FILE_READ_DESCRIPTION = "读取容器内文件的完整文本内容。路径限制 /app/ 下，单次最大 1MB。"
FILE_READ_SCHEMA = {
    "type": "object",
    "properties": {
        "file_path": {"type": "string", "description": "文件绝对路径"},
        "encoding": {"type": "string", "description": "编码，默认 utf-8"}
    },
    "required": ["file_path"]
}

# ── file_write ───────────────────────────────────────

FILE_WRITE_NAME = "tool_file_write"
FILE_WRITE_DESCRIPTION = "创建或修改容器内文件。mode=write 全量写入；mode=patch 精确查找替换。"
FILE_WRITE_SCHEMA = {
    "type": "object",
    "properties": {
        "file_path": {"type": "string", "description": "文件绝对路径"},
        "mode": {"type": "string", "enum": ["write", "patch"], "description": "write=覆盖, patch=替换"},
        "content": {"type": "string", "description": "write 模式的完整内容"},
        "old_text": {"type": "string", "description": "patch 模式的原文"},
        "new_text": {"type": "string", "description": "patch 模式的替换文本"}
    },
    "required": ["file_path"]
}


def _check_path(file_path: str) -> str | None:
    abs_path = os.path.abspath(file_path)
    if not any(abs_path.startswith(os.path.abspath(a)) for a in ALLOWED_WORKDIRS):
        return json.dumps({"status": "FAILED", "error": f"Path {file_path} is not allowed"}, ensure_ascii=False)
    return None


async def file_read(arguments: dict) -> str:
    file_path = arguments["file_path"]
    encoding = arguments.get("encoding", "utf-8")

    err = _check_path(file_path)
    if err:
        return err

    try:
        size = os.path.getsize(file_path)
        if size > 1_048_576:
            return json.dumps({"status": "FAILED", "error": f"File too large: {size} bytes (max 1MB)"}, ensure_ascii=False)

        with open(file_path, "r", encoding=encoding) as f:
            content = f.read()
        return json.dumps({"status": "SUCCESS", "content": content, "size": size}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "FAILED", "error": str(e)}, ensure_ascii=False)


async def file_write(arguments: dict) -> str:
    file_path = arguments["file_path"]
    mode = arguments.get("mode", "write")

    err = _check_path(file_path)
    if err:
        return err

    try:
        if mode == "write":
            content = arguments.get("content", "")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return json.dumps({"status": "SUCCESS", "message": f"Written {len(content)} chars to {file_path}"}, ensure_ascii=False)

        elif mode == "patch":
            old_text = arguments.get("old_text", "")
            new_text = arguments.get("new_text", "")
            if not old_text:
                return json.dumps({"status": "FAILED", "error": "patch mode requires old_text"}, ensure_ascii=False)

            with open(file_path, "r", encoding="utf-8") as f:
                original = f.read()

            count = original.count(old_text)
            if count == 0:
                return json.dumps({"status": "FAILED", "error": "old_text not found in file"}, ensure_ascii=False)

            patched = original.replace(old_text, new_text)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(patched)
            return json.dumps({"status": "SUCCESS", "message": f"Replaced {count} occurrence(s)"}, ensure_ascii=False)

        else:
            return json.dumps({"status": "FAILED", "error": f"Unknown mode: {mode}"}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "FAILED", "error": str(e)}, ensure_ascii=False)
