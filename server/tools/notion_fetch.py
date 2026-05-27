#!/usr/bin/env python3
"""
tool_notion_fetch - 从 Notion 页面获取内容并转换为 Markdown
"""
import json
import os
import re
import requests
import asyncio
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Tool 定义 ────────────────────────────────────────

TOOL_NAME = "tool_notion_fetch"
TOOL_DESCRIPTION = """从 Notion 页面获取内容并转换为 Markdown 格式。支持递归获取子块、表格解析。"""
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "page_id": {
            "type": "string",
            "description": "Notion 页面 ID（32位十六进制）"
        },
        "format": {
            "type": "string",
            "description": "输出格式：markdown（默认）或 json",
            "enum": ["markdown", "json"]
        },
        "recursive": {
            "type": "boolean",
            "description": "是否递归获取子块（默认 true）"
        },
        "include_tables": {
            "type": "boolean",
            "description": "是否包含表格内容（默认 true）"
        },
        "clean_heading_numbers": {
            "type": "boolean",
            "description": "是否清理标题编号（默认 true）"
        },
        "download_images": {
            "type": "boolean",
            "description": "是否下载图片到本地（默认 false）"
        },
        "image_dir": {
            "type": "string",
            "description": "图片保存目录（默认 /app/files/images/）"
        }
    },
    "required": ["page_id"]
}

# ── 配置 ────────────────────────────────────────

NOTION_API_KEY = os.environ["NOTION_API_KEY"]
NOTION_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"

# ── API 调用 ────────────────────────────────────────

def call_notion_api(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """调用 Notion API"""
    url = f"{NOTION_BASE_URL}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json"
    }

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=data, timeout=60)
        else:
            response = requests.post(url, headers=headers, json=data, timeout=60)

        if response.status_code != 200:
            return {"error": f"API Error {response.status_code}: {response.text[:200]}"}

        return response.json()
    except Exception as e:
        return {"error": str(e)}


def fetch_page_info(page_id: str) -> dict:
    """获取页面信息"""
    return call_notion_api(f"pages/{page_id}")


def fetch_blocks(block_id: str, recursive: bool = True) -> List[dict]:
    """递归获取所有 blocks（使用并发获取子块）"""
    all_blocks = []
    has_more = True
    start_cursor = None

    while has_more:
        endpoint = f"blocks/{block_id}/children?page_size=100"
        if start_cursor:
            endpoint += f"&start_cursor={start_cursor}"

        result = call_notion_api(endpoint)

        if "error" in result:
            return all_blocks

        blocks = result.get("results", [])

        if recursive:
            # 收集需要获取子块的 block
            blocks_with_children = [
                b for b in blocks
                if b.get("has_children", False) and b.get("type") not in ["child_page", "child_database"]
            ]

            if blocks_with_children:
                # 使用线程池并发获取子块
                with ThreadPoolExecutor(max_workers=5) as executor:
                    future_to_block = {
                        executor.submit(_fetch_block_children, b): b
                        for b in blocks_with_children
                    }
                    for future in as_completed(future_to_block):
                        block = future_to_block[future]
                        try:
                            children = future.result()
                            if children:
                                block["_children"] = children
                        except Exception:
                            pass

        all_blocks.extend(blocks)
        has_more = result.get("has_more", False)
        start_cursor = result.get("next_cursor")

    return all_blocks


def _fetch_block_children(block: dict) -> List[dict]:
    """获取单个 block 的子块"""
    return fetch_blocks(block["id"], recursive=True)


# ── 文本提取 ────────────────────────────────────────

def extract_rich_text(rich_text: List[dict]) -> str:
    """提取 rich_text 中的纯文本"""
    return "".join([rt.get("plain_text", "") for rt in rich_text if rt.get("plain_text")])


def clean_heading_number(text: str) -> str:
    """清理标题编号"""
    # 匹配 "1.1 标题" 或 "1.1.1 标题" 或 "1 标题"
    match = re.match(r'^((\d+\.){0,3}\d+)\s+', text)
    if match:
        return text[len(match.group(0)):]
    return text


# ── 图片下载 ────────────────────────────────────────

_image_cache = {}  # 缓存已下载的图片

