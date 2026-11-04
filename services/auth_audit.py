#!/usr/bin/python
# -*- coding: utf-8 -*-
"""认证与管理操作审计（落库 auth_audit_logs）。"""

from __future__ import annotations

import logging
from typing import Any, Optional

from config.settings import settings
from models.auth_models import AuthAuditLog
from models.models import db

logger = logging.getLogger(__name__)

# 登录 / 会话
EVENT_LOGIN_SUCCESS = 'login_success'
EVENT_LOGIN_FAILED = 'login_failed'
EVENT_LOGIN_LOCKED = 'login_locked'
EVENT_LOGIN_INACTIVE = 'login_inactive'
EVENT_LOGOUT = 'logout'
EVENT_USER_REGISTERED = 'user_registered'
EVENT_PASSWORD_CHANGED = 'password_changed'
# 用户管理
EVENT_USER_CREATED = 'user_created'
EVENT_USER_UPDATED = 'user_updated'
EVENT_USER_DELETED = 'user_deleted'
EVENT_USER_DEACTIVATED = 'user_deactivated'
EVENT_ACCOUNT_UNLOCKED = 'account_unlocked'


def auth_audit_enabled() -> bool:
    return bool(getattr(settings, 'AUTH_AUDIT_ENABLED', True))


def log_auth_event(
    event_type: str,
    *,
    actor_user_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    username: Optional[str] = None,
    ip_address: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    if not auth_audit_enabled():
        return
    try:
        row = AuthAuditLog(
            event_type=(event_type or '').strip()[:64],
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            username=(username or '').strip()[:64] or None,
            ip_address=(ip_address or '').strip()[:64] or None,
            detail=(detail or '').strip()[:500] or None,
        )
        db.session.add(row)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.warning('写入认证审计失败 event=%s: %s', event_type, exc)


def list_auth_audit_logs(*, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 500))
    safe_offset = max(0, int(offset))
    rows = (
        AuthAuditLog.query.order_by(AuthAuditLog.id.desc())
        .offset(safe_offset)
        .limit(safe_limit)
        .all()
    )
    return [row.to_dict() for row in rows]


def list_auth_audit_logs_page(*, page: int = 1, per_page: int = 20) -> dict[str, Any]:
    safe_page = max(1, int(page))
    safe_per_page = max(1, min(int(per_page), 100))
    query = AuthAuditLog.query.order_by(AuthAuditLog.id.desc())
    total = query.count()
    pages = (total + safe_per_page - 1) // safe_per_page if total else 0
    if pages and safe_page > pages:
        safe_page = pages
    rows = query.offset((safe_page - 1) * safe_per_page).limit(safe_per_page).all()
    return {
        'logs': [row.to_dict() for row in rows],
        'pagination': {
            'page': safe_page,
            'per_page': safe_per_page,
            'total': total,
            'pages': pages,
            'has_prev': safe_page > 1,
            'has_next': safe_page < pages if pages else False,
        },
    }
