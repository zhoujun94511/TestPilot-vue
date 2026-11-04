#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask

from services.chat_mode_guard import is_chat_action_mode, reject_chat_action_mode_response


def test_is_chat_action_mode():
    assert is_chat_action_mode('action') is True
    assert is_chat_action_mode('ACTION') is True
    assert is_chat_action_mode(' chat ') is False
    assert is_chat_action_mode('chat') is False
    assert is_chat_action_mode(None) is False
    assert is_chat_action_mode('') is False


def test_reject_chat_action_mode_response_shape():
    app = Flask(__name__)
    with app.app_context():
        body, status = reject_chat_action_mode_response()
        payload = body.get_json()
    assert status == 400
    assert payload['success'] is False
    assert payload['error'] == 'action_mode_not_supported'
    assert payload['error_code'] == 'ACTION_MODE_NOT_SUPPORTED'
    assert payload['experimental_actions']['execute'] == '/api/experimental-actions/execute'
    assert 'experimental-actions' in payload['message']