def download_image_to_local(url: str, image_dir: str, index: int) -> str:
    """下载图片到本地目录，返回本地路径"""
    if url in _image_cache:
        return _image_cache[url]

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            # 确定图片格式
            content = response.content
            if content[:4] == b'\x89PNG':
                ext = 'png'
            elif content[:2] == b'\xff\xd8':
                ext = 'jpg'
            elif content[:4] == b'GIF8':
                ext = 'gif'
            else:
                ext = 'png'

            # 创建目录
            os.makedirs(image_dir, exist_ok=True)

            # 保存文件
            filename = f"image_{index}.{ext}"
            filepath = os.path.join(image_dir, filename)

            with open(filepath, 'wb') as f:
                f.write(content)

            _image_cache[url] = filepath
            return filepath
    except Exception as e:
        print(f"[Image] Download failed: {e}")

    return None


# ── Block 转换 ────────────────────────────────────────

_image_counter = 0  # 全局图片计数器

def block_to_markdown(block: dict, clean_numbers: bool = True, include_tables: bool = True,
                       download_images: bool = False, image_dir: str = None) -> str:
    """将单个 block 转换为 Markdown"""
    block_type = block.get("type", "")
    md_lines = []

    if block_type.startswith("heading_"):
        level = int(block_type.split("_")[1])
        text = extract_rich_text(block.get(block_type, {}).get("rich_text", []))
        if clean_numbers:
            text = clean_heading_number(text)
        prefix = "#" * min(level, 4)
        md_lines.append(f"{prefix} {text}")

    elif block_type == "paragraph":
        text = extract_rich_text(block.get("paragraph", {}).get("rich_text", []))
        if text.strip():
            md_lines.append(text)

    elif block_type == "bulleted_list_item":
        text = extract_rich_text(block.get("bulleted_list_item", {}).get("rich_text", []))
        md_lines.append(f"- {text}")

    elif block_type == "numbered_list_item":
        text = extract_rich_text(block.get("numbered_list_item", {}).get("rich_text", []))
        md_lines.append(f"1. {text}")

    elif block_type == "to_do":
        text = extract_rich_text(block.get("to_do", {}).get("rich_text", []))
        checked = block.get("to_do", {}).get("checked", False)
        checkbox = "[x]" if checked else "[ ]"
        md_lines.append(f"- {checkbox} {text}")

    elif block_type == "quote":
        text = extract_rich_text(block.get("quote", {}).get("rich_text", []))
        md_lines.append(f"> {text}")

    elif block_type == "code":
        text = extract_rich_text(block.get("code", {}).get("rich_text", []))
        lang = block.get("code", {}).get("language", "")
        md_lines.append(f"```{lang}\n{text}\n```")

    elif block_type == "callout":
        text = extract_rich_text(block.get("callout", {}).get("rich_text", []))
        icon = block.get("callout", {}).get("icon", {})
        emoji = icon.get("emoji", "💡") if icon else "💡"
        md_lines.append(f"> {emoji} {text}")

    elif block_type == "divider":
        md_lines.append("---")

    elif block_type == "table" and include_tables:
        table_md = convert_table(block)
        if table_md:
            md_lines.append(table_md)

    elif block_type == "image":
        global _image_counter
        image_data = block.get("image", {})
        url = ""
        if image_data.get("type") == "external":
            url = image_data.get("external", {}).get("url", "")
        elif image_data.get("type") == "file":
            url = image_data.get("file", {}).get("url", "")
        caption = extract_rich_text(image_data.get("caption", []))

        if url:
            if download_images and image_dir:
                # 下载图片到本地
                _image_counter += 1
                local_path = download_image_to_local(url, image_dir, _image_counter)
                if local_path:
                    md_lines.append(f"![{caption}]({local_path})")
                else:
                    md_lines.append(f"![{caption}]({url})")
            else:
                md_lines.append(f"![{caption}]({url})")

    return "\n".join(md_lines)


