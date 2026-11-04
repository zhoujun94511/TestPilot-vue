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


def install_auth_gate(flask_app: Flask) -> None:
    @flask_app.before_request
    def _auth_gate():
        if not auth_required():
            return None
        path = request.path
        if not path.startswith('/api/') or request.method == 'OPTIONS':
            return None
        if path in _PUBLIC_API_PATHS:
            return None
        if current_user() is None:
            return jsonify({
                'success': False,
                'code': 'UNAUTHORIZED',
                'message_key': 'common.errors.http401',
                'message': '未登录或会话已过期',
            }), 401
        return None
