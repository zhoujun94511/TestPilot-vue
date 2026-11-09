#!/usr/bin/python
# -*- coding: utf-8 -*-
"""登录、登出、会话检查与可选注册。"""

from __future__ import annotations

from flask import Blueprint, current_app, request, session
from sqlalchemy.exc import IntegrityError

from models.models import db
from services.auth_service import (
    auth_required,
    client_ip,
    create_session,
    create_user,
    current_user,
    revoke_request_sessions,
    find_user_by_email_ci,
    find_user_by_username_ci,
    normalize_email,
    password_complexity_required,
    register_enabled,
    register_requires_approval,
    validate_password,
    validate_username,
)
from utils.utils_core.api_response import api_error, api_success
from utils.auth_decorators import admin_or_above, login_required
from services import user_admin_service as user_admin

auth_bp = Blueprint('auth', __name__)

_LOGIN_RATE_MAX = 15
_LOGIN_RATE_WINDOW_SECONDS = 60.0
_REGISTER_RATE_MAX = 8
_REGISTER_RATE_WINDOW_SECONDS = 60.0


class _BadField(ValueError):
    pass


def _client_ip_key() -> str:
    return client_ip(request)


def _validation_failed_response():
    return api_error(
        'VALIDATION_FAILED',
        message='用户名 3～64 位，仅限字母、数字、汉字及 . _ - @；密码 8～128 位且需含字母、数字与符号',
        message_key='auth.message.weakCredentials',
        status=400,
    )


def _invalid_email_response():
    return api_error(
        'VALIDATION_FAILED',
        message='邮箱格式不正确',
        message_key='auth.message.invalidEmail',
        status=400,
    )


def _duplicate_user_response():
    return api_error(
        'CONFLICT',
        message='用户名或邮箱已存在',
        message_key='auth.message.duplicateUser',
        status=409,
    )


def _bad_field_response():
    return api_error(
        'VALIDATION_FAILED',
        message='请求参数格式不正确',
        message_key='auth.message.invalidParams',
        status=400,
    )


def _optional_int(value) -> int | None:
    if value is None or str(value).strip() == '':
        return None
    if isinstance(value, bool):
        raise _BadField('not_int')
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise _BadField('not_int') from exc


def _optional_str(value) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise _BadField('not_str')
    return value


def _login_rate_limit_key() -> str:
    return f'login:{_client_ip_key()}'


def _register_rate_limit_key() -> str:
    return f'register:{_client_ip_key()}'


def _admin_disabled():
    if not auth_required():
        return api_error(
            'FORBIDDEN',
            message='请先开启 AUTH_REQUIRE_AUTH 后再使用账号管理',
            message_key='auth.message.adminRequiresAuth',
            status=403,
        )
    return None


def _body() -> dict:
    from flask import request
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


@auth_bp.post('/login')
def login():
    from services.request_rate_limit import sliding_window_allow

    if not sliding_window_allow(
        _login_rate_limit_key(),
        max_calls=_LOGIN_RATE_MAX,
        window_seconds=_LOGIN_RATE_WINDOW_SECONDS,
    ):
        return api_error(
            'TOO_MANY_REQUESTS',
            message='登录尝试过于频繁，请稍后再试',
            message_key='auth.message.loginRateLimited',
            status=429,
        )
    body = _body()
    username = str(body.get('username', '')).strip()
    password = str(body.get('password', ''))
    if not username or not password:
        return api_error(
            'VALIDATION_FAILED',
            message='用户名与密码不能为空',
            message_key='auth.message.credentialsRequired',
            status=400,
        )
    from services.auth_audit import (
        EVENT_LOGIN_FAILED,
        EVENT_LOGIN_INACTIVE,
        EVENT_LOGIN_LOCKED,
        EVENT_LOGIN_SUCCESS,
        log_auth_event,
    )
    from services.auth_service import attempt_login

    ip = _client_ip_key()
    attempt = attempt_login(username, password)
    if attempt.status == 'locked':
        log_auth_event(
            EVENT_LOGIN_LOCKED,
            username=username,
            ip_address=ip,
            detail='account_locked',
        )
        return api_error(
            'FORBIDDEN',
            message='登录失败次数过多，账户已暂时锁定，请稍后再试',
            message_key='auth.message.accountLocked',
            status=403,
        )
    if attempt.status == 'inactive':
        log_auth_event(
            EVENT_LOGIN_INACTIVE,
            username=username,
            ip_address=ip,
            detail='account_inactive',
        )
        return api_error(
            'FORBIDDEN',
            message='账号尚未启用或已停用，请联系管理员',
            message_key='auth.message.accountInactive',
            status=403,
        )
    if attempt.status != 'ok' or attempt.user is None:
        if attempt.status == 'invalid':
            log_auth_event(
                EVENT_LOGIN_FAILED,
                username=username,
                ip_address=ip,
            )
        return api_error(
            'UNAUTHORIZED',
            message='用户名或密码错误',
            message_key='auth.message.invalidCredentials',
            status=401,
        )
    user = attempt.user
    log_auth_event(
        EVENT_LOGIN_SUCCESS,
        actor_user_id=user['id'],
        username=user.get('username'),
        ip_address=ip,
    )
    token = create_session(user['id'])
    # 登录前的会话 id 可能是别人塞进来的，登录后换一个新的
    session.clear()
    session['session_token'] = token
    session.permanent = True
    regenerate = getattr(current_app.session_interface, 'regenerate', None)
    if callable(regenerate):
        regenerate(session)
    return api_success({'user': user, 'session_token': token})


