#!/usr/bin/python
# -*- coding: utf-8 -*-
"""历史 llm_usage_logs 的 dept_id / user_id 回填。"""

from __future__ import annotations

import logging

from models.models import ChatHistory, ChatSession, LlmUsageLog, TestCase, db
from services.auth_migrations import get_default_department_id

logger = logging.getLogger(__name__)


def backfill_llm_usage_scope() -> dict:
    """幂等：补齐缺失的 dept_id / user_id。"""
    stats = {'default_dept': 0, 'chat_history': 0, 'test_case_ref': 0}
    default_dept = get_default_department_id()

    chat_rows = (
        db.session.query(LlmUsageLog, ChatHistory, ChatSession)
        .join(ChatHistory, (LlmUsageLog.ref_type == 'chat_history') & (LlmUsageLog.ref_id == ChatHistory.id))
        .join(ChatSession, ChatHistory.session_id == ChatSession.session_id)
        .filter(LlmUsageLog.dept_id.is_(None) | LlmUsageLog.user_id.is_(None))
        .all()
    )
    for log_row, _history, session in chat_rows:
        row_changed = False
        if log_row.dept_id is None and session.dept_id is not None:
            log_row.dept_id = session.dept_id
            row_changed = True
        if log_row.user_id is None:
            if session.owner_user_id is not None:
                log_row.user_id = session.owner_user_id
                row_changed = True
            elif session.user_id:
                try:
                    log_row.user_id = int(session.user_id)
                    row_changed = True
                except (TypeError, ValueError):
                    pass
        if row_changed:
            stats['chat_history'] += 1

    case_rows = (
        db.session.query(LlmUsageLog, TestCase)
        .join(TestCase, (LlmUsageLog.ref_type == 'test_case') & (LlmUsageLog.ref_id == TestCase.id))
        .filter(LlmUsageLog.dept_id.is_(None) | LlmUsageLog.user_id.is_(None))
        .all()
    )
    for log_row, case in case_rows:
        row_changed = False
        if log_row.dept_id is None and case.dept_id is not None:
            log_row.dept_id = case.dept_id
            row_changed = True
        if log_row.user_id is None and case.owner_user_id is not None:
            log_row.user_id = case.owner_user_id
            row_changed = True
        if row_changed:
            stats['test_case_ref'] += 1

    stats['default_dept'] = (
        LlmUsageLog.query.filter(
            LlmUsageLog.dept_id.is_(None),
            (LlmUsageLog.ref_type.is_(None)) | (LlmUsageLog.ref_id.is_(None)),
        )
        .update({LlmUsageLog.dept_id: default_dept}, synchronize_session=False)
    )

    db.session.commit()
    changed = stats['default_dept'] + stats['chat_history'] + stats['test_case_ref']
    if changed:
        logger.info('llm_usage_logs 范围回填: %s', stats)
    else:
        logger.debug('llm_usage_logs 范围回填: 无待更新记录')
    return stats
