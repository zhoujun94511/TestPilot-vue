#!/usr/bin/python
# -*- coding: utf-8 -*-
"""实验动作 health 在开启认证时需登录。"""

from flask import Flask

from blueprints.experimental_actions import experimental_actions_bp
from config.settings import settings


def test_experimental_health_requires_login_when_auth_enabled(monkeypatch):
    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', True)
    monkeypatch.setattr(settings, 'ENABLE_EXPERIMENTAL_ACTIONS', True)

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(experimental_actions_bp)

    client = app.test_client()
    resp = client.get('/api/experimental-actions/health')
    assert resp.status_code == 401
    payload = resp.get_json()
    assert payload.get('error') == 'unauthorized'


def test_experimental_health_open_when_auth_disabled(monkeypatch):
    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', False)
    monkeypatch.setattr(settings, 'ENABLE_EXPERIMENTAL_ACTIONS', True)

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(experimental_actions_bp)

    client = app.test_client()
    resp = client.get('/api/experimental-actions/health')
    assert resp.status_code == 200
