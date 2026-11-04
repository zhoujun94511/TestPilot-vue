#!/usr/bin/python
# -*- coding: utf-8 -*-
"""轻量 RBAC 集成测：仅 auth / cases / export，不加载 chat LLM 栈。"""

from __future__ import annotations

import pytest

pytest.importorskip('flask_session')


@pytest.fixture()
def rbac_app(tmp_path, monkeypatch):
    monkeypatch.setenv('AUTH_BOOTSTRAP_SUPER_PASSWORD', 'TestPilot@2026')
    from config.settings import settings

    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', True)
    monkeypatch.setattr(settings, 'AUTH_REGISTER_ENABLED', False)

    from flask import Flask
    from flask_session import Session

    from blueprints.auth import auth_bp
    from blueprints.cases import cases_bp
    from blueprints.export import export_bp
    from blueprints.stats import stats_bp
    from models.auth_models import Department
    from models.models import TestCase, db
    from services.auth_gate import install_auth_gate
    from services.auth_migrations import get_default_department_id, run_auth_migrations
    from services.auth_service import create_user
    from services.request_rate_limit import reset_rate_limits

    reset_rate_limits()

    db_path = tmp_path / 'rbac_integration_light.db'
    session_dir = tmp_path / 'sessions'
    session_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY='rbac-integration-light',
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{db_path}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_TYPE='filesystem',
        SESSION_FILE_DIR=str(session_dir),
    )
    db.init_app(app)
    Session(app)

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(cases_bp, url_prefix='/api/cases')
    app.register_blueprint(export_bp, url_prefix='/api/export')
    app.register_blueprint(stats_bp, url_prefix='/api/stats')
    install_auth_gate(app)

    with app.app_context():
        db.create_all()
        run_auth_migrations()

        dept_a = get_default_department_id()
        dept_b = Department(code='dept_b', name='部门B', is_active=True)
        db.session.add(dept_b)
        db.session.commit()

        create_user(
            username='admin_a',
            password='AdminA@2026',
            role='admin',
            dept_id=dept_a,
        )
        create_user(
            username='user_a',
            password='UserA@2026',
            role='user',
            dept_id=dept_a,
        )

        db.session.add(
            TestCase(
                case_id='TC-SCOPE-A',
                title='dept A case',
                description='',
                precondition='',
                steps='[]',
                expected_result='[]',
                priority='P2',
                category='functional',
                tags='',
                status='draft',
                created_by='test',
                dept_id=dept_a,
            )
        )
        db.session.add(
            TestCase(
                case_id='TC-SCOPE-B',
                title='dept B case',
                description='',
                precondition='',
                steps='[]',
                expected_result='[]',
                priority='P2',
                category='functional',
                tags='',
                status='draft',
                created_by='test',
                dept_id=dept_b.id,
            )
        )

        db.session.commit()

    return app


def test_dept_admin_cases_list_is_scoped(rbac_app):
    client = rbac_app.test_client()
    assert client.post(
        '/api/auth/login',
        json={'username': 'admin_a', 'password': 'AdminA@2026'},
    ).status_code == 200

    payload = client.get('/api/cases/list').get_json()
    case_ids = {row.get('case_id') for row in payload.get('cases', [])}
    assert 'TC-SCOPE-A' in case_ids
    assert 'TC-SCOPE-B' not in case_ids


def test_dept_admin_cases_stats_is_scoped(rbac_app):
    client = rbac_app.test_client()
    assert client.post(
        '/api/auth/login',
        json={'username': 'admin_a', 'password': 'AdminA@2026'},
    ).status_code == 200

    payload = client.get('/api/cases/stats').get_json()
    stats = payload.get('stats') or {}
    assert stats.get('total_cases') == 1


def test_super_admin_sees_all_department_cases(rbac_app):
    client = rbac_app.test_client()
    assert client.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'TestPilot@2026'},
    ).status_code == 200

    payload = client.get('/api/cases/list').get_json()
    case_ids = {row.get('case_id') for row in payload.get('cases', [])}
    assert {'TC-SCOPE-A', 'TC-SCOPE-B'}.issubset(case_ids)


def test_dept_user_cannot_read_other_department_case(rbac_app):
    client = rbac_app.test_client()
    assert client.post(
        '/api/auth/login',
        json={'username': 'user_a', 'password': 'UserA@2026'},
    ).status_code == 200

    denied = client.get('/api/cases/TC-SCOPE-B')
    assert denied.status_code == 403


def test_dept_admin_gets_limited_stats_health(rbac_app):
    client = rbac_app.test_client()
    assert client.post(
        '/api/auth/login',
        json={'username': 'admin_a', 'password': 'AdminA@2026'},
    ).status_code == 200

    payload = client.get('/api/stats/health').get_json()
    health = payload.get('health') or {}
    assert health.get('limited_visibility') is True


def test_super_admin_gets_full_stats_health(rbac_app):
    client = rbac_app.test_client()
    assert client.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'TestPilot@2026'},
    ).status_code == 200

    payload = client.get('/api/stats/health').get_json()
    health = payload.get('health') or {}
    assert health.get('limited_visibility') is not True


def test_dept_admin_system_status_hides_host_metrics(rbac_app):
    from models.auth_models import Department
    from models.models import RagFileRecord, db
    from services.auth_migrations import get_default_department_id

    with rbac_app.app_context():
        dept_a_id = get_default_department_id()
        dept_b_id = Department.query.filter_by(code='dept_b').first().id
        db.session.add_all([
            RagFileRecord(file_name='a.md', file_path='knowledge/a.md', status='active',
                          ids=str(['a1', 'a2']), dept_id=dept_a_id),
            RagFileRecord(file_name='b.md', file_path='knowledge/b.md', status='active',
                          ids=str(['b1', 'b2', 'b3']), dept_id=dept_b_id),
        ])
        db.session.commit()

    client = rbac_app.test_client()
    assert client.post(
        '/api/auth/login',
        json={'username': 'admin_a', 'password': 'AdminA@2026'},
    ).status_code == 200

    system = client.get('/api/stats/system-status').get_json()['system']
    performance = system['performance']
    assert performance['limited_visibility'] is True
    assert performance['status'] == 'limited'
    assert performance['cpu'] is None and performance['memory_total'] is None
    assert system['knowledge']['docs'] == 1
    assert system['knowledge']['vectors'] == 2


def test_dept_user_exports_only_own_cases(rbac_app):
    client = rbac_app.test_client()
    assert client.post(
        '/api/auth/login',
        json={'username': 'user_a', 'password': 'UserA@2026'},
    ).status_code == 200

    exported = client.get('/api/export/cases/json')
    assert exported.status_code == 200
    body = exported.data.decode('utf-8')
    assert 'dept A case' in body
    assert 'dept B case' not in body
    assert 'TC-SCOPE-B' not in body
