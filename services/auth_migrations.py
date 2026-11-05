#!/usr/bin/python
# -*- coding: utf-8 -*-
"""认证与数据权限相关 SQLite 列迁移、默认部门与引导账号。"""

from __future__ import annotations

import logging
import os

from sqlalchemy import text

from models.auth_models import Department, User
from models.models import db
from services.auth_service import create_user

logger = logging.getLogger(__name__)

DEFAULT_DEPT_CODE = 'default'
DEFAULT_DEPT_NAME = '默认部门'

_SCOPE_COLUMNS: dict[str, list[tuple[str, str]]] = {
    'test_cases': [
        ('dept_id', 'INTEGER'),
        ('owner_user_id', 'INTEGER'),
    ],
    'requirements': [
        ('dept_id', 'INTEGER'),
        ('owner_user_id', 'INTEGER'),
    ],
    'rag_file_records': [
        ('dept_id', 'INTEGER'),
        ('owner_user_id', 'INTEGER'),
        ('vector_meta_pending', 'INTEGER DEFAULT 0'),
    ],
    'chat_sessions': [
        ('dept_id', 'INTEGER'),
        ('owner_user_id', 'INTEGER'),
    ],
    'llm_usage_logs': [
        ('dept_id', 'INTEGER'),
        ('user_id', 'INTEGER'),
    ],
}

_AUTH_USER_COLUMNS: list[tuple[str, str]] = [
    ('failed_login_count', 'INTEGER DEFAULT 0'),
    ('locked_until', 'DATETIME'),
]


def _table_columns(conn, table: str) -> set[str]:
    result = conn.execute(text(f'PRAGMA table_info({table})'))
    return {col[1] for col in result.fetchall()}


def ensure_auth_user_security_columns() -> None:
    with db.engine.connect() as conn:
        try:
            columns = _table_columns(conn, 'users')
        except Exception as exc:
            logger.warning('跳过 users 安全列检查: %s', exc)
            return
        for col_name, col_type in _AUTH_USER_COLUMNS:
            if col_name in columns:
                continue
            conn.execute(text(f'ALTER TABLE users ADD COLUMN {col_name} {col_type}'))
            conn.commit()
            logger.info('已添加 users.%s', col_name)


def ensure_scope_columns() -> None:
    with db.engine.connect() as conn:
        for table, specs in _SCOPE_COLUMNS.items():
            try:
                columns = _table_columns(conn, table)
            except Exception as exc:
                logger.warning('跳过表 %s 列检查: %s', table, exc)
                continue
            for col_name, col_type in specs:
                if col_name in columns:
                    continue
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col_name} {col_type}'))
                conn.commit()
                logger.info('已添加 %s.%s', table, col_name)


def get_default_department_id() -> int:
    dept = Department.query.filter_by(code=DEFAULT_DEPT_CODE).first()
    if dept:
        return dept.id
    dept = Department(code=DEFAULT_DEPT_CODE, name=DEFAULT_DEPT_NAME, is_active=True)
    db.session.add(dept)
    db.session.commit()
    return dept.id


def _default_department_id() -> int:
    """内部兼容别名，新代码请使用 get_default_department_id。"""
    return get_default_department_id()


def backfill_legacy_dept_id(default_dept_id: int) -> None:
    statements = [
        ('test_cases', 'dept_id'),
        ('requirements', 'dept_id'),
        ('rag_file_records', 'dept_id'),
        ('chat_sessions', 'dept_id'),
    ]
    with db.engine.connect() as conn:
        for table, col in statements:
            try:
                columns = _table_columns(conn, table)
            except (OSError, ValueError, RuntimeError) as exc:
                logger.debug('跳过回填表 %s: %s', table, exc)
                continue
            if col not in columns:
                continue
            conn.execute(
                text(f'UPDATE {table} SET {col} = :dept_id WHERE {col} IS NULL'),
                {'dept_id': default_dept_id},
            )
            conn.commit()


BUILTIN_BOOTSTRAP_PASSWORD = 'TestPilot@2026'


def bootstrap_account_specs() -> list[dict]:
    """三类初始账号。未单独设密码时，沿用 AUTH_BOOTSTRAP_SUPER_PASSWORD，仍为空才用内置密码。"""

    def resolve_password(specific_key: str) -> tuple[str, bool]:
        specific = os.getenv(specific_key, '').strip()
        if specific:
            return specific, False
        shared = os.getenv('AUTH_BOOTSTRAP_SUPER_PASSWORD', '').strip()
        if shared:
            return shared, False
        return BUILTIN_BOOTSTRAP_PASSWORD, True

    super_password, super_builtin = resolve_password('AUTH_BOOTSTRAP_SUPER_PASSWORD')
    admin_password, admin_builtin = resolve_password('AUTH_BOOTSTRAP_ADMIN_PASSWORD')
    user_password, user_builtin = resolve_password('AUTH_BOOTSTRAP_USER_PASSWORD')
    return [
        {
            'role': 'super_admin',
            'username': os.getenv('AUTH_BOOTSTRAP_SUPER_USERNAME', 'admin').strip() or 'admin',
            'password': super_password,
            'builtin_password': super_builtin,
            'email': os.getenv('AUTH_BOOTSTRAP_SUPER_EMAIL', '').strip() or None,
        },
        {
            'role': 'admin',
            'username': os.getenv('AUTH_BOOTSTRAP_ADMIN_USERNAME', 'manager').strip() or 'manager',
            'password': admin_password,
            'builtin_password': admin_builtin,
            'email': None,
        },
        {
            'role': 'user',
            'username': os.getenv('AUTH_BOOTSTRAP_USER_USERNAME', 'member').strip() or 'member',
            'password': user_password,
            'builtin_password': user_builtin,
            'email': None,
        },
    ]


def ensure_bootstrap_accounts() -> list[str]:
    """补齐尚未存在的初始账号。已有同名用户不改密码、不改角色。"""
    from services.auth_service import find_user_by_username_ci

    default_dept_id = _default_department_id()
    created: list[str] = []
    used_builtin = False
    for spec in bootstrap_account_specs():
        existing = find_user_by_username_ci(spec['username'])
        if existing:
            if existing.role != spec['role']:
                logger.warning(
                    '用户名 %s 已存在且角色为 %s，跳过初始角色 %s',
                    existing.username,
                    existing.role,
                    spec['role'],
                )
            continue
        create_user(
            username=spec['username'],
            password=spec['password'],
            role=spec['role'],
            dept_id=default_dept_id,
            email=spec['email'],
        )
        created.append(f"{spec['role']}:{spec['username']}")
        used_builtin = used_builtin or bool(spec['builtin_password'])
    if created:
        logger.info('已创建初始账号: %s', ', '.join(created))
        if used_builtin:
            logger.warning('部分初始账号使用了内置默认密码，请登录后立即修改。密码不写入界面提示。')
    return created


def seed_auth_bootstrap() -> None:
    default_dept_id = _default_department_id()
    backfill_legacy_dept_id(default_dept_id)

    from models.auth_models import BootstrapMarker

    if BootstrapMarker.query.filter_by(marker_key='first_run').first() is not None:
        return
    if User.query.count() > 0:
        return
    ensure_bootstrap_accounts()


def run_auth_migrations() -> None:
    ensure_scope_columns()
    ensure_auth_user_security_columns()
    seed_auth_bootstrap()
    try:
        from services.llm_usage_backfill import backfill_llm_usage_scope

        backfill_llm_usage_scope()
    except Exception as exc:
        logger.warning('llm_usage_logs 回填跳过: %s', exc)