@auth_bp.post('/logout')
def logout():
    from services.auth_audit import EVENT_LOGOUT, log_auth_event

    actor = current_user()
    log_auth_event(
        EVENT_LOGOUT,
        actor_user_id=actor.get('id') if actor else None,
        username=actor.get('username') if actor else None,
        ip_address=_client_ip_key(),
    )
    revoke_request_sessions()
    return api_success({'message': '已退出登录'})


@auth_bp.get('/check-auth')
def check_auth():
    user = current_user()
    return api_success({
        'authenticated': user is not None,
        'auth_required': auth_required(),
        'register_enabled': register_enabled(),
        'register_requires_approval': register_requires_approval(),
        'password_complexity_required': password_complexity_required(),
        'user': user,
    })


@auth_bp.post('/register')
def register():
    from services.request_rate_limit import sliding_window_allow

    if not register_enabled():
        return api_error(
            'FORBIDDEN',
            message='注册已关闭，请联系管理员开通账号',
            message_key='auth.message.registerDisabled',
            status=403,
        )
    if not sliding_window_allow(
        _register_rate_limit_key(),
        max_calls=_REGISTER_RATE_MAX,
        window_seconds=_REGISTER_RATE_WINDOW_SECONDS,
    ):
        return api_error(
            'TOO_MANY_REQUESTS',
            message='注册尝试过于频繁，请稍后再试',
            message_key='auth.message.registerRateLimited',
            status=429,
        )
    body = _body()
    username_raw = str(body.get('username', ''))
    password = str(body.get('password', ''))
    try:
        username = validate_username(username_raw)
        validate_password(password)
    except ValueError:
        return _validation_failed_response()
    try:
        email = normalize_email(body.get('email'))
    except ValueError:
        return _invalid_email_response()
    if find_user_by_username_ci(username) or find_user_by_email_ci(email):
        return _duplicate_user_response()
    from services.auth_audit import EVENT_USER_REGISTERED, log_auth_event
    from services.auth_migrations import get_default_department_id

    pending = register_requires_approval()
    try:
        user = create_user(
            username=username,
            password=password,
            email=email,
            role='user',
            dept_id=get_default_department_id(),
            is_active=not pending,
        )
    except IntegrityError:
        db.session.rollback()
        return _duplicate_user_response()
    log_auth_event(
        EVENT_USER_REGISTERED,
        target_user_id=user.id,
        username=user.username,
        ip_address=_client_ip_key(),
        detail='pending_approval' if pending else 'role=user',
    )
    if pending:
        return api_success(
            {'message': '注册成功，等待管理员审核启用', 'pending_approval': True},
            message_key='auth.message.registerPending',
        )
    return api_success({'message': '注册成功，请登录', 'pending_approval': False})


@auth_bp.get('/departments')
@admin_or_above
def list_departments():
    blocked = _admin_disabled()
    if blocked:
        return blocked
    return api_success({'departments': user_admin.list_departments()})


@auth_bp.post('/departments')
@admin_or_above
def create_department():
    blocked = _admin_disabled()
    if blocked:
        return blocked
    from services.auth_service import current_user

    if current_user().get('role') != 'super_admin':
        return api_error('FORBIDDEN', message_key='common.errors.http403', status=403)
    body = _body()
    try:
        dept = user_admin.create_department(
            str(body.get('code', '')),
            str(body.get('name', '')),
        )
    except ValueError as exc:
        code = str(exc)
        if code == 'duplicate_code':
            return api_error('CONFLICT', message='部门编码已存在', status=409)
        return api_error('VALIDATION_FAILED', message='部门编码与名称不能为空', status=400)
    except PermissionError:
        return api_error('FORBIDDEN', message_key='common.errors.http403', status=403)
    return api_success({'department': dept.to_dict()})


