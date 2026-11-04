#!/usr/bin/python
# -*- coding: utf-8 -*-
"""自助注册、审核启用、账号规则与超管保护（轻量 Flask）。"""

from __future__ import annotations

import pytest

pytest.importorskip('flask_session')

SUPER_PASSWORD = 'TestPilot@2026'
USER_PASSWORD = 'Password@123'


@pytest.fixture()
def reg_app(tmp_path, monkeypatch):
    monkeypatch.setenv('AUTH_BOOTSTRAP_SUPER_PASSWORD', SUPER_PASSWORD)
    from config.settings import settings

    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', True, raising=False)
    monkeypatch.setattr(settings, 'AUTH_REGISTER_ENABLED', True, raising=False)
    monkeypatch.setattr(settings, 'AUTH_REGISTER_REQUIRE_APPROVAL', True, raising=False)
    monkeypatch.setattr(settings, 'AUTH_TRUST_PROXY_HEADERS', False, raising=False)
    monkeypatch.setattr(settings, 'AUTH_PASSWORD_REQUIRE_COMPLEXITY', True, raising=False)

    from flask import Flask
    from flask_session import Session

    from blueprints.auth import auth_bp
    from blueprints.export import export_bp
    from models.models import db
    from services.auth_gate import install_auth_gate
    from services.request_rate_limit import reset_rate_limits
    from services.auth_migrations import run_auth_migrations

    reset_rate_limits()

    session_dir = tmp_path / 'sessions'
    session_dir.mkdir(parents=True, exist_ok=True)
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY='register-flow',
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path / 'register_flow.db'}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_TYPE='filesystem',
        SESSION_FILE_DIR=str(session_dir),
    )
    db.init_app(app)
    Session(app)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(export_bp, url_prefix='/api/export')
    install_auth_gate(app)

    with app.app_context():
        db.create_all()
        run_auth_migrations()
    yield app
    reset_rate_limits()


def _login(client, username, password):
    return client.post('/api/auth/login', json={'username': username, 'password': password})


def _register(client, username, password=USER_PASSWORD, **extra):
    return client.post('/api/auth/register', json={'username': username, 'password': password, **extra})


def _user_id(app, username):
    from models.auth_models import User

    with app.app_context():
        return User.query.filter_by(username=username).first().id


def test_register_disabled_returns_403(reg_app, monkeypatch):
    from config.settings import settings

    monkeypatch.setattr(settings, 'AUTH_REGISTER_ENABLED', False, raising=False)
    resp = _register(reg_app.test_client(), 'alice')
    assert resp.status_code == 403
    assert resp.get_json()['message_key'] == 'auth.message.registerDisabled'


def test_register_pending_until_admin_enables(reg_app):
    from models.auth_models import AuthAuditLog, User

    client = reg_app.test_client()
    resp = _register(client, 'alice', role='super_admin')
    assert resp.status_code == 200
    assert resp.get_json()['data']['pending_approval'] is True

    with reg_app.app_context():
        user = User.query.filter_by(username='alice').first()
        assert user.role == 'user'
        assert user.is_active is False
        log = AuthAuditLog.query.filter_by(event_type='user_registered').first()
        assert log is not None and log.detail == 'pending_approval'

    wrong = _login(client, 'alice', 'Wrong@1234')
    assert wrong.status_code == 401
    inactive = _login(client, 'alice', USER_PASSWORD)
    assert inactive.status_code == 403
    assert inactive.get_json()['message_key'] == 'auth.message.accountInactive'

    admin = reg_app.test_client()
    assert _login(admin, 'admin', SUPER_PASSWORD).status_code == 200
    enable = admin.put(f"/api/auth/users/{_user_id(reg_app, 'alice')}", json={'is_active': True})
    assert enable.status_code == 200

    ok = _login(client, 'alice', USER_PASSWORD)
    assert ok.status_code == 200
    assert ok.get_json()['data']['user']['role'] == 'user'


def test_register_without_approval_is_active(reg_app, monkeypatch):
    from config.settings import settings

    monkeypatch.setattr(settings, 'AUTH_REGISTER_REQUIRE_APPROVAL', False, raising=False)
    client = reg_app.test_client()
    resp = _register(client, 'bob')
    assert resp.status_code == 200
    assert resp.get_json()['data']['pending_approval'] is False
    assert _login(client, 'bob', USER_PASSWORD).status_code == 200


def test_register_rejects_case_insensitive_duplicates(reg_app):
    client = reg_app.test_client()
    assert _register(client, 'ADMIN').status_code == 409
    assert _register(client, 'carol', email='Carol@Example.com').status_code == 200
    assert _register(client, 'Carol').status_code == 409
    assert _register(client, 'dave', email='carol@example.com').status_code == 409


