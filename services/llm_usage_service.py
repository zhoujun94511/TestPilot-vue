#!/usr/bin/python
# -*- coding: utf-8 -*-
"""全站 LLM Token 落库与仪表盘聚合"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func

from models.models import ChatHistory, LlmUsageLog, db
from services.auth_service import current_user
from services.data_scope import apply_llm_usage_scope
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


def log_llm_usage(
    tokens: int,
    model_name: Optional[str],
    source: str,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    ref_type: Optional[str] = None,
    ref_id: Optional[int] = None,
    created_time: Optional[datetime] = None,
    owner: Optional[tuple] = None,
) -> None:
    """写入一条 Token 消耗记录；带 ref 时幂等（同一 ref 不重复插入）。
    owner=(dept_id, user_id) 时按它归属，否则记到当前登录用户。"""
    total = int(tokens or 0)
    if total <= 0:
        return

    if ref_type and ref_id is not None:
        existing = LlmUsageLog.query.filter_by(ref_type=ref_type, ref_id=ref_id).first()
        if existing:
            return

    if owner is not None:
        actor = {'dept_id': owner[0], 'id': owner[1]}
    else:
        actor = current_user()
    row = LlmUsageLog(
        tokens=total,
        input_tokens=int(input_tokens or 0),
        output_tokens=int(output_tokens or 0),
        model_name=(model_name or None),
        source=(source or 'llm').strip() or 'llm',
        ref_type=ref_type,
        ref_id=ref_id,
        created_time=created_time or datetime.now(timezone.utc),
        dept_id=actor.get('dept_id') if actor else None,
        user_id=actor.get('id') if actor else None,
    )
    db.session.add(row)
    db.session.commit()


def log_chat_assistant_usage(chat_row: ChatHistory) -> None:
    if not chat_row or not chat_row.id:
        return
    log_llm_usage(
        int(chat_row.tokens_used or 0),
        chat_row.model_name,
        'chat',
        ref_type='chat_history',
        ref_id=chat_row.id,
        created_time=chat_row.created_time,
        owner=_chat_owner(chat_row.session_id),
    )


def _chat_owner(session_id: Optional[str], cache: Optional[dict] = None) -> Optional[tuple]:
    """聊天用量归会话属主，而不是触发记账的人（回填时触发人是查看报表的管理员）。"""
    if not session_id:
        return None
    if cache is not None and session_id in cache:
        return cache[session_id]
    from models.models import ChatSession

    chat_session = ChatSession.query.filter_by(session_id=session_id).first()
    owner = None
    if chat_session is not None:
        user_id = chat_session.owner_user_id
        if user_id is None and chat_session.user_id:
            try:
                user_id = int(chat_session.user_id)
            except (TypeError, ValueError):
                user_id = None
        owner = (chat_session.dept_id, user_id)
    if cache is not None:
        cache[session_id] = owner
    return owner


def backfill_chat_usage_since(start_date: datetime) -> int:
    """将历史 ChatHistory.tokens_used 同步到 llm_usage_logs（幂等）。"""
    inserted = 0
    rows = (
        ChatHistory.query.filter(
            ChatHistory.created_time >= start_date,
            ChatHistory.tokens_used > 0,
        )
        .order_by(ChatHistory.id.asc())
        .all()
    )
    logged_ids = {
        ref_id for (ref_id,) in db.session.query(LlmUsageLog.ref_id)
        .filter(LlmUsageLog.ref_type == 'chat_history', LlmUsageLog.ref_id.isnot(None))
        .all()
    }
    owners: dict = {}
    for row in rows:
        if row.id in logged_ids:
            continue
        owner = _chat_owner(row.session_id, owners)
        if owner is None:
            continue
        try:
            log_llm_usage(
                int(row.tokens_used or 0),
                row.model_name,
                'chat',
                ref_type='chat_history',
                ref_id=row.id,
                created_time=row.created_time,
                owner=owner,
            )
            inserted += 1
        except Exception as error:
            logger.warning('回填 Chat Token 失败 id=%s: %s', row.id, error)
            db.session.rollback()
    return inserted


def build_global_token_stats(days: int) -> Dict[str, Any]:
    """仪表盘 / 导出用：指定天数内的全站 Token 聚合。"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    try:
        from services.llm_usage_backfill import backfill_llm_usage_scope

        backfill_llm_usage_scope()
    except Exception as error:
        logger.warning('llm_usage 范围回填跳过: %s', error)
        db.session.rollback()

    try:
        backfill_chat_usage_since(start_date)
    except Exception as error:
        logger.warning('Chat Token 回填跳过: %s', error)
        db.session.rollback()

    scoped = apply_llm_usage_scope(LlmUsageLog.query)
    scoped = scoped.filter(
        LlmUsageLog.created_time >= start_date,
        LlmUsageLog.tokens > 0,
    )

    id_subq = scoped.with_entities(LlmUsageLog.id).subquery()
    base_on_ids = (LlmUsageLog.id.in_(id_subq),)

    token_stats = db.session.query(
        func.sum(LlmUsageLog.tokens).label('total_tokens'),
        func.avg(LlmUsageLog.tokens).label('avg_tokens'),
        func.count(LlmUsageLog.id).label('call_count'),
    ).filter(*base_on_ids).first()

    model_stats = (
        db.session.query(
            LlmUsageLog.model_name,
            func.sum(LlmUsageLog.tokens).label('total_tokens'),
            func.count(LlmUsageLog.id).label('call_count'),
        )
        .filter(*base_on_ids)
        .group_by(LlmUsageLog.model_name)
        .all()
    )

    source_stats = (
        db.session.query(
            LlmUsageLog.source,
            func.sum(LlmUsageLog.tokens).label('total_tokens'),
            func.count(LlmUsageLog.id).label('call_count'),
        )
        .filter(*base_on_ids)
        .group_by(LlmUsageLog.source)
        .all()
    )

    daily_tokens = (
        db.session.query(
            func.date(LlmUsageLog.created_time).label('date'),
            func.sum(LlmUsageLog.tokens).label('total_tokens'),
        )
        .filter(*base_on_ids)
        .group_by(func.date(LlmUsageLog.created_time))
        .all()
    )

    call_count = int(token_stats.call_count or 0)
    return {
        'period_days': days,
        'source': 'llm_usage_logs',
        'included_scopes': ['chat', 'case_generation', 'document_analysis', 'agent', 'llm'],
        'summary': {
            'total_tokens': int(token_stats.total_tokens or 0),
            'avg_tokens_per_call': round(float(token_stats.avg_tokens or 0), 2),
            'total_calls': call_count,
            # 兼容旧前端字段名
            'avg_tokens_per_message': round(float(token_stats.avg_tokens or 0), 2),
            'total_messages': call_count,
        },
        'by_model': [
            {
                'model': model or 'unknown',
                'total_tokens': int(tokens or 0),
                'message_count': int(count or 0),
                'call_count': int(count or 0),
            }
            for model, tokens, count in model_stats
        ],
        'by_source': [
            {
                'source': source or 'llm',
                'total_tokens': int(tokens or 0),
                'call_count': int(count or 0),
            }
            for source, tokens, count in source_stats
        ],
        'daily_usage': [
            {'date': str(date), 'total_tokens': int(tokens or 0)}
            for date, tokens in daily_tokens
        ],
    }
