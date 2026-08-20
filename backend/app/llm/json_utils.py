"""LLM 输出 JSON 兜底解析（五级保障第 2 级：兼容 markdown 代码块包裹）

策略：
1. 剥离 ```json ... ``` / ``` ... ``` 代码块；
2. 直接 json.loads 全文；
3. 失败则取第一个 { 到最后一个 }（或第一个 [ 到最后一个 ]）再解析，
   容忍模型在 JSON 前后附带说明文字。
"""

import json
import re

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```")


def _strip_fence(text: str) -> str:
    match = _FENCE_RE.search(text)
    return match.group(1).strip() if match else text.strip()


def _extract_bracket_region(text: str) -> str:
    """截取首尾大括号/方括号之间的内容（处理 JSON 内嵌花括号）。"""
    starts = [text.find("{"), text.find("[")]
    candidates = [i for i in starts if i != -1]
    if not candidates:
        raise ValueError("内容中找不到 JSON 起始符")
    start = min(candidates)
    open_ch = text[start]
    close_ch = "}" if open_ch == "{" else "]"
    return text[start : text.rfind(close_ch) + 1]


def extract_json(text: str) -> dict | list:
    """从 LLM 输出文本中提取并解析 JSON；失败抛 ValueError。"""
    if not text or not text.strip():
        raise ValueError("内容为空")

    cleaned = _strip_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    region = _extract_bracket_region(cleaned)
    if not region:
        raise ValueError("内容中不包含 JSON 结构")
    return json.loads(region)
