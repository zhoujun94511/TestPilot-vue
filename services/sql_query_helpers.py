#!/usr/bin/python
# -*- coding: utf-8 -*-
"""SQLAlchemy 查询辅助（类型检查友好）。"""

from __future__ import annotations

from typing import Any, Optional, cast

from sqlalchemy import false as sa_false
from sqlalchemy.orm import Query
from sqlalchemy.sql.elements import ColumnElement


def deny_all(query: Query) -> Query:
    return query.filter(sa_false())


def filter_column_eq(query: Query, column: Any, value: Optional[str]) -> Query:
    if value is None or value == '':
        return query
    clause = cast(ColumnElement[bool], column == value)
    return query.filter(clause)


def filter_by_eq(query: Query, column: Any, value: Any) -> Query:
    """列等于任意可绑定值（int/str 等），满足静态类型检查。"""
    if value is None:
        return query
    clause = cast(ColumnElement[bool], column == value)
    return query.filter(clause)


def filter_like_contains(query: Query, column: Any, text: str) -> Query:
    needle = str(text or '').strip()
    if not needle:
        return query
    escaped = needle.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    clause = cast(ColumnElement[bool], column.like(f'%{escaped}%', escape='\\'))
    return query.filter(clause)


def path_name_matches(column: Any, file_name: str) -> Any:
    """路径列的文件名部分等于 file_name；不能用 contains，a.txt 会匹配到 ba.txt。"""
    from sqlalchemy import or_

    name = str(file_name or '').strip()
    escaped = name.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return or_(
        column == name,
        column.like(f'%/{escaped}', escape='\\'),
        column.like(f'%\\\\{escaped}', escape='\\'),
    )


def filter_expression(query: Query, expression: Any) -> Query:
    """包装任意 SQL 比较表达式，满足静态类型检查。"""
    return query.filter(cast(ColumnElement[bool], expression))
