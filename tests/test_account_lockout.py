#!/usr/bin/python
# -*- coding: utf-8 -*-
"""账户登录失败锁定与审计（轻量）。"""

from __future__ import annotations

import pytest

pytest.importorskip('flask_session')


@pytest.fixture()
def lock_app(tmp_path, monkeypatch):
    monkeypatch.setenv('AUTH_BOOTSTRAP_SUPER_PASSWORD', 'TestPilot@2026')
    from config.settings import settings

    settings.AUTH_REQUIRE_AUTH = True
    settings.AUTH_LOCK_ENABLED = True
    settings.AUTH_LOCK_MAX_FAILURES = 3
    settings.AUTH_LOCK_DURATION_SECONDS = 600
    settings.AUTH_AUDIT_ENABLED = True
    settings.AUTH_PASSWORD_REQUIRE_COMPLEXITY = True

    from flask import Flask
    from flask_session import Session

    from blueprints.auth import auth_bp
    from models.models import db
    from services.auth_gate import install_auth_gate
    from services.auth_migrations import run_auth_migrations
    from services.auth_migrations import get_default_department_id
    from services.auth_service import create_user

    db_path = tmp_path / 'lock_test.db'
    session_dir = tmp_path / 'sessions'
    session_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY='lock-test',
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{db_path}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_TYPE='filesystem',
        SESSION_FILE_DIR=str(session_dir),
    )
    db.init_app(app)
    Session(app)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    install_auth_gate(app)

    with app.app_context():
        db.create_all()
        run_auth_migrations()
        dept_id = get_default_department_id()
        create_user(
            username='lock_user',
            password='LockUser@2026',
            role='user',
            dept_id=dept_id,
        )

    return app


def test_login_username_is_case_insensitive(lock_app):
    resp = lock_app.test_client().post(
        '/api/auth/login',
        json={'username': 'LOCK_USER', 'password': 'LockUser@2026'},
    )
    assert resp.status_code == 200


def test_account_locks_after_repeated_bad_password(lock_app):
    client = lock_app.test_client()
    for _ in range(2):
        resp = client.post(
            '/api/auth/login',
            json={'username': 'lock_user', 'password': 'wrong-password'},
        )
        assert resp.status_code == 401

    third = client.post(
        '/api/auth/login',
        json={'username': 'lock_user', 'password': 'wrong-password'},
    )
    # 密码错误时不提示锁定，避免借锁定提示判断账号是否存在
    assert third.status_code == 401

    locked = client.post(
        '/api/auth/login',
        json={'username': 'lock_user', 'password': 'LockUser@2026'},
    )
    assert locked.status_code == 403
    body = locked.get_json()
    assert body.get('message_key') == 'auth.message.accountLocked'

    with lock_app.app_context():
        from models.auth_models import AuthAuditLog, User

        user = User.query.filter_by(username='lock_user').first()
        assert user is not None
        assert user.locked_until is not None
        assert AuthAuditLog.query.filter_by(event_type='login_locked').count() >= 1
