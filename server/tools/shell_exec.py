"""
tool_shell_exec - 在容器内执行 Shell 命令
安全约束：命令黑名单 + 工作目录限制
"""
import subprocess
import json
import os
from server.config import SHELL_BLACKLIST, ALLOWED_WORKDIRS

TOOL_NAME = "tool_shell_exec"
TOOL_DESCRIPTION = "在 Docker 容器内执行 Shell 命令。返回 {stdout, stderr, exit_code}。默认工作目录 /app。超时：普通命令 30s，构建类 300s。安全约束：路径限制，禁止破坏性命令。"
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {"type": "string", "description": "Shell 命令字符串"},
        "cwd": {"type": "string", "description": "工作目录，默认 /app"},
        "timeout": {"type": "integer", "description": "超时秒数，默认 60"}
    },
    "required": ["command"]
}


async def handle(arguments: dict) -> str:
    command = arguments["command"]
    cwd = arguments.get("cwd")
    timeout = arguments.get("timeout", 60)

    # 1. 黑名单检查
    for forbidden in SHELL_BLACKLIST:
        if forbidden in command:
            return json.dumps({
                "status": "FAILED",
                "error": f"Command contains forbidden string: {forbidden}"
            }, ensure_ascii=False)

    # 2. 工作目录校验
    if cwd:
        abs_cwd = os.path.abspath(cwd)
        if not any(abs_cwd.startswith(os.path.abspath(a)) for a in ALLOWED_WORKDIRS):
            return json.dumps({
                "status": "FAILED",
                "error": f"CWD {cwd} is not in ALLOWED_WORKDIRS"
            }, ensure_ascii=False)
    else:
        cwd = ALLOWED_WORKDIRS[0]

    # 3. 执行
    try:
        process = subprocess.Popen(
            command, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=cwd
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return json.dumps({
                "status": "SUCCESS" if process.returncode == 0 else "FAILED",
                "exit_code": process.returncode,
                "stdout": stdout[-5000:] if len(stdout) > 5000 else stdout,
                "stderr": stderr[-2000:] if len(stderr) > 2000 else stderr,
            }, ensure_ascii=False)
        except subprocess.TimeoutExpired:
            process.kill()
            return json.dumps({"status": "FAILED", "error": f"Command timed out after {timeout}s"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "FAILED", "error": str(e)}, ensure_ascii=False)
