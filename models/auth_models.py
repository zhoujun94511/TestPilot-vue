#!/usr/bin/python
# -*- coding: utf-8 -*-
"""用户、部门与会话表（RBAC + 部门隔离）。"""

from __future__ import annotations

from datetime import datetime, timezone

from models.models import db
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String


class Department(db.Model):
    __tablename__ = 'departments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), unique=True, nullable=False, comment='部门编码')
    name = Column(String(200), nullable=False, comment='部门名称')
    is_active = Column(Boolean, default=True, comment='是否启用')
    created_time = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment='创建时间',
    )

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'is_active': bool(self.is_active),
            'created_time': self.created_time.isoformat() if self.created_time else None,
        }


class User(db.Model):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, comment='登录名')
    email = Column(String(255), nullable=True, comment='邮箱')
    password_hash = Column(String(255), nullable=False, comment='密码哈希')
    salt = Column(String(64), nullable=False, comment='密码盐')
    role = Column(
        String(32),
        nullable=False,
        default='user',
        comment='角色: super_admin, admin, user',
    )
    dept_id = Column(Integer, ForeignKey('departments.id'), nullable=True, comment='所属部门')
    is_active = Column(Boolean, default=True, comment='是否启用')
    created_time = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment='创建时间',
    )
    last_login = Column(DateTime, nullable=True, comment='最近登录')
    failed_login_count = Column(Integer, default=0, comment='连续登录失败次数')
    locked_until = Column(DateTime, nullable=True, comment='账户锁定截止时间')

    def to_public_dict(self, *, include_lock_state: bool = False):
        payload = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'dept_id': self.dept_id,
            'is_active': bool(self.is_active),
            'created_time': self.created_time.isoformat() if self.created_time else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }
        if include_lock_state:
            from services.auth_service import is_account_locked

            payload['failed_login_count'] = int(self.failed_login_count or 0)
            locked = is_account_locked(self)
            payload['is_locked'] = locked
            payload['locked_until'] = (
                self.locked_until.isoformat() if locked and self.locked_until else None
            )
        return payload


class AuthAuditLog(db.Model):
    __tablename__ = 'auth_audit_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(64), nullable=False, index=True, comment='事件类型')
    actor_user_id = Column(Integer, nullable=True, index=True, comment='操作者用户 ID')
    target_user_id = Column(Integer, nullable=True, index=True, comment='目标用户 ID')
    username = Column(String(64), nullable=True, comment='相关用户名快照')
    ip_address = Column(String(64), nullable=True, comment='客户端 IP')
    detail = Column(String(500), nullable=True, comment='附加说明')
    created_time = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        comment='事件时间',
    )

    def to_dict(self):
        return {
            'id': self.id,
            'event_type': self.event_type,
            'actor_user_id': self.actor_user_id,
            'target_user_id': self.target_user_id,
            'username': self.username,
            'ip_address': self.ip_address,
            'detail': self.detail,
            'created_time': self.created_time.isoformat() if self.created_time else None,
        }


class UserSession(db.Model):
    __tablename__ = 'user_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    session_token = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, comment='过期时间')
    created_time = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment='创建时间',
    )
