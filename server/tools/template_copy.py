#!/usr/bin/env python3
"""
tool_template_copy - 复制 Word 模板文件

将模板文件复制到输出位置，用于后续内容填充。
支持封面占位符预填充。
"""
import json
import os
import shutil
from pathlib import Path
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn

# ── Tool 定义 ────────────────────────────────────────

TOOL_NAME = "tool_template_copy"
TOOL_DESCRIPTION = """复制 Word 模板文件到输出位置。支持封面占位符预填充。
输出文件保存在 /app/files/ 目录下。"""
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "template_path": {
            "type": "string",
            "description": "模板文件路径（如 /app/resources/模板/文档模板V0.1.docx）"
        },
        "output": {
            "type": "string",
            "description": "输出文件名（相对于 /app/files/）"
        },
        "cover_info": {
            "type": "object",
            "description": "封面填充信息（可选）",
            "properties": {
                "project_name": {"type": "string", "description": "项目名称，替换（项目名称）"},
                "client_name": {"type": "string", "description": "客户名称，替换（客户名称）"},
                "version": {"type": "string", "description": "版本号，替换 V1.0"},
                "date": {"type": "string", "description": "日期"}
            }
        }
    },
    "required": ["template_path", "output"]
}

# 默认目录
FILES_DIR = "/app/files"


def copy_template(template_path: str, output_name: str, cover_info: dict = None) -> dict:
    """
    复制模板文件到输出位置

    Args:
        template_path: 模板文件路径
        output_name: 输出文件名
        cover_info: 封面填充信息

    Returns:
        结果字典
    """
    try:
        # 检查模板存在
        if not os.path.exists(template_path):
            return {"status": "FAILED", "error": f"模板不存在: {template_path}"}

        # 构建输出路径
        output_path = os.path.join(FILES_DIR, output_name)

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else FILES_DIR, exist_ok=True)

        # 如果有封面信息，打开文档填充后保存
        if cover_info:
            doc = Document(template_path)

            # 填充封面占位符
            for p in doc.paragraphs:
                for run in p.runs:
                    text = run.text

                    # 项目名称
                    if "（项目名称）" in text and cover_info.get("project_name"):
                        run.text = text.replace("（项目名称）", cover_info["project_name"])

                    # 客户名称
                    if "（客户名称）" in text and cover_info.get("client_name"):
                        run.text = text.replace("（客户名称）", cover_info["client_name"])

                    # 版本号
                    if "V1.0" in text and cover_info.get("version"):
                        run.text = text.replace("V1.0", cover_info["version"])

                    # 日期
                    if "（日期）" in text and cover_info.get("date"):
                        run.text = text.replace("（日期）", cover_info["date"])

            # 保存到输出路径
            doc.save(output_path)
        else:
            # 直接复制文件
            shutil.copy2(template_path, output_path)

        # 获取文件大小
        file_size = os.path.getsize(output_path)

        return {
            "status": "SUCCESS",
            "message": "模板复制成功",
            "output_path": output_path,
            "template_path": template_path,
            "size_bytes": file_size,
            "cover_filled": bool(cover_info)
        }

    except Exception as e:
        import traceback
        return {"status": "FAILED", "error": str(e), "traceback": traceback.format_exc()}


# ── 主处理函数 ────────────────────────────────────────

async def handle(arguments: dict) -> str:
    """处理 tool_template_copy 请求"""
    template_path = arguments.get("template_path", "")
    output = arguments.get("output", "")
    cover_info = arguments.get("cover_info", {})

    if not template_path:
        return json.dumps({"status": "FAILED", "error": "缺少 template_path 参数"}, ensure_ascii=False)

    if not output:
        return json.dumps({"status": "FAILED", "error": "缺少 output 参数"}, ensure_ascii=False)

    result = copy_template(template_path, output, cover_info if cover_info else None)
    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import asyncio

    async def test():
        result = await handle({
            "template_path": "/app/resources/模板/文档模板V0.1.docx",
            "output": "test_copy.docx",
            "cover_info": {"project_name": "测试项目", "version": "V2.0"}
        })
        print(result)

    asyncio.run(test())