"""敏感词过滤（K12 内容安全第一道防线）

MVP 阶段使用简单关键词列表过滤；输入侧强制调用。
"""

BLOCKED_KEYWORDS = [
    "暴力",
    "色情",
    "赌博",
    "毒品",
    "自杀",
    "恐怖",
    "炸弹",
    "爆炸",
    "入侵",
    "黑客攻击",
    "武器",
    "血腥",
    "虐杀",
    "邪教",
]


def check_content(text: str) -> bool:
    """检查文本是否包含敏感词，返回 True 表示安全"""
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text:
            return False
    return True