def test_register_rejects_bad_username_and_email(reg_app):
    client = reg_app.test_client()
    assert _register(client, 'bad name').status_code == 400
    bad_email = _register(client, 'erin', email='not-an-email')
    assert bad_email.status_code == 400
    assert bad_email.get_json()['message_key'] == 'auth.message.invalidEmail'


def test_spoofed_forwarded_for_does_not_bypass_rate_limit(reg_app):
    from blueprints.auth import _REGISTER_RATE_MAX

    client = reg_app.test_client()
    statuses = []
    for idx in range(_REGISTER_RATE_MAX + 2):
        resp = client.post(
            '/api/auth/register',
            json={'username': f'spoof{idx}', 'password': USER_PASSWORD},
            headers={'X-Forwarded-For': f'10.0.0.{idx}'},
        )
        statuses.append(resp.status_code)
    assert 429 in statuses


def test_last_super_admin_cannot_be_demoted_or_disabled(reg_app):
    from models.models import db
    from services.auth_service import create_user

    client = reg_app.test_client()
    assert _login(client, 'admin', SUPER_PASSWORD).status_code == 200
    admin_id = _user_id(reg_app, 'admin')

    demote = client.put(f'/api/auth/users/{admin_id}', json={'role': 'user'})
    assert demote.status_code == 400
    assert demote.get_json()['message_key'] == 'auth.message.lastSuperAdmin'

    with reg_app.app_context():
        create_user(username='root2', password=SUPER_PASSWORD, role='super_admin', dept_id=None)
        db.session.commit()
    root2_id = _user_id(reg_app, 'root2')
    assert client.put(f'/api/auth/users/{root2_id}', json={'is_active': False}).status_code == 200
    # root2 已停用，admin 又成了唯一启用的超管
    assert client.put(f'/api/auth/users/{admin_id}', json={'role': 'admin'}).status_code == 400


def test_delete_user_keeps_last_super_admin(reg_app):
    from models.auth_models import User
    from models.models import db
    from services.auth_service import create_user

    client = reg_app.test_client()
    assert _register(client, 'carol').status_code == 200
    carol_id = _user_id(reg_app, 'carol')
    assert _login(client, 'admin', SUPER_PASSWORD).status_code == 200
    admin_id = _user_id(reg_app, 'admin')

    blocked = client.delete(f'/api/auth/users/{admin_id}')
    assert blocked.status_code == 400
    assert blocked.get_json()['message_key'] == 'auth.message.cannotDeleteLastSuperAdmin'
    with reg_app.app_context():
        assert User.query.get(admin_id) is not None

    deleted = client.delete(f'/api/auth/users/{carol_id}')
    assert deleted.status_code == 200
    with reg_app.app_context():
        assert User.query.get(carol_id) is None

    with reg_app.app_context():
        create_user(username='root2', password=SUPER_PASSWORD, role='super_admin', dept_id=None)
        db.session.commit()
    root2_id = _user_id(reg_app, 'root2')
    assert client.delete(f'/api/auth/users/{root2_id}').status_code == 200
    still_self = client.delete(f'/api/auth/users/{admin_id}')
    assert still_self.status_code == 400
    assert still_self.get_json()['message_key'] == 'auth.message.cannotDeleteLastSuperAdmin'


def test_update_validates_before_writing(reg_app):
    from models.auth_models import User

    client = reg_app.test_client()
    assert _register(client, 'frank').status_code == 200
    frank_id = _user_id(reg_app, 'frank')
    assert _login(client, 'admin', SUPER_PASSWORD).status_code == 200

    bad = client.put(f'/api/auth/users/{frank_id}', json={'is_active': True, 'password': 'short'})
    assert bad.status_code == 400
    with reg_app.app_context():
        assert User.query.get(frank_id).is_active is False

    assert client.put(f'/api/auth/users/{frank_id}', json={'dept_id': 'abc'}).status_code == 400
    assert client.put(f'/api/auth/users/{frank_id}', json={'is_active': 'yes'}).status_code == 400
    assert client.post('/api/auth/users', json={
        'username': 'grace', 'password': USER_PASSWORD, 'dept_id': 'x',
    }).status_code == 400


def test_regular_user_can_export_and_download_template(reg_app, monkeypatch):
    from config.settings import settings

    monkeypatch.setattr(settings, 'AUTH_REGISTER_REQUIRE_APPROVAL', False, raising=False)
    client = reg_app.test_client()
    assert _register(client, 'henry').status_code == 200
    assert _login(client, 'henry', USER_PASSWORD).status_code == 200

    exported = client.get('/api/export/cases/json')
    assert exported.status_code != 403
    assert client.get('/api/export/template/cases?type=csv').status_code != 403


def test_check_auth_exposes_register_policy(reg_app):
    data = reg_app.test_client().get('/api/auth/check-auth').get_json()['data']
    assert data['register_enabled'] is True
    assert data['register_requires_approval'] is True
    assert data['password_complexity_required'] is True
