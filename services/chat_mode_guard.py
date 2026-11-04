#!/usr/bin/python
# -*- coding: utf-8 -*-
"""聊天 mode=action 拒绝逻辑（与实验动作通道分离，无 LLM 依赖）。"""

from __future__ import annotations

from typing import Any

from flask import jsonify

_ACTION_MODE_REJECT_MESSAGE = (
    '聊天接口不再支持 mode=action（旧客户端请升级）。'
    '实验工具请调用 POST /api/experimental-actions/execute，'
    'body 中提供 tool_name 与 args；高风险操作使用 /confirm、/cancel。'
)


def is_chat_action_mode(raw_mode: Any) -> bool:
    return str(raw_mode or 'chat').strip().lower() == 'action'


def reject_chat_action_mode_response():
    return jsonify({
        'success': False,
        'message': _ACTION_MODE_REJECT_MESSAGE,
        'error': 'action_mode_not_supported',
        'error_code': 'ACTION_MODE_NOT_SUPPORTED',
        'message_key': 'chat.message.actionModeNotSupported',
        'experimental_actions': {
            'execute': '/api/experimental-actions/execute',
            'health': '/api/experimental-actions/health',
            'confirm': '/api/experimental-actions/confirm',
            'cancel': '/api/experimental-actions/cancel',
        },
    }), 400
