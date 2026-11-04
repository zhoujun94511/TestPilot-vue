#!/usr/bin/python
# -*- coding: utf-8 -*-
"""仪表盘 /stats 数据范围与平台级指标可见性。"""

from __future__ import annotations

from sqlalchemy.orm import Query

from models.models import ChatSession, RagFileRecord, Requirement, TestCase
from services.auth_service import auth_required, current_user
from services.data_scope import apply_data_scope
from services.data_scope import scoped_chat_history_query as _scoped_chat_history_query


def platform_metrics_visible() -> bool:
    """性能指标、系统日志、录指标等全站平台数据（非 super_admin 在开启认证时不可见）。"""
    if not auth_required():
        return True
    user = current_user()
    return bool(user and user.get('role') == 'super_admin')


def scoped_cases_query() -> Query:
    return apply_data_scope(TestCase.query, TestCase, 'cases')


def scoped_requirements_query() -> Query:
    return apply_data_scope(Requirement.query, Requirement, 'requirements')


def scoped_chat_sessions_query() -> Query:
    return apply_data_scope(
        ChatSession.query.filter(ChatSession.is_deleted.is_(False)),
        ChatSession,
        'chat',
    )


def scoped_knowledge_files_query() -> Query:
    return apply_data_scope(
        RagFileRecord.query.filter(RagFileRecord.status == 'active'),
        RagFileRecord,
        'knowledge',
    )


def scoped_knowledge_chunk_count() -> int:
    """可见知识文件登记的 chunk 总数（rag_file_records.ids 为 chunk id 列表的字面量）。"""
    import ast

    total = 0
    for (raw_ids,) in scoped_knowledge_files_query().with_entities(RagFileRecord.ids).all():
        try:
            ids = ast.literal_eval(raw_ids) if raw_ids else []
        except (ValueError, SyntaxError, TypeError):
            continue
        if isinstance(ids, list):
            total += len(ids)
    return total


def scoped_chat_history_query():
    return _scoped_chat_history_query()


def empty_log_stats(hours: int) -> dict:
    return {
        'period_hours': hours,
        'level_distribution': {},
        'top_modules': [],
        'recent_errors': [],
    }


def empty_performance_stats(hours: int) -> dict:
    return {
        'period_hours': hours,
        'metrics': {},
        'summary': {},
    }


def limited_token_session_status() -> dict:
    """非 super_admin 可见的占位 payload（不暴露进程级 TokenMonitor 明细）。"""
    from config.settings import settings

    max_tokens = int(getattr(settings, 'TOKEN_MAX_PER_SESSION', 50000))
    max_calls = int(getattr(settings, 'TOKEN_MAX_CALLS_PER_SESSION', 100))
    return {
        'level': 'ok',
        'warn_threshold_percent': 80,
        'tokens': {'used': 0, 'max': max_tokens, 'percent': 0.0},
        'calls': {'used': 0, 'max': max_calls, 'percent': 0.0},
        'message_key': None,
        'message_params': {},
        'notice_signature': None,
        'limited_visibility': True,
    }


def limited_system_health() -> dict:
    """非 super_admin 不返回平台级探针详情。"""
    return {
        'success': True,
        'health': {
            'status': 'limited',
            'limited_visibility': True,
            'message': '仅超级管理员可查看完整系统健康状态',
        },
    }
