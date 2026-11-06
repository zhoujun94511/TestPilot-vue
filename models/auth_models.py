#!/usr/bin/python
# -*- coding: utf-8 -*-
"""用户、部门与会话表（RBAC + 部门隔离）。"""

from __future__ import annotations

from datetime import datetime, timezone

from models.models import db
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint


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
        from services.auth_migrations import DEFAULT_DEPT_CODE

        payload = {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'is_active': bool(self.is_active),
            'created_time': self.created_time.isoformat() if self.created_time else None,
        }
        if self.code == DEFAULT_DEPT_CODE:
            payload['name_key'] = 'admin.users.dept.defaultName'
        return payload


class Project(db.Model):
    """部门下的项目。需求、用例和知识库按项目分开，部门决定谁能进入。"""

    __tablename__ = 'projects'
    __table_args__ = (
        UniqueConstraint('dept_id', 'name', name='uq_project_dept_name'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False, comment='项目名称')
    dept_id = Column(Integer, ForeignKey('departments.id'), nullable=False, index=True, comment='所属部门')
    created_time = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment='创建时间',
    )

    def to_dict(self):
        from services.project_service import DEFAULT_PROJECT_NAME

        payload = {
            'id': self.id,
            'name': self.name,
            'dept_id': self.dept_id,
            'created_time': self.created_time.isoformat() if self.created_time else None,
        }
        if self.name == DEFAULT_PROJECT_NAME:
            payload['name_key'] = 'common.project.defaultName'
        return payload


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
    must_change_password = Column(Boolean, default=False, comment='使用公开默认密码，登录后必须先改密码')

    def to_public_dict(self, *, include_lock_state: bool = False):
        payload = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'dept_id': self.dept_id,
            'is_active': bool(self.is_active),
            'must_change_password': bool(self.must_change_password),
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


class BootstrapMarker(db.Model):
    """首次初始化游标。存在即表示账号、配置中心缺省项已写过，后续启动不得重做。"""

    __tablename__ = 'app_bootstrap_markers'

    marker_key = Column(String(64), primary_key=True)
    completed_at = Column(DateTime, nullable=False, comment='完成时间')


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
