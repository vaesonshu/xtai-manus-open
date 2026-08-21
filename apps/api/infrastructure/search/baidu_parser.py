"""百度搜索结果页 HTML 解析（纯标准库，便于单测）。"""

from __future__ import annotations

import html
import re
from typing import Any

# 仅匹配正文区的自然结果卡片，跳过 head 内 CSS 片段
_CONTAINER_MARKER = re.compile(r'<div\s+class="result\s+c-container\b', re.I)
_MU_PATTERN = re.compile(r'\bmu="([^"]+)"')
_TITLE_PATTERNS = (
    re.compile(r'<span[^>]+class="[^"]*tts-b-hl[^"]*"[^>]*>([\s\S]*?)<', re.I),
    re.compile(r"<h3[\s\S]*?<a[^>]*>([\s\S]*?)</a>", re.I),
)
_SNIPPET_PATTERNS = (
    re.compile(r'class="[^"]*\bc-abstract\b[^"]*"[^>]*>([\s\S]*?)<', re.I),
    re.compile(r'class="[^"]*content-right[^"]*"[^>]*>([\s\S]*?)<', re.I),
    re.compile(r'class="[^"]*summary-text[^"]*"[^>]*>([\s\S]*?)<', re.I),
)
_CAPTCHA_MARKERS = ("百度安全验证", "请输入验证码", "网络不给力", "verify.baidu.com")


def strip_html_tags(raw: str) -> str:
    """移除 HTML 标签并规范化空白。"""
    text = re.sub(r"<[^>]+>", "", raw)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def looks_like_captcha_page(page_html: str) -> bool:
    """检测是否被百度风控页拦截。"""
    return any(marker in page_html for marker in _CAPTCHA_MARKERS)


def iter_result_blocks(page_html: str) -> list[str]:
    """按结果卡片切分 HTML 片段。"""
    body = page_html
    body_start = page_html.lower().find("<body")
    if body_start >= 0:
        body = page_html[body_start:]

    starts = [match.start() for match in _CONTAINER_MARKER.finditer(body)]
    blocks: list[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else start + 12000
        blocks.append(body[start:end])
    return blocks


def parse_result_block(block: str) -> dict[str, str] | None:
    """从单个结果卡片提取 title / url / snippet。"""
    mu_match = _MU_PATTERN.search(block)
    if mu_match is None:
        return None

    url = html.unescape(mu_match.group(1).strip())
    if not url.startswith("http"):
        return None

    title = ""
    for pattern in _TITLE_PATTERNS:
        match = pattern.search(block)
        if match is None:
            continue
        title = strip_html_tags(match.group(1))
        if title:
            break

    if not title:
        return None

    snippet = ""
    for pattern in _SNIPPET_PATTERNS:
        match = pattern.search(block)
        if match is None:
            continue
        snippet = strip_html_tags(match.group(1))
        if snippet:
            break

    return {"title": title, "url": url, "snippet": snippet}


def parse_baidu_search_html(page_html: str, *, max_results: int) -> list[dict[str, str]]:
    """解析百度搜索结果页，返回结构化条目列表。"""
    results: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for block in iter_result_blocks(page_html):
        item = parse_result_block(block)
        if item is None:
            continue
        if item["url"] in seen_urls:
            continue
        seen_urls.add(item["url"])
        results.append(item)
        if len(results) >= max_results:
            break

    return results


def format_search_message(query: str, results: list[dict[str, Any]]) -> str:
    """将搜索结果格式化为 LLM 易读的多行文本。"""
    if not results:
        return f"百度搜索「{query}」未找到相关结果。"

    lines = [f"百度搜索「{query}」共 {len(results)} 条结果："]
    for index, item in enumerate(results, start=1):
        lines.append(f"{index}. {item['title']}")
        lines.append(f"   链接: {item['url']}")
        snippet = str(item.get("snippet") or "").strip()
        if snippet:
            lines.append(f"   摘要: {snippet}")
    return "\n".join(lines)
