#!/usr/bin/python
# -*- coding: utf-8 -*-
"""注册接口 IP 限流。"""

from __future__ import annotations

import pytest

pytest.importorskip('flask_session')


def test_register_rate_limit_returns_429(tmp_path, monkeypatch):
    monkeypatch.setenv('AUTH_BOOTSTRAP_SUPER_PASSWORD', 'TestPilot@2026')
    from config.settings import settings

    settings.AUTH_REQUIRE_AUTH = True
    settings.AUTH_REGISTER_ENABLED = True

    from flask import Flask
    from flask_session import Session

    from blueprints.auth import auth_bp, _REGISTER_RATE_MAX
    from models.models import db
    from services.auth_migrations import run_auth_migrations
    from services.request_rate_limit import reset_rate_limits

    reset_rate_limits()

    db_path = tmp_path / 'register_rl.db'
    session_dir = tmp_path / 'sessions'
    session_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY='register-rl',
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{db_path}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_TYPE='filesystem',
        SESSION_FILE_DIR=str(session_dir),
    )
    db.init_app(app)
    Session(app)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    with app.app_context():
        db.create_all()
        run_auth_migrations()

    client = app.test_client()
    last_status = 200
    for idx in range(_REGISTER_RATE_MAX + 2):
        resp = client.post(
            '/api/auth/register',
            json={
                'username': f'newuser{idx}',
                'password': 'Password@123',
            },
        )
        last_status = resp.status_code
        if resp.status_code == 429:
            break

    assert last_status == 429
