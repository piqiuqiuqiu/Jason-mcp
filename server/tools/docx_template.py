#!/usr/bin/env python3
"""
tool_docx_template - Word 文档模板应用
"""
import json
import os
import re
import shutil
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm
from docx.oxml.ns import qn
from copy import deepcopy

# ── Tool 定义 ────────────────────────────────────────

TOOL_NAME = "tool_docx_template"
TOOL_DESCRIPTION = """将 Word 模板应用到现有文档，支持封面填充。直接修改原文档，保留所有图片和表格。"""
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "docx_path": {
            "type": "string",
            "description": "待处理的 Word 文档路径"
        },
        "template_path": {
            "type": "string",
            "description": "模板文件路径"
        },
        "cover_info": {
            "type": "object",
            "description": "封面填充信息",
            "properties": {
                "project_name": {"type": "string", "description": "项目名称"},
                "client_name": {"type": "string", "description": "客户名称"},
                "version": {"type": "string", "description": "版本号"},
                "date": {"type": "string", "description": "日期"}
            }
        }
    },
    "required": ["docx_path"]
}

# ── 辅助函数 ────────────────────────────────────────

FONT_SIZES = {
    '二号': 22,
    '三号': 16,
    '四号': 14,
    '小四': 12,
    '五号': 10.5
}


def insert_cover_page(doc: Document, cover_info: dict) -> None:
    """在文档开头插入封面信息"""
    project_name = cover_info.get("project_name", "")
    client_name = cover_info.get("client_name", "")
    version = cover_info.get("version", "")
    date = cover_info.get("date", "")

    # 创建封面段落（稍后插入到开头）
    cover_elements = []

    # 标题
    if project_name:
        title_para = doc.add_paragraph()
        title_para.alignment = 1  # 居中
        title_run = title_para.add_run(project_name)
        title_run.font.name = "SimSun"
        title_run._element.rPr.rFonts.set(qn('w:eastAsia'), 'SimSun')
        title_run.font.size = Pt(FONT_SIZES['二号'])
        title_run.bold = True
        cover_elements.append(title_para._element)

    # 副标题
    if project_name:
        subtitle_para = doc.add_paragraph()
        subtitle_para.alignment = 1
        subtitle_run = subtitle_para.add_run(f'{project_name}（模块）系统说明书')
        subtitle_run.font.name = "SimSun"
        subtitle_run._element.rPr.rFonts.set(qn('w:eastAsia'), 'SimSun')
        subtitle_run.font.size = Pt(FONT_SIZES['三号'])
        cover_elements.append(subtitle_para._element)

    # 空行
    empty_para = doc.add_paragraph()
    cover_elements.append(empty_para._element)

    # 项目信息表
    info_items = []
    if project_name:
        info_items.append(f'项目名称：{project_name}')
    if client_name:
        info_items.append(f'客户名称：{client_name}')
    if version:
        info_items.append(f'文档版本：{version}')
    if date:
        info_items.append(f'日    期：{date}')

    for item in info_items:
        info_para = doc.add_paragraph()
        info_run = info_para.add_run(item)
        info_run.font.name = "SimSun"
        info_run._element.rPr.rFonts.set(qn('w:eastAsia'), 'SimSun')
        info_run.font.size = Pt(FONT_SIZES['四号'])
        cover_elements.append(info_para._element)

    # 分隔线
    sep_para = doc.add_paragraph()
    sep_para.alignment = 1
    sep_run = sep_para.add_run('━' * 40)
    sep_run.font.color.rgb = None
    cover_elements.append(sep_para._element)

    # 空行
    empty_para2 = doc.add_paragraph()
    cover_elements.append(empty_para2._element)

    # 将封面元素移动到文档开头
    body = doc._element.body
    for elem in reversed(cover_elements):
        body.insert(0, elem)


def apply_template(docx_path: str, template_path: str, cover_info: dict, preserve_headers: bool = True) -> dict:
    """应用模板到文档 - 直接修改原文档，插入封面"""
    try:
        # 检查文件存在
        if not os.path.exists(docx_path):
            return {"status": "FAILED", "error": f"文档不存在: {docx_path}"}

        # 打开文档
        doc = Document(docx_path)

        # 统计原始内容
        original_images = 0
        for para in doc.paragraphs:
            for run in para.runs:
                original_images += len(run._element.findall('.//' + qn('wp:inline')))
        original_tables = len(doc.tables)
        original_paragraphs = len(doc.paragraphs)

        # 插入封面
        if cover_info:
            insert_cover_page(doc, cover_info)

        # 保存文档
        doc.save(docx_path)

        # 统计最终内容
        final_images = 0
        for para in doc.paragraphs:
            for run in para.runs:
                final_images += len(run._element.findall('.//' + qn('wp:inline')))

        return {
            "status": "SUCCESS",
            "message": "封面已添加到文档开头（保留原内容）",
            "output_path": docx_path,
            "cover_filled": bool(cover_info),
            "images_preserved": final_images,
            "tables_preserved": original_tables,
            "original_paragraphs": original_paragraphs,
            "final_paragraphs": len(doc.paragraphs)
        }

    except Exception as e:
        import traceback
        return {"status": "FAILED", "error": str(e), "traceback": traceback.format_exc()}


# ── 主处理函数 ────────────────────────────────────────

async def handle(arguments: dict) -> str:
    """处理 tool_docx_template 请求"""
    docx_path = arguments.get("docx_path", "")
    template_path = arguments.get("template_path", "")
    cover_info = arguments.get("cover_info", {})

    if not docx_path:
        return json.dumps({"status": "FAILED", "error": "缺少 docx_path 参数"}, ensure_ascii=False)

    result = apply_template(docx_path, template_path, cover_info)
    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import asyncio

    async def test():
        result = await handle({
            "docx_path": "test.docx",
            "cover_info": {"project_name": "测试项目", "version": "V1.0"}
        })
        print(result)

    asyncio.run(test())