@auth_bp.get('/users')
@admin_or_above
def list_users():
    blocked = _admin_disabled()
    if blocked:
        return blocked
    return api_success({'users': user_admin.list_users()})


@auth_bp.post('/users')
@admin_or_above
def admin_create_user():
    blocked = _admin_disabled()
    if blocked:
        return blocked
    body = _body()
    username_raw = str(body.get('username', ''))
    password = str(body.get('password', ''))
    try:
        role = (_optional_str(body.get('role', 'user')) or 'user').strip()
        dept_id_int = _optional_int(body.get('dept_id'))
    except _BadField:
        return _bad_field_response()
    try:
        username = validate_username(username_raw)
        validate_password(password)
    except ValueError:
        return _validation_failed_response()
    try:
        email = normalize_email(body.get('email'))
    except ValueError:
        return _invalid_email_response()
    if find_user_by_username_ci(username) or find_user_by_email_ci(email):
        return _duplicate_user_response()
    try:
        user = user_admin.admin_create_user(
            username=username,
            password=password,
            email=email,
            role=role,
            dept_id=dept_id_int,
        )
    except PermissionError:
        return api_error('FORBIDDEN', message_key='common.errors.http403', status=403)
    except ValueError as exc:
        msg = str(exc)
        if msg == 'invalid_role':
            return api_error('VALIDATION_FAILED', message='无效角色', status=400)
        if msg == 'dept_required':
            return api_error('VALIDATION_FAILED', message='请选择部门', status=400)
        return api_error('VALIDATION_FAILED', message=msg, status=400)
    from services.auth_audit import EVENT_USER_CREATED, log_auth_event
    from services.auth_service import current_user

    actor = current_user()
    log_auth_event(
        EVENT_USER_CREATED,
        actor_user_id=actor.get('id') if actor else None,
        target_user_id=user.id,
        username=user.username,
        ip_address=_client_ip_key(),
        detail=f'role={user.role}',
    )
    return api_success({'user': user.to_public_dict()})


@auth_bp.put('/users/<int:user_id>')
@admin_or_above
def admin_update_user(user_id: int):
    blocked = _admin_disabled()
    if blocked:
        return blocked
    body = _body()
    updates = {}
    try:
        if 'email' in body:
            updates['email'] = _optional_str(body.get('email')) or ''
        if 'role' in body:
            updates['role'] = _optional_str(body.get('role'))
        if 'dept_id' in body:
            updates['dept_id'] = _optional_int(body.get('dept_id'))
        if 'is_active' in body:
            if not isinstance(body.get('is_active'), bool):
                raise _BadField('not_bool')
            updates['is_active'] = body.get('is_active')
        if body.get('password'):
            updates['password'] = _optional_str(body.get('password'))
    except _BadField:
        return _bad_field_response()
    try:
        user = user_admin.admin_update_user(user_id, **updates)
    except LookupError:
        return api_error('NOT_FOUND', message='用户不存在', status=404)
    except PermissionError:
        return api_error('FORBIDDEN', message_key='common.errors.http403', status=403)
    except ValueError as exc:
        code = str(exc)
        if code == 'cannot_deactivate_self':
            return api_error(
                'VALIDATION_FAILED',
                message='不能停用当前登录账号',
                message_key='auth.message.cannotDeactivateSelf',
                status=400,
            )
        if code == 'last_super_admin':
            return api_error(
                'VALIDATION_FAILED',
                message='至少保留一个启用中的超级管理员',
                message_key='auth.message.lastSuperAdmin',
                status=400,
            )
        if code == 'invalid_email':
            return _invalid_email_response()
        if code == 'duplicate_email':
            return _duplicate_user_response()
        if code == 'invalid_role':
            return api_error(
                'VALIDATION_FAILED',
                message='无效角色',
                message_key='auth.message.invalidRole',
                status=400,
            )
        return _validation_failed_response()
    from services.auth_audit import EVENT_USER_UPDATED, log_auth_event
    from services.auth_service import current_user

    actor = current_user()
    log_auth_event(
        EVENT_USER_UPDATED,
        actor_user_id=actor.get('id') if actor else None,
        target_user_id=user.id,
        username=user.username,
        ip_address=_client_ip_key(),
        detail=','.join(sorted(updates.keys())) if updates else None,
    )
    return api_success({'user': user.to_public_dict()})


