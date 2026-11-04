#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Flask 视图角色与登录装饰器。"""

from __future__ import annotations

import functools
from typing import Callable

from flask import jsonify

from services.auth_service import auth_required, current_user


def _unauthorized():
    return jsonify({
        'success': False,
        'code': 'UNAUTHORIZED',
        'message_key': 'common.errors.http401',
        'message': '未登录或会话已过期',
    }), 401


def _forbidden():
    return jsonify({
        'success': False,
        'code': 'FORBIDDEN',
        'message_key': 'common.errors.http403',
        'message': '没有权限执行此操作',
    }), 403


def login_required(view: Callable):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not auth_required():
            return view(*args, **kwargs)
        if current_user() is None:
            return _unauthorized()
        return view(*args, **kwargs)

    return wrapped


def roles_required(*roles: str):
    allowed = frozenset(roles)

    def decorator(view: Callable):
        @functools.wraps(view)
        def wrapped(*args, **kwargs):
            if not auth_required():
                return view(*args, **kwargs)
            user = current_user()
            if user is None:
                return _unauthorized()
            if user.get('role') not in allowed:
                return _forbidden()
            return view(*args, **kwargs)

        return wrapped

    return decorator


def admin_or_above(view: Callable):
    return roles_required('super_admin', 'admin')(view)