def convert_table(block: dict) -> str:
    """将表格 block 转换为 Markdown 表格"""
    children = block.get("_children", [])

    if not children:
        return ""

    rows = []
    for child in children:
        if child.get("type") == "table_row":
            cells = child.get("table_row", {}).get("cells", [])
            row_data = []
            for cell in cells:
                if isinstance(cell, list):
                    cell_text = extract_rich_text(cell)
                else:
                    cell_text = str(cell)
                row_data.append(cell_text.replace("|", "\\|"))
            rows.append(row_data)

    if not rows:
        return ""

    # 构建 Markdown 表格
    num_cols = max(len(row) for row in rows)
    lines = []

    for i, row in enumerate(rows):
        # 填充缺失列
        padded_row = row + [""] * (num_cols - len(row))
        lines.append("| " + " | ".join(padded_row) + " |")
        if i == 0:
            lines.append("| " + " | ".join(["---"] * num_cols) + " |")

    return "\n".join(lines)


def blocks_to_markdown(blocks: List[dict], clean_numbers: bool = True, include_tables: bool = True,
                        download_images: bool = False, image_dir: str = None) -> str:
    """将 blocks 列表转换为 Markdown"""
    md_parts = []

    for block in blocks:
        md = block_to_markdown(block, clean_numbers, include_tables, download_images, image_dir)
        if md.strip():
            md_parts.append(md)

    return "\n\n".join(md_parts)


# ── 主处理函数 ────────────────────────────────────────

async def handle(arguments: dict) -> str:
    """处理 tool_notion_fetch 请求"""
    global _image_counter
    _image_counter = 0  # 重置计数器

    page_id = arguments.get("page_id", "")
    output_format = arguments.get("format", "markdown")
    recursive = arguments.get("recursive", True)
    include_tables = arguments.get("include_tables", True)
    clean_numbers = arguments.get("clean_heading_numbers", True)
    download_images = arguments.get("download_images", False)
    image_dir = arguments.get("image_dir", "/app/files/images/")

    # 验证 page_id
    if not page_id:
        return json.dumps({"status": "FAILED", "error": "缺少 page_id 参数"}, ensure_ascii=False)

    if not re.match(r"^[a-f0-9]{32}$", page_id, re.IGNORECASE):
        return json.dumps({"status": "FAILED", "error": f"无效的 page_id 格式: {page_id}"}, ensure_ascii=False)

    try:
        # 获取页面信息
        page_info = fetch_page_info(page_id)
        if "error" in page_info:
            return json.dumps({"status": "FAILED", "error": page_info["error"]}, ensure_ascii=False)

        # 提取标题
        title = extract_rich_text(
            page_info.get("properties", {}).get("title", {}).get("title", [])
        )

        # 获取 blocks
        blocks = fetch_blocks(page_id, recursive=recursive)

        # 统计信息
        heading_count = sum(1 for b in blocks if b.get("type", "").startswith("heading_"))
        table_count = sum(1 for b in blocks if b.get("type") == "table")
        image_count = sum(1 for b in blocks if b.get("type") == "image")

        # 转换格式
        if output_format == "json":
            result = {
                "status": "SUCCESS",
                "page_id": page_id,
                "title": title,
                "blocks": blocks,
                "metadata": {
                    "block_count": len(blocks),
                    "heading_count": heading_count,
                    "table_count": table_count,
                    "image_count": image_count
                }
            }
        else:
            markdown = blocks_to_markdown(blocks, clean_numbers, include_tables, download_images, image_dir)
            result = {
                "status": "SUCCESS",
                "page_id": page_id,
                "title": title,
                "markdown": markdown,
                "metadata": {
                    "block_count": len(blocks),
                    "heading_count": heading_count,
                    "table_count": table_count,
                    "image_count": image_count,
                    "images_downloaded": _image_counter
                }
            }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"status": "FAILED", "error": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    # 测试
    import asyncio

    async def test():
        result = await handle({"page_id": "33b2b84f319480a29c3de6295921deff"})
        data = json.loads(result)
        if data.get("status") == "SUCCESS":
            print(f"Title: {data.get('title')}")
            print(f"Blocks: {data.get('metadata', {}).get('block_count')}")
            print(f"Markdown length: {len(data.get('markdown', ''))}")
        else:
            print(f"Error: {data.get('error')}")

    asyncio.run(test())