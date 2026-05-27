"""
tool_git_ops - Git 版本控制操作
支持 status / commit / push / pull / clone / init_config / log / diff / branch
"""
import subprocess
import json
import os
from server.config import GIT_USER_NAME, GIT_USER_EMAIL, SSH_KEY_PATH, ALLOWED_WORKDIRS

GIT_SSH_CMD = f'ssh -i {SSH_KEY_PATH} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/known_hosts'

TOOL_NAME = "tool_git_ops"
TOOL_DESCRIPTION = "执行 Git 版本控制操作。op: status|commit|push|pull|clone|init_config|log|diff|branch。push 使用内置 SSH Key。"
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "op": {"type": "string", "enum": ["init_config", "clone", "commit", "push", "pull", "status", "log", "diff", "branch"]},
        "repo_path": {"type": "string", "description": "仓库路径"},
        "url": {"type": "string", "description": "clone 时的远程 URL"},
        "message": {"type": "string", "description": "commit 信息"},
        "force": {"type": "boolean"},
        "confirm_force": {"type": "boolean"},
        "args": {"type": "string", "description": "额外参数（log/diff/branch 时使用）"}
    },
    "required": ["op", "repo_path"]
}


def _run(command, cwd, use_ssh=False):
    env = os.environ.copy()
    if use_ssh and os.path.exists(SSH_KEY_PATH):
        try:
            os.chmod(SSH_KEY_PATH, 0o600)
        except OSError:
            pass
        env["GIT_SSH_COMMAND"] = GIT_SSH_CMD
    process = subprocess.Popen(
        command, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=cwd, env=env
    )
    stdout, stderr = process.communicate(timeout=60)
    return process.returncode, stdout, stderr


def _check_path(repo_path: str) -> str | None:
    abs_path = os.path.abspath(repo_path)
    if not any(abs_path.startswith(os.path.abspath(a)) for a in ALLOWED_WORKDIRS):
        return json.dumps({"status": "FAILED", "error": f"Path {repo_path} is not allowed"}, ensure_ascii=False)
    return None


async def handle(arguments: dict) -> str:
    op = arguments["op"]
    repo_path = arguments["repo_path"]

    err = _check_path(repo_path)
    if err:
        return err

    try:
        if op == "init_config":
            _run(f'git config --global user.name "{GIT_USER_NAME}"', repo_path)
            _run(f'git config --global user.email "{GIT_USER_EMAIL}"', repo_path)
            return json.dumps({"status": "SUCCESS", "message": "Git config updated"}, ensure_ascii=False)

        elif op == "clone":
            url = arguments.get("url", "")
            os.makedirs(repo_path, exist_ok=True)
            code, out, err_msg = _run(f"git clone {url} .", repo_path, use_ssh=True)
            return json.dumps({"status": "SUCCESS" if code == 0 else "FAILED", "stdout": out, "stderr": err_msg}, ensure_ascii=False)

        elif op == "commit":
            message = arguments.get("message", "Auto commit")
            _run("git add -A", repo_path)
            code, out, err_msg = _run(f'git commit -m "{message}"', repo_path)
            return json.dumps({"status": "SUCCESS" if code == 0 else "FAILED", "stdout": out, "stderr": err_msg}, ensure_ascii=False)

        elif op == "push":
            force = arguments.get("force", False)
            cmd = "git push origin master"
            if force:
                if not arguments.get("confirm_force", False):
                    return json.dumps({"status": "FAILED", "error": "Force push requires confirm_force=True"}, ensure_ascii=False)
                cmd += " --force"
            code, out, err_msg = _run(cmd, repo_path, use_ssh=True)
            return json.dumps({"status": "SUCCESS" if code == 0 else "FAILED", "stdout": out, "stderr": err_msg}, ensure_ascii=False)

        elif op == "pull":
            code, out, err_msg = _run("git pull", repo_path, use_ssh=True)
            return json.dumps({"status": "SUCCESS" if code == 0 else "FAILED", "stdout": out, "stderr": err_msg}, ensure_ascii=False)

        elif op == "status":
            code, out, err_msg = _run("git status", repo_path)
            return json.dumps({"status": "SUCCESS", "stdout": out, "stderr": err_msg}, ensure_ascii=False)

        elif op == "log":
            extra = arguments.get("args", "--oneline -20")
            code, out, err_msg = _run(f"git log {extra}", repo_path)
            return json.dumps({"status": "SUCCESS", "stdout": out}, ensure_ascii=False)

        elif op == "diff":
            extra = arguments.get("args", "")
            code, out, err_msg = _run(f"git diff {extra}", repo_path)
            return json.dumps({"status": "SUCCESS", "stdout": out}, ensure_ascii=False)

        elif op == "branch":
            extra = arguments.get("args", "-a")
            code, out, err_msg = _run(f"git branch {extra}", repo_path)
            return json.dumps({"status": "SUCCESS", "stdout": out}, ensure_ascii=False)

        else:
            return json.dumps({"status": "FAILED", "error": f"Unsupported op: {op}"}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "FAILED", "error": str(e)}, ensure_ascii=False)
