"""
Docker 相关资源：容器状态、compose 配置、镜像列表
"""
import subprocess
import json

RESOURCES = [
    {"uri": "docker://containers", "name": "Docker 容器列表", "description": "当前运行的所有 Docker 容器"},
    {"uri": "docker://compose-config", "name": "Docker Compose 配置", "description": "当前 docker-compose.yml 的解析内容"},
    {"uri": "docker://images", "name": "Docker 镜像列表", "description": "本地所有 Docker 镜像"},
]


async def read(uri: str) -> str:
    if uri == "docker://containers":
        proc = subprocess.run(
            ["docker", "ps", "--format", "table .Names\\t.Status\\t.Ports\\t.Image"],
            capture_output=True, text=True, timeout=10
        )
        return proc.stdout if proc.returncode == 0 else f"Error: {proc.stderr}"

    elif uri == "docker://compose-config":
        proc = subprocess.run(
            ["docker", "compose", "config"], capture_output=True, text=True,
            cwd="/app", timeout=10
        )
        return proc.stdout if proc.returncode == 0 else f"Error: {proc.stderr}"

    elif uri == "docker://images":
        proc = subprocess.run(
            ["docker", "images", "--format", "table .Repository\\t.Tag\\t.Size\\t.CreatedSince"],
            capture_output=True, text=True, timeout=10
        )
        return proc.stdout if proc.returncode == 0 else f"Error: {proc.stderr}"

    raise ValueError(f"Unknown docker resource: {uri}")
