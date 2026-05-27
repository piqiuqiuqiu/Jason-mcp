"""
tool_cron_mgr - Crontab 定时任务管理
支持 list / add / remove 操作
"""
import subprocess
import json

TOOL_NAME = "tool_cron_mgr"
TOOL_DESCRIPTION = "Crontab 定时任务管理。action: list(列出)|add(新增)|remove(删除)"
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["list", "add", "remove"]},
        "schedule": {"type": "string", "description": "cron 表达式，如 '0 * * * *'"},
        "command": {"type": "string", "description": "要执行的命令"},
        "pattern": {"type": "string", "description": "remove 时的匹配模式"}
    },
    "required": ["action"]
}


async def handle(arguments: dict) -> str:
    action = arguments["action"]
    try:
        if action == "list":
            proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            if proc.returncode != 0:
                return json.dumps({"status": "SUCCESS", "crontab": "(empty)", "message": "No crontab configured"}, ensure_ascii=False)
            return json.dumps({"status": "SUCCESS", "crontab": proc.stdout}, ensure_ascii=False)

        elif action == "add":
            schedule = arguments.get("schedule", "")
            command = arguments.get("command", "")
            if not schedule or not command:
                return json.dumps({"status": "FAILED", "error": "schedule and command required"}, ensure_ascii=False)
            # 读取现有 crontab
            proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            existing = proc.stdout if proc.returncode == 0 else ""
            new_entry = f"{schedule} {command}\n"
            if new_entry.strip() in existing:
                return json.dumps({"status": "SUCCESS", "message": "Entry already exists"}, ensure_ascii=False)
            updated = existing.rstrip("\n") + "\n" + new_entry
            proc2 = subprocess.run(["crontab", "-"], input=updated, capture_output=True, text=True)
            if proc2.returncode == 0:
                return json.dumps({"status": "SUCCESS", "message": f"Added: {new_entry.strip()}"}, ensure_ascii=False)
            return json.dumps({"status": "FAILED", "error": proc2.stderr}, ensure_ascii=False)

        elif action == "remove":
            pattern = arguments.get("pattern", "")
            if not pattern:
                return json.dumps({"status": "FAILED", "error": "pattern required"}, ensure_ascii=False)
            proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            if proc.returncode != 0:
                return json.dumps({"status": "SUCCESS", "message": "No crontab to modify"}, ensure_ascii=False)
            lines = [l for l in proc.stdout.splitlines() if pattern not in l]
            updated = "\n".join(lines) + "\n"
            removed = len(proc.stdout.splitlines()) - len(lines)
            subprocess.run(["crontab", "-"], input=updated, capture_output=True, text=True)
            return json.dumps({"status": "SUCCESS", "message": f"Removed {removed} entries matching '{pattern}'"}, ensure_ascii=False)

        else:
            return json.dumps({"status": "FAILED", "error": f"Unknown action: {action}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "FAILED", "error": str(e)}, ensure_ascii=False)
