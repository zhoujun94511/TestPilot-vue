#!/usr/bin/python
# -*- coding: utf-8 -*-
"""用户与部门管理（super_admin / admin 本部门）。"""

from __future__ import annotations

from typing import Any, List, Optional

from models.auth_models import Department, User, UserSession
from models.models import db
from services.auth_service import (
    VALID_ROLES,
    clear_login_failures,
    create_user,
    current_user,
    find_user_by_email_ci,
    new_password_fields,
    normalize_email,
    revoke_user_sessions,
    validate_password,
    verify_password,
)


def _actor() -> Optional[dict[str, Any]]:
    return current_user()


def can_manage_role(actor_role: str, target_role: str) -> bool:
    if actor_role == 'super_admin':
        return target_role in VALID_ROLES
    if actor_role == 'admin':
        return target_role == 'user'
    return False


def list_departments() -> List[dict]:
    actor = _actor()
    if not actor:
        return []
    if actor.get('role') == 'super_admin':
        rows = Department.query.order_by(Department.id.asc()).all()
        return [d.to_dict() for d in rows]
    dept_id = actor.get('dept_id')
    if dept_id is None:
        return []
    dept = Department.query.get(dept_id)
    return [dept.to_dict()] if dept else []


def create_department(code: str, name: str) -> Department:
    actor = _actor()
    if not actor or actor.get('role') != 'super_admin':
        raise PermissionError('forbidden')
    code_text = (code or '').strip()
    name_text = (name or '').strip()
    if not code_text or not name_text:
        raise ValueError('code_name_required')
    if Department.query.filter_by(code=code_text).first():
        raise ValueError('duplicate_code')
    dept = Department(code=code_text, name=name_text, is_active=True)
    db.session.add(dept)
    db.session.commit()
    return dept


def list_users() -> List[dict]:
    actor = _actor()
    if not actor:
        return []
    query = User.query.order_by(User.id.asc())
    if actor.get('role') == 'admin':
        dept_id = actor.get('dept_id')
        if dept_id is None:
            return []
        query = query.filter(User.dept_id == dept_id, User.role == 'user')
    elif actor.get('role') != 'super_admin':
        return []
    include_lock = actor.get('role') == 'super_admin'
    return [u.to_public_dict(include_lock_state=include_lock) for u in query.all()]


def resolve_create_dept_id(requested_dept_id: Optional[int], role: str) -> Optional[int]:
    actor = _actor()
    if not actor:
        raise PermissionError('forbidden')
    if actor.get('role') == 'super_admin':
        if role == 'super_admin':
            return requested_dept_id
        return requested_dept_id or actor.get('dept_id')
    if actor.get('role') == 'admin':
        return actor.get('dept_id')
    raise PermissionError('forbidden')


def admin_create_user(
    *,
    username: str,
    password: str,
    email: Optional[str],
    role: str,
    dept_id: Optional[int],
) -> User:
    actor = _actor()
    if not actor or actor.get('role') not in ('super_admin', 'admin'):
        raise PermissionError('forbidden')
    role_name = (role or 'user').strip()
    if role_name not in VALID_ROLES:
        raise ValueError('invalid_role')
    if not can_manage_role(actor.get('role', ''), role_name):
        raise PermissionError('forbidden')
    resolved_dept = resolve_create_dept_id(dept_id, role_name)
    if role_name != 'super_admin' and resolved_dept is None:
        raise ValueError('dept_required')
    return create_user(
        username=username,
        password=password,
        email=email,
        role=role_name,
        dept_id=resolved_dept,
    )


