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
    from services.request_rate_limit import reset_rate_limits

    reset_rate_limits()
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


def test_embedded_client_uses_bearer_without_cookie(auth_app):
    login = auth_app.test_client().post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'TestPilot@2026'},
        headers={'Sec-Fetch-Site': 'cross-site'},
    )
    assert login.status_code == 200
    token = (login.get_json() or {}).get('data', {}).get('session_token')
    assert token

    client = auth_app.test_client()
    assert client.get('/api/cases/list').status_code == 401
    assert client.get(
        '/api/cases/list',
        headers={'Authorization': f'Bearer {token}'},
    ).status_code == 200

    denied = client.post('/api/auth/logout', headers={'Sec-Fetch-Site': 'cross-site'})
    assert denied.status_code == 403

    logged_out = client.post(
        '/api/auth/logout',
        headers={'Authorization': f'Bearer {token}', 'Sec-Fetch-Site': 'cross-site'},
    )
    assert logged_out.status_code == 200
    assert client.get(
        '/api/cases/list',
        headers={'Authorization': f'Bearer {token}'},
    ).status_code == 401


def test_overlapping_logins_keep_one_session(auth_app):
    import threading

    from models.auth_models import User, UserSession
    from models.models import db
    from services.auth_service import create_session

    with auth_app.app_context():
        user_id = User.query.filter_by(username='admin').one().id

    barrier = threading.Barrier(2)
    errors = []

    def enter():
        try:
            with auth_app.app_context():
                barrier.wait(timeout=5)
                create_session(user_id)
                db.session.remove()
        except Exception as exc:  # 后到的事务可能撞上数据库锁，重试一次
            errors.append(exc)
            with auth_app.app_context():
                create_session(user_id)
                db.session.remove()

    threads = [threading.Thread(target=enter) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    with auth_app.app_context():
        assert UserSession.query.filter_by(user_id=user_id).count() == 1


def test_second_login_revokes_the_other_session(auth_app):
    body = {'username': 'admin', 'password': 'TestPilot@2026'}
    first = auth_app.test_client()
    second = auth_app.test_client()

    assert first.post('/api/auth/login', json=body).status_code == 200
    assert first.get('/api/cases/list').status_code == 200

    assert second.post('/api/auth/login', json=body).status_code == 200
    assert second.get('/api/cases/list').status_code == 200
    assert first.get('/api/cases/list').status_code == 401
    still = first.get('/api/auth/check-auth').get_json()
    assert still.get('data', {}).get('authenticated') is False


def test_forced_password_change_accepts_new_password_twice(auth_app):
    from models.auth_models import User
    from models.models import db

    client = auth_app.test_client()
    login = client.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'TestPilot@2026'},
    )
    assert login.status_code == 200
    with auth_app.app_context():
        user = User.query.filter_by(username='admin').first()
        user.must_change_password = True
        db.session.commit()

    missing_old = client.post(
        '/api/auth/change-password',
        json={'new_password': 'FreshKey@2026'},
    )
    assert missing_old.status_code == 200

    relogin = client.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'FreshKey@2026'},
    )
    assert relogin.status_code == 200
    assert relogin.get_json().get('data', {}).get('user', {}).get('must_change_password') is False


def test_voluntary_password_change_still_checks_current_password(auth_app):
    client = auth_app.test_client()
    login = client.post(
        '/api/auth/login',
        json={'username': 'dept_admin', 'password': 'DeptAdmin@2026'},
    )
    assert login.status_code == 200
    rejected = client.post(
        '/api/auth/change-password',
        json={'new_password': 'FreshKey@2026'},
    )
    assert rejected.status_code == 401


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


def test_admin_reset_password_forces_change(auth_app):
    from models.auth_models import User

    with auth_app.app_context():
        user_id = User.query.filter_by(username='dept_admin').first().id

    client = auth_app.test_client()
    assert client.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'TestPilot@2026'},
    ).status_code == 200
    resp = client.put(f'/api/auth/users/{user_id}', json={'password': 'NewPass@2026x'})
    assert resp.status_code == 200
    with auth_app.app_context():
        assert User.query.get(user_id).must_change_password is True


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
