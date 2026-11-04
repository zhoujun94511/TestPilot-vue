#!/usr/bin/python
# -*- coding: utf-8 -*-
"""按角色与资源类型过滤 SQLAlchemy 查询。"""

from __future__ import annotations

from typing import Any, Optional, Type

from flask import g
from sqlalchemy.orm import Query

from services.auth_service import auth_required, current_user
from services.sql_query_helpers import deny_all, filter_by_eq, filter_like_contains

ResourceKind = str  # cases | requirements | knowledge | chat


def _user() -> Optional[dict[str, Any]]:
    return current_user()


def apply_data_scope(query: Query, model: Type, resource: ResourceKind) -> Query:
    """列表/计数查询附加数据范围。未开启 AUTH_REQUIRE_AUTH 时不改动。"""
    if not auth_required():
        return query
    user = _user()
    if not user:
        return deny_all(query)

    role = user.get('role')
    if role == 'super_admin':
        return query

    dept_id = user.get('dept_id')
    if resource == 'chat':
        if role == 'admin':
            if dept_id is None:
                return deny_all(query)
            return filter_by_eq(query, getattr(model, 'dept_id'), dept_id)
        owner_col = getattr(model, 'owner_user_id', None)
        if owner_col is None:
            return filter_by_eq(query, getattr(model, 'user_id'), str(user.get('id')))
        return filter_by_eq(query, owner_col, user.get('id'))

    dept_col = getattr(model, 'dept_id', None)
    if dept_col is None:
        return query
    if dept_id is None:
        return deny_all(query)
    return filter_by_eq(query, dept_col, dept_id)


def can_access_record(record, resource: ResourceKind) -> bool:
    if not auth_required():
        return True
    user = _user()
    if not user:
        return False
    if user.get('role') == 'super_admin':
        return True

    dept_id = user.get('dept_id')
    if resource == 'chat':
        if user.get('role') == 'admin':
            return dept_id is not None and getattr(record, 'dept_id', None) == dept_id
        owner = getattr(record, 'owner_user_id', None)
        if owner is not None:
            return owner == user.get('id')
        return str(getattr(record, 'user_id', '') or '') == str(user.get('id'))

    record_dept = getattr(record, 'dept_id', None)
    if dept_id is None:
        return False
    if record_dept is None:
        from services.auth_migrations import get_default_department_id

        record_dept = get_default_department_id()
    return record_dept == dept_id


def set_g_user_for_tests(user: Optional[dict[str, Any]]) -> None:
    g.current_user = user


def apply_llm_usage_scope(query: Query) -> Query:
    from models.models import LlmUsageLog

    if not auth_required():
        return query
    user = _user()
    if not user:
        return deny_all(query)
    if user.get('role') == 'super_admin':
        return query
    if user.get('role') == 'user':
        return filter_by_eq(query, LlmUsageLog.user_id, user.get('id'))
    dept_id = user.get('dept_id')
    if dept_id is None:
        return deny_all(query)
    return filter_by_eq(query, LlmUsageLog.dept_id, dept_id)


def allowed_knowledge_file_ids() -> Optional[set[int]]:
    """None 表示不限制（未开认证）；否则为可见 rag_file_records.id 集合。"""
    if not auth_required():
        return None
    from models.models import RagFileRecord

    rows = apply_data_scope(RagFileRecord.query, RagFileRecord, 'knowledge').with_entities(
        RagFileRecord.id
    ).all()
    return {int(row[0]) for row in rows if row and row[0] is not None}


def _allowed_knowledge_scope() -> Optional[tuple[set[int], set[str]]]:
    """(可见文件 id, 可见文件存储名)；None 表示不限制。"""
    if not auth_required():
        return None
    from pathlib import PurePath

    from models.models import RagFileRecord

    rows = apply_data_scope(RagFileRecord.query, RagFileRecord, 'knowledge').with_entities(
        RagFileRecord.id, RagFileRecord.file_path
    ).all()
    ids = {int(row[0]) for row in rows if row and row[0] is not None}
    names = {PurePath(str(row[1]).replace('\\', '/')).name for row in rows if row and row[1]}
    return ids, names


def _metadata_in_scope(meta: dict, file_id: Any, scope: tuple[set[int], set[str]]) -> bool:
    ids, names = scope
    if file_id is not None:
        try:
            return int(file_id) in ids
        except (TypeError, ValueError):
            return False
    # 上传后 file_id 回填完成前，chunk 只有 source / file_name（磁盘存储名）
    from pathlib import PurePath

    for key in ('source', 'file_name'):
        value = meta.get(key)
        if value and PurePath(str(value).replace('\\', '/')).name in names:
            return True
    return False


def filter_scoped_retrieval_items(items: list) -> list:
    """
    过滤 Document / RetrievalResult 等带 metadata 属性的检索结果。
    SQLite 向量库不执行 filter kwargs，RAG 注入前必须走这一层。
    """
    scope = _allowed_knowledge_scope()
    if scope is None:
        return list(items or [])
    kept = []
    for item in items or []:
        meta = getattr(item, 'metadata', None)
        if isinstance(meta, dict) and _metadata_in_scope(meta, meta.get('file_id'), scope):
            kept.append(item)
    return kept


def filter_knowledge_search_results(results: list) -> list:
    scope = _allowed_knowledge_scope()
    if scope is None:
        return results
    filtered = []
    for item in results:
        if not isinstance(item, dict):
            continue
        meta = item.get('metadata') if isinstance(item.get('metadata'), dict) else {}
        if _metadata_in_scope(meta, item.get('file_id') or meta.get('file_id'), scope):
            filtered.append(item)
    return filtered


def can_access_document_filename(filename: str) -> bool:
    """磁盘文档是否在当前用户数据范围内（需求关联或侧车 meta 归属）。"""
    if not auth_required():
        return True
    user = _user()
    if not user:
        return False
    if user.get('role') == 'super_admin':
        return True
    from models.models import Requirement

    safe_name = str(filename or '').strip()
    if not safe_name:
        return False
    try:
        scoped = apply_data_scope(Requirement.query, Requirement, 'requirements')
        if filter_like_contains(scoped, Requirement.source_file, safe_name).limit(1).count() > 0:
            return True
    except RuntimeError:
        pass

    try:
        from pathlib import Path

        from flask import current_app

        from services.document_meta import read_document_meta

        doc_path = Path(current_app.config['UPLOAD_FOLDER']) / 'documents' / safe_name
        meta = read_document_meta(doc_path)
    except (OSError, RuntimeError, KeyError):
        meta = {}

    meta_dept = meta.get('dept_id')
    meta_owner = meta.get('owner_user_id')
    user_dept = user.get('dept_id')
    if meta_dept is not None:
        return user_dept is not None and int(meta_dept) == int(user_dept)
    if meta_owner is not None:
        return int(meta_owner) == int(user.get('id'))
    return False


def scoped_chat_history_query():
    from models.models import ChatHistory, ChatSession

    if not auth_required():
        return ChatHistory.query
    user = _user()
    if not user:
        return deny_all(ChatHistory.query)
    if user.get('role') == 'super_admin':
        return ChatHistory.query
    session_ids = [
        row[0]
        for row in apply_data_scope(ChatSession.query, ChatSession, 'chat')
        .with_entities(ChatSession.session_id)
        .all()
    ]
    if not session_ids:
        return deny_all(ChatHistory.query)
    return ChatHistory.query.filter(ChatHistory.session_id.in_(session_ids))
