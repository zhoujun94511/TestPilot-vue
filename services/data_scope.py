#!/usr/bin/python
# -*- coding: utf-8 -*-
"""按角色与资源类型过滤 SQLAlchemy 查询。"""

from __future__ import annotations

from typing import Any, Optional, Type

from flask import g
from sqlalchemy.orm import Query

from services.auth_service import auth_required, current_user
from services.project_service import filter_query_by_current_project, record_in_current_project
from services.sql_query_helpers import deny_all, filter_by_eq, path_name_matches

ResourceKind = str  # cases | requirements | knowledge | chat


def _user() -> Optional[dict[str, Any]]:
    return current_user()


def apply_data_scope(query: Query, model: Type, resource: ResourceKind, *, project: bool = True) -> Query:
    """列表/计数查询附加数据范围。未开启 AUTH_REQUIRE_AUTH 时不改动。
    project=False 时只按部门，用于删除部门共用文档时清掉该部门各项目的需求。"""
    if not auth_required():
        return query
    user = _user()
    if not user:
        return deny_all(query)

    role = user.get('role')
    if role == 'super_admin':
        if not project:
            return query
        return filter_query_by_current_project(query, model, resource)

    dept_id = user.get('dept_id')
    if resource == 'chat':
        # 对话正文只给本人：管理员也不例外，部门统计走 apply_chat_stats_scope
        owner_col = getattr(model, 'owner_user_id', None)
        user_col = getattr(model, 'user_id', None)
        if owner_col is None:
            return filter_by_eq(query, user_col, str(user.get('id')))
        if user_col is None:
            return filter_by_eq(query, owner_col, user.get('id'))
        # 没写属主的老会话按 user_id 认领，与 can_access_record 口径一致
        return query.filter(
            (owner_col == user.get('id')) | (owner_col.is_(None) & (user_col == str(user.get('id'))))
        )

    dept_col = getattr(model, 'dept_id', None)
    if dept_col is None:
        return query
    if dept_id is None:
        return deny_all(query)
    from services.auth_migrations import find_default_department_id

    if dept_id == find_default_department_id():
        # 未标部门的历史记录归默认部门，与按 id 访问的 can_access_record 口径一致
        query = query.filter((dept_col == dept_id) | dept_col.is_(None))
    else:
        query = filter_by_eq(query, dept_col, dept_id)
    if not project:
        return query
    return filter_query_by_current_project(query, model, resource)


def apply_chat_stats_scope(query: Query, model: Type) -> Query:
    """聊天的计数口径（只用于统计数字，不返回正文）：超管全部，管理员本部门，普通用户本人。"""
    if not auth_required():
        return query
    user = _user()
    if not user:
        return deny_all(query)
    role = user.get('role')
    if role == 'super_admin':
        return query
    if role == 'admin':
        dept_id = user.get('dept_id')
        if dept_id is None:
            return deny_all(query)
        return filter_by_eq(query, getattr(model, 'dept_id'), dept_id)
    return apply_data_scope(query, model, 'chat')


def can_access_record(record, resource: ResourceKind) -> bool:
    if not auth_required():
        return True
    user = _user()
    if not user:
        return False
    if user.get('role') == 'super_admin':
        return record_in_current_project(record, resource)

    dept_id = user.get('dept_id')
    if resource == 'chat':
        owner = getattr(record, 'owner_user_id', None)
        if owner is not None:
            return owner == user.get('id')
        return str(getattr(record, 'user_id', '') or '') == str(user.get('id'))

    record_dept = getattr(record, 'dept_id', None)
    if dept_id is None:
        return False
    if record_dept is None:
        from services.auth_migrations import find_default_department_id

        record_dept = find_default_department_id()
    if record_dept is None or record_dept != dept_id:
        return False
    return record_in_current_project(record, resource)


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
    """磁盘文档是否可见：先看部门（超管不限），再看是否属于当前项目（所有角色）。"""
    if not auth_required():
        return True
    user = _user()
    if not user:
        return False
    safe_name = str(filename or '').strip()
    if not safe_name:
        return False
    doc_path, meta = _document_path_and_meta(safe_name)
    if user.get('role') != 'super_admin' and not _document_in_user_dept(user, safe_name, meta):
        return False
    return _document_in_current_project(doc_path, meta)


def _document_path_and_meta(safe_name: str):
    from pathlib import Path

    from flask import current_app

    from services.document_meta import read_document_meta

    try:
        doc_path = Path(current_app.config['UPLOAD_FOLDER']) / 'documents' / safe_name
        return doc_path, read_document_meta(doc_path)
    except (OSError, RuntimeError, KeyError):
        return None, {}


def _document_in_user_dept(user: dict, safe_name: str, meta: dict) -> bool:
    meta_dept = meta.get('dept_id')
    user_dept = user.get('dept_id')
    if meta_dept is not None:
        return user_dept is not None and int(meta_dept) == int(user_dept)
    meta_owner = meta.get('owner_user_id')
    if meta_owner is not None:
        return int(meta_owner) == int(user.get('id'))
    from models.models import Requirement

    try:
        scoped = apply_data_scope(Requirement.query, Requirement, 'requirements', project=False)
        return scoped.filter(path_name_matches(Requirement.source_file, safe_name)).limit(1).count() > 0
    except RuntimeError:
        return False


def _document_in_current_project(doc_path, meta: dict) -> bool:
    from services.project_service import document_project_id, resolve_current_project_id

    current = resolve_current_project_id()
    if current is None:
        return True
    if doc_path is None:
        return False
    return document_project_id(doc_path, meta) == current


def scoped_chat_history_query():
    """可见的聊天消息：只包含未软删除会话里的消息。
    会话删除后消息仍保留在库里，但对总览统计、最近活动、搜索和导出都不可见，与会话列表口径一致。"""
    from models.models import ChatHistory, ChatSession

    live_sessions = ChatSession.query.filter(ChatSession.is_deleted.is_(False))
    if not auth_required():
        return ChatHistory.query.filter(
            ChatHistory.session_id.in_(live_sessions.with_entities(ChatSession.session_id))
        )
    user = _user()
    if not user:
        return deny_all(ChatHistory.query)
    if user.get('role') == 'super_admin':
        return ChatHistory.query.filter(
            ChatHistory.session_id.in_(live_sessions.with_entities(ChatSession.session_id))
        )
    session_ids = [
        row[0]
        for row in apply_data_scope(live_sessions, ChatSession, 'chat')
        .with_entities(ChatSession.session_id)
        .all()
    ]
    if not session_ids:
        return deny_all(ChatHistory.query)
    return ChatHistory.query.filter(ChatHistory.session_id.in_(session_ids))