@auth_bp.delete('/users/<int:user_id>')
@admin_or_above
def admin_delete_user(user_id: int):
    blocked = _admin_disabled()
    if blocked:
        return blocked
    try:
        deleted = user_admin.admin_delete_user(user_id)
    except LookupError:
        return api_error('NOT_FOUND', message='用户不存在', status=404)
    except PermissionError:
        return api_error('FORBIDDEN', message_key='common.errors.http403', status=403)
    except ValueError as exc:
        code = str(exc)
        if code == 'cannot_delete_self':
            return api_error(
                'VALIDATION_FAILED',
                message='不能删除当前登录账号',
                message_key='auth.message.cannotDeleteSelf',
                status=400,
            )
        if code == 'last_super_admin':
            return api_error(
                'VALIDATION_FAILED',
                message='至少保留一个超级管理员，不能删除最后一个超级管理员',
                message_key='auth.message.cannotDeleteLastSuperAdmin',
                status=400,
            )
        return _validation_failed_response()

    from services.auth_audit import EVENT_USER_DELETED, log_auth_event
    from services.auth_service import current_user

    actor = current_user()
    log_auth_event(
        EVENT_USER_DELETED,
        actor_user_id=actor.get('id') if actor else None,
        target_user_id=deleted['id'],
        username=deleted['username'],
        ip_address=_client_ip_key(),
        detail=f"role={deleted['role']}",
    )
    return api_success({'deleted_user_id': deleted['id']})


@auth_bp.post('/users/<int:user_id>/unlock')
@admin_or_above
def admin_unlock_user_account(user_id: int):
    blocked = _admin_disabled()
    if blocked:
        return blocked
    from services.auth_service import current_user

    if current_user().get('role') != 'super_admin':
        return api_error('FORBIDDEN', message_key='common.errors.http403', status=403)
    try:
        user = user_admin.admin_unlock_user(user_id)
    except LookupError:
        return api_error('NOT_FOUND', message='用户不存在', status=404)
    except PermissionError:
        return api_error('FORBIDDEN', message_key='common.errors.http403', status=403)
    from services.auth_audit import EVENT_ACCOUNT_UNLOCKED, log_auth_event

    actor = current_user()
    log_auth_event(
        EVENT_ACCOUNT_UNLOCKED,
        actor_user_id=actor.get('id') if actor else None,
        target_user_id=user.id,
        username=user.username,
        ip_address=_client_ip_key(),
    )
    return api_success({'user': user.to_public_dict(include_lock_state=True)})


@auth_bp.get('/audit-logs')
@admin_or_above
def list_auth_audit_logs_route():
    blocked = _admin_disabled()
    if blocked:
        return blocked
    from services.auth_service import current_user

    if current_user().get('role') != 'super_admin':
        return api_error('FORBIDDEN', message_key='common.errors.http403', status=403)
    from flask import request

    from services.auth_audit import list_auth_audit_logs, list_auth_audit_logs_page

    page = request.args.get('page', type=int)
    if page is not None:
        per_page = min(max(1, request.args.get('per_page', 20, type=int) or 20), 100)
        return api_success(list_auth_audit_logs_page(page=page, per_page=per_page))

    limit = min(max(1, request.args.get('limit', 100, type=int) or 100), 500)
    offset = max(0, request.args.get('offset', 0, type=int) or 0)
    return api_success({'logs': list_auth_audit_logs(limit=limit, offset=offset)})


@auth_bp.post('/change-password')
@login_required
def change_password():
    blocked = _admin_disabled()
    if blocked:
        return blocked
    from services.request_rate_limit import sliding_window_allow

    actor = current_user()
    if not sliding_window_allow(
        f"change-password:{actor.get('id') if actor else _client_ip_key()}",
        max_calls=_LOGIN_RATE_MAX,
        window_seconds=_LOGIN_RATE_WINDOW_SECONDS,
    ):
        return api_error(
            'TOO_MANY_REQUESTS',
            message='操作过于频繁，请稍后再试',
            message_key='auth.message.loginRateLimited',
            status=429,
        )
    body = _body()
    try:
        user_admin.change_own_password(
            str(body.get('old_password', '')),
            str(body.get('new_password', '')),
        )
    except ValueError as exc:
        if str(exc) == 'bad_old_password':
            return api_error('UNAUTHORIZED', message='原密码错误', status=401)
        if str(exc) == 'same_password':
            return api_error(
                'VALIDATION_FAILED',
                message='新密码不能与原密码相同',
                message_key='auth.message.samePassword',
                status=400,
            )
        return api_error('VALIDATION_FAILED', message_key='auth.message.weakCredentials', status=400)
    from services.auth_audit import EVENT_PASSWORD_CHANGED, log_auth_event

    actor = current_user()
    log_auth_event(
        EVENT_PASSWORD_CHANGED,
        actor_user_id=actor.get('id') if actor else None,
        username=actor.get('username') if actor else None,
        ip_address=_client_ip_key(),
    )
    revoke_request_sessions()
    return api_success({'message': '密码已修改，请重新登录'})
