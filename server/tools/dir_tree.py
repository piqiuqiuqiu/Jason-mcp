"""
tool_dir_tree - 目录树可视化
"""
import json
import os
from pathlib import Path
from server.config import ALLOWED_WORKDIRS

TOOL_NAME = "tool_dir_tree"
TOOL_DESCRIPTION = "以树形结构展示目录内容。支持深度限制、文件过滤、大小显示。"
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "目标目录，默认 /app"},
        "max_depth": {"type": "integer", "description": "最大深度，默认 3"},
        "file_pattern": {"type": "string", "description": "文件 glob 过滤，如 *.py"},
        "dirs_only": {"type": "boolean", "description": "只显示目录"},
        "show_size": {"type": "boolean", "description": "显示文件大小"},
    },
    "required": []
}

EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".mypy_cache"}


def _build_tree(root: Path, prefix: str, depth: int, max_depth: int,
                file_pattern: str, dirs_only: bool, show_size: bool) -> list:
    if depth >= max_depth:
        return []
    lines = []
    try:
        entries = sorted(root.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return [f"{prefix}[Permission Denied]"]

    entries = [e for e in entries if e.name not in EXCLUDE_DIRS and not e.name.startswith(".")]
    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        if entry.is_dir():
            lines.append(f"{prefix}{connector}{entry.name}/")
            ext = "    " if is_last else "│   "
            lines.extend(_build_tree(entry, prefix + ext, depth + 1, max_depth, file_pattern, dirs_only, show_size))
        elif not dirs_only:
            if file_pattern and not entry.match(file_pattern):
                continue
            size_str = f" ({entry.stat().st_size:,} B)" if show_size else ""
            lines.append(f"{prefix}{connector}{entry.name}{size_str}")
    return lines


async def handle(arguments: dict) -> str:
    path = arguments.get("path", "/app")
    max_depth = arguments.get("max_depth", 3)
    file_pattern = arguments.get("file_pattern", "")
    dirs_only = arguments.get("dirs_only", False)
    show_size = arguments.get("show_size", False)

    root = Path(path)
    if not root.exists():
        return json.dumps({"status": "FAILED", "error": f"Path not found: {path}"}, ensure_ascii=False)

    lines = [f"{root.name}/"]
    lines.extend(_build_tree(root, "", 0, max_depth, file_pattern, dirs_only, show_size))
    tree = "\n".join(lines)
    return json.dumps({"status": "SUCCESS", "tree": tree}, ensure_ascii=False)
