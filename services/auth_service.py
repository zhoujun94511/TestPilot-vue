#!/usr/bin/python
# -*- coding: utf-8 -*-
"""认证：密码、服务端会话、当前用户解析。"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from flask import g, request, session
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from config.settings import settings
from models.auth_models import User, UserSession
from models.models import db

SESSION_TTL_HOURS = 24
VALID_ROLES = frozenset({'super_admin', 'admin', 'user'})
USERNAME_MIN_LEN = 3
USERNAME_MAX_LEN = 64
PASSWORD_MIN_LEN = 8
PASSWORD_MAX_LEN = 128
EMAIL_MAX_LEN = 255
# \w 含汉字；额外只放行 . _ - @，避免空格、控制字符和易混淆的符号
_USERNAME_PATTERN = re.compile(r'^[\w.@-]+$')
_EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def validate_username(username: str) -> str:
    """规范化用户名；不符合规则时抛出 ValueError(weak_username|username_too_long|username_invalid_chars)。"""
    name = (username or '').strip()
    if len(name) < USERNAME_MIN_LEN:
        raise ValueError('weak_username')
    if len(name) > USERNAME_MAX_LEN:
        raise ValueError('username_too_long')
    if not _USERNAME_PATTERN.match(name):
        raise ValueError('username_invalid_chars')
    return name


def normalize_email(email: Any) -> Optional[str]:
    """空值返回 None；格式不对抛出 ValueError(invalid_email)。"""
    if email is None:
        return None
    if not isinstance(email, str):
        raise ValueError('invalid_email')
    text = email.strip()
    if not text:
        return None
    if len(text) > EMAIL_MAX_LEN or not _EMAIL_PATTERN.match(text):
        raise ValueError('invalid_email')
    return text


def find_user_by_username_ci(username: str, *, exclude_id: Optional[int] = None) -> Optional[User]:
    query = User.query.filter(func.lower(User.username) == (username or '').strip().lower())
    if exclude_id is not None:
        query = query.filter(User.id != exclude_id)
    return query.first()


def find_user_by_email_ci(email: Optional[str], *, exclude_id: Optional[int] = None) -> Optional[User]:
    if not email:
        return None
    query = User.query.filter(func.lower(User.email) == email.strip().lower())
    if exclude_id is not None:
        query = query.filter(User.id != exclude_id)
    return query.first()


def password_complexity_required() -> bool:
    return bool(getattr(settings, 'AUTH_PASSWORD_REQUIRE_COMPLEXITY', True))


def validate_password(password: str) -> None:
    """长度 + 可选复杂度；不符合时抛出 ValueError(weak_password|password_* )。"""
    pwd = password or ''
    if len(pwd) < PASSWORD_MIN_LEN:
        raise ValueError('weak_password')
    if len(pwd) > PASSWORD_MAX_LEN:
        raise ValueError('password_too_long')
    if not password_complexity_required():
        return
    if not re.search(r'[A-Za-z]', pwd):
        raise ValueError('password_needs_letter')
    if not re.search(r'\d', pwd):
        raise ValueError('password_needs_digit')
    if not re.search(r'[^A-Za-z0-9]', pwd):
        raise ValueError('password_needs_symbol')


def account_lock_enabled() -> bool:
    return bool(getattr(settings, 'AUTH_LOCK_ENABLED', True))


def _lock_max_failures() -> int:
    return max(1, int(getattr(settings, 'AUTH_LOCK_MAX_FAILURES', 5)))


def _lock_duration_seconds() -> int:
    return max(60, int(getattr(settings, 'AUTH_LOCK_DURATION_SECONDS', 900)))


def _clear_expired_lock(user: User) -> None:
    if user.locked_until and user.locked_until <= _now_utc():
        user.locked_until = None
        user.failed_login_count = 0


def is_account_locked(user: User) -> bool:
    if not account_lock_enabled():
        return False
    _clear_expired_lock(user)
    return bool(user.locked_until and user.locked_until > _now_utc())


def register_login_failure(user: User) -> bool:
    """记录一次失败；若刚触发锁定返回 True。"""
    if not account_lock_enabled():
        return False
    count = int(user.failed_login_count or 0) + 1
    user.failed_login_count = count
    locked_now = False
    if count >= _lock_max_failures():
        user.locked_until = _now_utc() + timedelta(seconds=_lock_duration_seconds())
        locked_now = True
    db.session.commit()
    return locked_now


def clear_login_failures(user: User) -> None:
    user.failed_login_count = 0
    user.locked_until = None


def credential_validation_error_code(exc: ValueError) -> str:
    return str(exc) if str(exc) else 'weak_credentials'


def auth_required() -> bool:
    return bool(getattr(settings, 'AUTH_REQUIRE_AUTH', False))


def register_enabled() -> bool:
    return bool(getattr(settings, 'AUTH_REGISTER_ENABLED', False))


def register_requires_approval() -> bool:
    return bool(getattr(settings, 'AUTH_REGISTER_REQUIRE_APPROVAL', True))


def trust_proxy_headers() -> bool:
    return bool(getattr(settings, 'AUTH_TRUST_PROXY_HEADERS', False))


def client_ip(req) -> str:
    """客户端 IP；只有显式信任代理时才读 X-Forwarded-For。"""
    if trust_proxy_headers():
        forwarded = req.headers.get('X-Forwarded-For', '').split(',')[0].strip()
        if forwarded:
            return forwarded
    return req.remote_addr or 'unknown'


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash_password(password: str, salt: str) -> str:
    return generate_password_hash(password + salt)


def new_password_fields(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(32)
    return _hash_password(password, salt), salt


def verify_password(stored_hash: str, salt: str, password: str) -> bool:
    return check_password_hash(stored_hash, password + salt)


_DUMMY_PASSWORD_HASH: Optional[str] = None


def _dummy_password_hash() -> str:
    global _DUMMY_PASSWORD_HASH
    if _DUMMY_PASSWORD_HASH is None:
        _DUMMY_PASSWORD_HASH = generate_password_hash(secrets.token_hex(16))
    return _DUMMY_PASSWORD_HASH


def _row_to_user(user: User) -> Dict[str, Any]:
    return user.to_public_dict()


@dataclass(frozen=True)
class LoginAttemptResult:
    user: Optional[Dict[str, Any]]
    status: str  # ok | invalid | locked | inactive


def attempt_login(username: str, password: str) -> LoginAttemptResult:
    name = (username or '').strip()
    if not name:
        return LoginAttemptResult(None, 'invalid')
    # 注册按不区分大小写查重，登录也要一致；精确匹配优先，兼容历史上大小写不同的重名账号
    user = User.query.filter_by(username=name).first() or find_user_by_username_ci(name)
    if not user:
        # 账号不存在也算一次哈希，否则响应快慢就能看出用户名是否存在
        check_password_hash(_dummy_password_hash(), password or '')
        return LoginAttemptResult(None, 'invalid')
    password_ok = verify_password(user.password_hash, user.salt, password)
    # 只有密码正确才提示已锁定，否则锁定提示会暴露账号存在
    if is_account_locked(user):
        return LoginAttemptResult(None, 'locked' if password_ok else 'invalid')
    if not password_ok:
        register_login_failure(user)
        return LoginAttemptResult(None, 'invalid')
    # 停用状态只在密码正确后告知，避免借此探测账号
    if not user.is_active:
        clear_login_failures(user)
        db.session.commit()
        return LoginAttemptResult(None, 'inactive')
    clear_login_failures(user)
    user.last_login = _now_utc()
    db.session.commit()
    return LoginAttemptResult(_row_to_user(user), 'ok')


def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    result = attempt_login(username, password)
    return result.user if result.status == 'ok' else None


def revoke_user_sessions(user_id: int) -> None:
    UserSession.query.filter_by(user_id=user_id).delete()
    db.session.commit()


def create_session(user_id: int) -> str:
    """换掉这个账号的全部旧令牌，只留下新的一张。删除和插入在同一事务里提交。"""
    token = secrets.token_urlsafe(32)
    expires = _now_utc() + timedelta(hours=SESSION_TTL_HOURS)
    UserSession.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    db.session.add(
        UserSession(user_id=user_id, session_token=token, expires_at=expires)
    )
    db.session.commit()
    return token


def destroy_session(token: str) -> None:
    if not token:
        return
    UserSession.query.filter_by(session_token=token).delete()
    db.session.commit()


_BEARER_PREFIX = 'Bearer '
_MAX_SESSION_TOKEN_LENGTH = 128


def bearer_token_from_request() -> str:
    """只认「Bearer 」前缀。空白、超长或中间带空白都当成没有令牌。"""
    header = request.headers.get('Authorization', '')
    if not header.startswith(_BEARER_PREFIX):
        return ''
    token = header[len(_BEARER_PREFIX):].strip()
    if not token or len(token) > _MAX_SESSION_TOKEN_LENGTH:
        return ''
    if any(character.isspace() for character in token):
        return ''
    return token


def revoke_request_sessions() -> None:
    """作废本次请求里的 Bearer 和 cookie 令牌。两处是同一枚时只删一次。"""
    tokens: list[str] = []
    for token in (bearer_token_from_request(), str(session.get('session_token') or '')):
        if token and token not in tokens:
            tokens.append(token)
    for token in tokens:
        destroy_session(token)
    session.pop('session_token', None)


_SESSION_CLEANUP_INTERVAL_SECONDS = 300.0
_last_expired_session_cleanup = 0.0


def _purge_expired_sessions(now) -> None:
    global _last_expired_session_cleanup
    import time

    if time.monotonic() - _last_expired_session_cleanup < _SESSION_CLEANUP_INTERVAL_SECONDS:
        return
    deleted = UserSession.query.filter(UserSession.expires_at < now).delete(
        synchronize_session=False
    )
    if deleted:
        db.session.commit()
    _last_expired_session_cleanup = time.monotonic()


def validate_token(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    now = _now_utc()
    _purge_expired_sessions(now)
    row = (
        db.session.query(User)
        .join(UserSession, User.id == UserSession.user_id)
        .filter(
            UserSession.session_token == token,
            User.is_active.is_(True),
            UserSession.expires_at > now,
        )
        .first()
    )
    return _row_to_user(row) if row else None


def current_user() -> Optional[Dict[str, Any]]:
    if hasattr(g, 'current_user'):
        return g.current_user
    user = validate_token(bearer_token_from_request())
    if user is None:
        user = validate_token(str(session.get('session_token') or ''))
    g.current_user = user
    return user


def stamp_ownership(record) -> None:
    """创建业务记录时写入部门与属主（已登录时）。"""
    user = current_user()
    if not user:
        return
    from services.project_service import PROJECT_MODELS

    if isinstance(record, PROJECT_MODELS) and getattr(record, 'project_id', None) is None:
        from services.project_service import ensure_default_project, resolve_current_project_id

        project_id = resolve_current_project_id()
        if project_id is None and user.get('dept_id') is not None:
            project_id = ensure_default_project(int(user['dept_id'])).id
        if project_id is not None:
            record.project_id = project_id
    if hasattr(record, 'dept_id') and getattr(record, 'dept_id', None) is None:
        record.dept_id = _record_project_dept_id(record)
        if record.dept_id is None:
            record.dept_id = user.get('dept_id')
    if hasattr(record, 'owner_user_id') and getattr(record, 'owner_user_id', None) is None:
        record.owner_user_id = user.get('id')
    if hasattr(record, 'user_id'):
        uid = getattr(record, 'user_id', None)
        if uid is None or str(uid).strip() == '':
            record.user_id = str(user.get('id'))


def _record_project_dept_id(record) -> Optional[int]:
    """超管切到别的部门的项目里建数据时，部门要跟项目走，否则该部门的人看不到。"""
    project_id = getattr(record, 'project_id', None)
    if project_id is None:
        return None
    from models.auth_models import Project

    project = db.session.get(Project, int(project_id))
    return project.dept_id if project else None


_USER_REF_COLUMNS = frozenset({'user_id', 'owner_user_id', 'actor_user_id', 'target_user_id'})


def _next_user_id() -> int:
    """SQLite 不带 AUTOINCREMENT 时会复用最大的已删 id，新用户会继承旧用户的会话和数据归属。
    取用户表和所有引用用户 id 的列里的最大值再加一。"""
    from sqlalchemy import Integer, cast, func, inspect, select

    existing = set(inspect(db.engine).get_table_names())
    highest = 0
    for table in db.metadata.tables.values():
        if table.name not in existing:
            continue
        for column in table.columns:
            is_user_pk = table.name == 'users' and column.name == 'id'
            if not is_user_pk and column.name not in _USER_REF_COLUMNS:
                continue
            value = db.session.execute(select(func.max(cast(column, Integer)))).scalar()
            if value is not None:
                highest = max(highest, int(value))
    return highest + 1


def create_user(
    *,
    username: str,
    password: str,
    email: str | None = None,
    role: str = 'user',
    dept_id: int | None = None,
    is_active: bool = True,
) -> User:
    role_name = (role or 'user').strip()
    if role_name not in VALID_ROLES:
        raise ValueError(f'invalid role: {role_name}')
    clean_username = validate_username(username)
    validate_password(password)
    pwd_hash, salt = new_password_fields(password)
    user = User(
        id=_next_user_id(),
        username=clean_username,
        email=normalize_email(email),
        password_hash=pwd_hash,
        salt=salt,
        role=role_name,
        dept_id=dept_id,
        is_active=bool(is_active),
    )
    db.session.add(user)
    db.session.commit()
    return user
