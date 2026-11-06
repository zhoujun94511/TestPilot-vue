#!/usr/bin/python
# -*- coding: utf-8 -*-
"""聊天会话访问校验（供 chat / export 等蓝图复用）。"""

from __future__ import annotations

from flask import jsonify

from services.data_scope import can_access_record


def session_access_error(chat_session):
    if chat_session is None or getattr(chat_session, 'is_deleted', False):
        return jsonify({'success': False, 'message': '会话不存在'}), 404
    if not can_access_record(chat_session, 'chat'):
        return jsonify({
            'success': False,
            'message': '没有权限访问该会话',
            'message_key': 'common.errors.http403',
        }), 403
    return None
