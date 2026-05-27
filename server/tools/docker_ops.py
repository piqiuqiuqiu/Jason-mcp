"""
tool_docker_ops - Docker Compose 操作
支持 ps / logs / up / down / restart / build / inspect
"""
import subprocess
import json
import os
from server.config import ALLOWED_WORKDIRS, DEFAULT_COMPOSE_PATH

TOOL_NAME = "tool_docker_ops"
TOOL_DESCRIPTION = "管理 Docker Compose 服务。op: ps|logs|up|down|restart|build|inspect。⚠️ 重启容器会中断连接 10-15s。"
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "op": {"type": "string", "enum": ["up", "down", "restart", "ps", "logs", "build", "inspect"]},
        "compose_path": {"type": "string", "description": "docker-compose 文件路径"},
        "service": {"type": "string", "description": "指定服务名"},
        "tail": {"type": "integer", "description": "logs 时的行数，默认 100"}
    },
    "required": ["op"]
}


def _run(command, cwd, timeout=120):
    process = subprocess.Popen(
        command, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=cwd
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        process.kill()
        return -1, "", "Timeout"


async def handle(arguments: dict) -> str:
    op = arguments["op"]
    compose_path = arguments.get("compose_path", DEFAULT_COMPOSE_PATH)
    service = arguments.get("service", "")
    tail = arguments.get("tail", 100)

    # compose_path 可以是文件或目录
    compose_dir = os.path.dirname(os.path.abspath(compose_path))

    # 路径校验
    if not any(compose_dir.startswith(os.path.abspath(a)) for a in ALLOWED_WORKDIRS):
        return json.dumps({"status": "FAILED", "error": f"Path {compose_path} is not allowed"}, ensure_ascii=False)

    compose_flag = f"-f {os.path.abspath(compose_path)}" if os.path.isfile(compose_path) else ""

    try:
        if op == "ps":
            code, out, err = _run(f"docker compose {compose_flag} ps", compose_dir)
        elif op == "logs":
            code, out, err = _run(f"docker compose {compose_flag} logs --tail={tail} {service}", compose_dir)
        elif op == "up":
            code, out, err = _run(f"docker compose {compose_flag} up -d {service}", compose_dir, timeout=300)
        elif op == "down":
            code, out, err = _run(f"docker compose {compose_flag} down", compose_dir)
        elif op == "restart":
            code, out, err = _run(f"docker compose {compose_flag} restart {service}", compose_dir)
        elif op == "build":
            # 后台执行以防自杀中断
            cmd = f"nohup docker compose {compose_flag} up -d --build --force-recreate {service} > /dev/null 2>&1 &"
            subprocess.Popen(cmd, shell=True, cwd=compose_dir, start_new_session=True)
            return json.dumps({"status": "SUCCESS", "message": "Rebuild started in background."}, ensure_ascii=False)
        elif op == "inspect":
            svc = service or ""
            code, out, err = _run(f"docker inspect {svc}" if svc else "docker ps --format '{{.Names}}\\t{{.Status}}\\t{{.Ports}}'", compose_dir)
        else:
            return json.dumps({"status": "FAILED", "error": f"Unsupported op: {op}"}, ensure_ascii=False)

        return json.dumps({
            "status": "SUCCESS" if code == 0 else "FAILED",
            "exit_code": code,
            "stdout": out[-5000:] if len(out) > 5000 else out,
            "stderr": err[-2000:] if len(err) > 2000 else err,
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "FAILED", "error": str(e)}, ensure_ascii=False)
