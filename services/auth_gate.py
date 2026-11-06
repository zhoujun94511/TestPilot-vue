#!/usr/bin/python
# -*- coding: utf-8 -*-
"""全局 /api 登录网关（AUTH_REQUIRE_AUTH=true 时生效）。"""

from __future__ import annotations

from flask import Flask, jsonify, request

from services.auth_service import auth_required, current_user

_PUBLIC_API_PATHS = frozenset({
    '/api/auth/login',
    '/api/auth/register',
    '/api/auth/check-auth',
})


_PASSWORD_CHANGE_PATHS = frozenset({
    '/api/auth/change-password',
    '/api/auth/logout',
})


def _cross_site_write() -> bool:
    """浏览器会如实标记跨站请求；跨站来的写操作一律拒绝。"""
    if request.headers.get('Sec-Fetch-Site', '').lower() != 'cross-site':
        return False
    return request.method not in ('GET', 'HEAD')


def install_auth_gate(flask_app: Flask) -> None:
    @flask_app.before_request
    def _auth_gate():
        path = request.path
        if not path.startswith('/api/') or request.method == 'OPTIONS':
            return None
        if _cross_site_write():
            return jsonify({
                'success': False,
                'code': 'FORBIDDEN',
                'message_key': 'common.errors.http403',
                'message': '拒绝跨站请求',
            }), 403
        if not auth_required():
            return None
        if path in _PUBLIC_API_PATHS:
            return None
        user = current_user()
        if user is None:
            return jsonify({
                'success': False,
                'code': 'UNAUTHORIZED',
                'message_key': 'common.errors.http401',
                'message': '未登录或会话已过期',
            }), 401
        if user.get('must_change_password') and path not in _PASSWORD_CHANGE_PATHS:
            return jsonify({
                'success': False,
                'code': 'PASSWORD_CHANGE_REQUIRED',
                'message_key': 'auth.message.passwordChangeRequired',
                'message': '当前账号仍在使用默认密码，请先修改密码',
            }), 403
        return None