def admin_update_user(
    user_id: int,
    *,
    email: Optional[str] = None,
    role: Optional[str] = None,
    dept_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    password: Optional[str] = None,
) -> User:
    actor = _actor()
    if not actor or actor.get('role') not in ('super_admin', 'admin'):
        raise PermissionError('forbidden')

    target = User.query.get(user_id)
    if not target:
        raise LookupError('not_found')

    if actor.get('role') == 'admin':
        if target.dept_id != actor.get('dept_id') or target.role != 'user':
            raise PermissionError('forbidden')

    # 先完成全部校验再改字段，任何一项不通过都不落库
    new_role = None
    if role is not None:
        new_role = role.strip()
        if new_role not in VALID_ROLES:
            raise ValueError('invalid_role')
        if not can_manage_role(actor.get('role', ''), new_role):
            raise PermissionError('forbidden')

    new_email = None
    if email is not None:
        new_email = normalize_email(email)
        if find_user_by_email_ci(new_email, exclude_id=target.id):
            raise ValueError('duplicate_email')

    if is_active is not None and target.id == actor.get('id') and not is_active:
        raise ValueError('cannot_deactivate_self')

    if password:
        validate_password(password)

    loses_super_admin = target.role == 'super_admin' and target.is_active and (
        (new_role is not None and new_role != 'super_admin')
        or (is_active is not None and not is_active)
    )
    if loses_super_admin and _other_active_super_admins(target.id) == 0:
        raise ValueError('last_super_admin')

    revoke = False
    if new_role is not None:
        target.role = new_role
    if dept_id is not None and actor.get('role') == 'super_admin':
        target.dept_id = dept_id
    if email is not None:
        target.email = new_email
    if is_active is not None:
        target.is_active = bool(is_active)
        revoke = revoke or not target.is_active
    if password:
        pwd_hash, salt = new_password_fields(password)
        target.password_hash = pwd_hash
        target.salt = salt
        # 管理员设的密码对方并不私有，下次登录必须自己改掉
        target.must_change_password = target.id != actor.get('id')
        revoke = True

    db.session.commit()
    if revoke:
        revoke_user_sessions(target.id)
    return target


def admin_delete_user(user_id: int) -> dict[str, Any]:
    """删除账号。最后一个超级管理员不能删；其余账号也不能删除自己。业务数据不随账号删除。"""
    actor = _actor()
    if not actor or actor.get('role') not in ('super_admin', 'admin'):
        raise PermissionError('forbidden')

    target = User.query.get(user_id)
    if not target:
        raise LookupError('not_found')

    if actor.get('role') == 'admin':
        if target.dept_id != actor.get('dept_id') or target.role != 'user':
            raise PermissionError('forbidden')

    if target.role == 'super_admin' and _other_super_admins(target.id) == 0:
        raise ValueError('last_super_admin')
    if target.id == actor.get('id'):
        raise ValueError('cannot_delete_self')

    snapshot = {
        'id': target.id,
        'username': target.username,
        'role': target.role,
    }
    UserSession.query.filter_by(user_id=target.id).delete()
    db.session.delete(target)
    db.session.commit()
    return snapshot


def _other_super_admins(exclude_id: int) -> int:
    return User.query.filter(
        User.role == 'super_admin',
        User.id != exclude_id,
    ).count()


def _other_active_super_admins(exclude_id: int) -> int:
    return User.query.filter(
        User.role == 'super_admin',
        User.is_active.is_(True),
        User.id != exclude_id,
    ).count()


def admin_unlock_user(user_id: int) -> User:
    actor = _actor()
    if not actor or actor.get('role') != 'super_admin':
        raise PermissionError('forbidden')
    target = User.query.get(user_id)
    if not target:
        raise LookupError('not_found')
    clear_login_failures(target)
    db.session.commit()
    return target


def change_own_password(old_password: str, new_password: str) -> None:
    actor = _actor()
    if not actor:
        raise PermissionError('forbidden')
    user = User.query.get(actor['id'])
    if not user:
        raise LookupError('not_found')
    forced = bool(user.must_change_password)
    if not forced and not verify_password(user.password_hash, user.salt, old_password):
        raise ValueError('bad_old_password')
    validate_password(new_password)
    if verify_password(user.password_hash, user.salt, new_password) or (
        not forced and new_password == old_password
    ):
        raise ValueError('same_password')
    pwd_hash, salt = new_password_fields(new_password)
    user.password_hash = pwd_hash
    user.salt = salt
    user.must_change_password = False
    db.session.commit()
    revoke_user_sessions(user.id)
