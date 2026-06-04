"""通用工具函数"""
from typing import Tuple


def escape_markdown(txt) -> str:
    """简单转义 Markdown 特殊字符"""
    if not isinstance(txt, str):
        txt = str(txt)
    return txt.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace('[', '\\[')


def parse_amount(amount_str: str) -> Tuple[float, bool]:
    """解析金额字符串，返回 (amount, is_usdt)

    支持格式:
        - '100u' / '100usdt' → (100.0, True)
        - '0.5' → (0.5, False)
    """
    is_usdt = False
    s = amount_str.lower().strip()
    if s.endswith('usdt'):
        is_usdt = True
        s = s[:-4]
    elif s.endswith('u'):
        is_usdt = True
        s = s[:-1]
    try:
        amount = float(s)
    except ValueError:
        raise ValueError(f"数量必须是数字: {amount_str}")
    return amount, is_usdt
