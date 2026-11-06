"""用例筛选值。

列表里看到的类别名和库里存的原文经常不是同一个字符串。
筛选按同一组叫法匹配，避免选「功能测试」却查不到「功能测试」这几行。
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence

from sqlalchemy.orm import Query

_CATEGORY_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("functional", ("functional", "功能测试", "functional testing")),
    ("performance", ("performance", "性能测试", "弱网测试", "performance testing")),
    ("security", ("security", "安全测试", "安全性测试", "security testing")),
    ("compatibility", ("compatibility", "兼容性测试", "compatibility testing")),
    ("usability", ("usability", "可用性测试", "易用性测试", "usability testing")),
    ("integration", ("integration", "集成测试", "接口测试", "api", "api testing", "integration testing")),
    ("regression", ("regression", "回归测试", "自动化测试", "自动化回归测试", "automation", "automation testing", "regression testing")),
)

_PRIORITY_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("P0", ("P0", "critical", "blocker", "urgent", "紧急", "最高", "致命")),
    ("P1", ("P1", "high", "h", "高", "严重")),
    ("P2", ("P2", "medium", "normal", "m", "中", "中等", "一般")),
    ("P3", ("P3", "low", "l", "低", "轻微")),
    ("P4", ("P4", "very_low", "vl", "lowest", "minimal", "最低")),
)


def normalize_priority(raw: Optional[str], default: str = "P2") -> str:
    """用例和需求共用一套优先级口径，写库前统一成 P0-P4。"""
    folded = str(raw or "").strip().casefold()
    if folded:
        for key, aliases in _PRIORITY_GROUPS:
            if folded == key.casefold() or folded in {str(item).casefold() for item in aliases}:
                return key
    return default


def _matching_values(raw: Optional[str], groups: Sequence[tuple[str, Sequence[str]]]) -> list[str]:
    text = str(raw or "").strip()
    if not text:
        return []
    folded = text.casefold()
    for key, aliases in groups:
        known = {key.casefold(), *(str(item).casefold() for item in aliases)}
        if folded in known:
            return list(dict.fromkeys((key, *aliases)))
    return [text]


def case_category_values(raw: Optional[str]) -> list[str]:
    return _matching_values(raw, _CATEGORY_GROUPS)


def case_priority_values(raw: Optional[str]) -> list[str]:
    return _matching_values(raw, _PRIORITY_GROUPS)


def filter_column_in(query: Query, column, values: Iterable[str]) -> Query:
    """忽略大小写匹配，库里历史数据里 p1 / P1 混用。"""
    from sqlalchemy import func

    choices = list(dict.fromkeys(str(item).casefold() for item in values if str(item).strip()))
    if not choices:
        return query
    return query.filter(func.lower(column).in_(choices))
