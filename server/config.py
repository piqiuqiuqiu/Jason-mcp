"""
JasonMCP 配置管理
集中管理所有环境变量、路径常量和安全策略
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

# ── Server Settings ──────────────────────────────────
SERVER_NAME = "JasonMCP"
SERVER_VERSION = "0.2.0"
SERVER_HOST = os.getenv("MCP_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("MCP_PORT", "8000"))

# ── Auth ─────────────────────────────────────────────
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "")

# ── Path Settings ────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
LOGS_DIR = BASE_DIR / "logs"
STORE_DIR = BASE_DIR / "store"

# Ensure directories exist
for d in [DOWNLOADS_DIR, LOGS_DIR, STORE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Security ─────────────────────────────────────────
ALLOWED_WORKDIRS = os.getenv("ALLOWED_WORKDIRS", str(BASE_DIR)).split(",")

# Shell 命令黑名单
SHELL_BLACKLIST = [
    "rm -rf /", "rm -rf *", "mkfs", "dd if=", "shutdown", "reboot",
    ":(){ :|:& };:", "> /dev/sda", "docker rm", "docker rmi",
    "docker image rm", "docker container rm",
]

# ── Git Settings ─────────────────────────────────────
GIT_USER_NAME = os.getenv("GIT_USER_NAME", "JasonMCP")
GIT_USER_EMAIL = os.getenv("GIT_USER_EMAIL", "mcp@example.com")
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH", "/app/.ssh/id_ed25519")

# ── Docker Settings ──────────────────────────────────
DEFAULT_COMPOSE_PATH = os.getenv("DEFAULT_COMPOSE_PATH", str(BASE_DIR / "docker-compose.yml"))

# ── Upstream MCP (V1) Connection ─────────────────────
UPSTREAM_MCP_URL = os.getenv("UPSTREAM_MCP_URL", "http://notion-mcp:8000")

# ── Public URL ───────────────────────────────────────
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://v02.daishushushu0123.top")
