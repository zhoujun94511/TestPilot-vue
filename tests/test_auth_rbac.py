#!/usr/bin/python
# -*- coding: utf-8 -*-
"""认证与配置中心门禁（轻量 Flask，不加载完整 create_app/LLM 栈）。"""

from __future__ import annotations

import pytest

pytest.importorskip('flask_session')


@pytest.fixture()
def auth_app(tmp_path, monkeypatch):
    monkeypatch.setenv('AUTH_BOOTSTRAP_SUPER_PASSWORD', 'TestPilot@2026')
    from config.settings import settings

    settings.AUTH_REQUIRE_AUTH = True
    settings.AUTH_REGISTER_ENABLED = False

    from flask import Flask
    from flask_session import Session

    from blueprints.auth import auth_bp
    from blueprints.cases import cases_bp
    from blueprints.config_center import config_center_bp
    from models.models import db
    from services.auth_gate import install_auth_gate
    from services.auth_migrations import get_default_department_id, run_auth_migrations
    from services.auth_service import create_user

    db_path = tmp_path / 'auth_test.db'
    session_dir = tmp_path / 'sessions'
    session_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY='auth-rbac-light',
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{db_path}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_TYPE='filesystem',
        SESSION_FILE_DIR=str(session_dir),
    )
    db.init_app(app)
    Session(app)

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(cases_bp, url_prefix='/api/cases')
    app.register_blueprint(config_center_bp)
    install_auth_gate(app)

    with app.app_context():
        db.create_all()
        run_auth_migrations()
        dept_id = get_default_department_id()
        create_user(
            username='dept_admin',
            password='DeptAdmin@2026',
            role='admin',
            dept_id=dept_id,
        )

    return app


def test_login_and_check_auth(auth_app):
    client = auth_app.test_client()
    unauth = client.get('/api/cases/list')
    assert unauth.status_code == 401

    login = client.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'TestPilot@2026'},
    )
    assert login.status_code == 200
    payload = login.get_json()
    assert payload.get('success') is True
    assert payload.get('data', {}).get('user', {}).get('role') == 'super_admin'

    ok = client.get('/api/cases/list')
    assert ok.status_code == 200


def test_config_center_forbidden_for_non_super(auth_app):
    client = auth_app.test_client()
    login = client.post(
        '/api/auth/login',
        json={'username': 'dept_admin', 'password': 'DeptAdmin@2026'},
    )
    assert login.status_code == 200

    cfg = client.get('/api/config/categories')
    assert cfg.status_code == 403


def test_admin_reset_password_rejects_short(auth_app):
    from models.auth_models import User

    with auth_app.app_context():
        target = User.query.filter_by(username='dept_admin').first()
        assert target is not None
        user_id = target.id

    client = auth_app.test_client()
    login = client.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'TestPilot@2026'},
    )
    assert login.status_code == 200

    bad = client.put(f'/api/auth/users/{user_id}', json={'password': 'short'})
    assert bad.status_code == 400


def test_super_admin_can_unlock_user(auth_app):
    from models.auth_models import User
    from services.auth_service import register_login_failure

    with auth_app.app_context():
        target = User.query.filter_by(username='dept_admin').first()
        assert target is not None
        user_id = target.id
        for _ in range(5):
            register_login_failure(target)

    client = auth_app.test_client()
    login = client.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'TestPilot@2026'},
    )
    assert login.status_code == 200

    unlock = client.post(f'/api/auth/users/{user_id}/unlock', json={})
    assert unlock.status_code == 200
    payload = unlock.get_json()
    assert payload.get('data', {}).get('user', {}).get('is_locked') is False
