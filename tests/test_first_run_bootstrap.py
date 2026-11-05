#!/usr/bin/python
# -*- coding: utf-8 -*-
"""首次初始化游标：只在没有游标时写入，再次启动不得改已有数据。"""

from __future__ import annotations

import inspect

from flask import Flask

from models.auth_models import BootstrapMarker, User
from models.config_models import ConfigItem
from models.models import db
from services.auth_migrations import run_auth_migrations
from services.auth_service import verify_password
from services.first_run_bootstrap import first_run_completed, run_first_run_bootstrap
import services.first_run_bootstrap as first_run_module


def _make_app(tmp_path, name: str) -> Flask:
    app = Flask(name)
    app.config.update(
        TESTING=True,
        SECRET_KEY='first-run-bootstrap',
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{tmp_path / name}.db',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(app)
    return app


def _prepare(app: Flask) -> None:
    with app.app_context():
        db.create_all()
        run_auth_migrations()


def test_module_does_not_wipe_vector_or_force_config():
    source = inspect.getsource(first_run_module.run_first_run_bootstrap)
    assert 'clear_vector_db' not in source
    assert 'init-vector-db' not in source
    assert 'force' not in source


def test_first_run_creates_three_roles_and_config(tmp_path, monkeypatch):
    monkeypatch.setenv('AUTH_BOOTSTRAP_SUPER_PASSWORD', '')
    monkeypatch.setenv('AUTH_BOOTSTRAP_ADMIN_PASSWORD', '')
    monkeypatch.setenv('AUTH_BOOTSTRAP_USER_PASSWORD', '')
    monkeypatch.setenv('DEFAULT_COMPANY', 'QWEN')
    app = _make_app(tmp_path, 'fresh')
    _prepare(app)

    with app.app_context():
        assert run_first_run_bootstrap() == 'completed'
        roles = {user.username: user.role for user in User.query.all()}
        assert roles == {
            'admin': 'super_admin',
            'manager': 'admin',
            'member': 'user',
        }
        for user in User.query.all():
            assert verify_password(user.password_hash, user.salt, 'TestPilot@2026')
        company = ConfigItem.query.filter_by(key='DEFAULT_COMPANY').one()
        assert company.value == 'QWEN'
        assert ConfigItem.query.count() > 10
        assert first_run_completed()


def test_second_run_keeps_password_config_and_deleted_key(tmp_path, monkeypatch):
    monkeypatch.setenv('AUTH_BOOTSTRAP_SUPER_PASSWORD', 'Custom#2026')
    monkeypatch.setenv('DEFAULT_COMPANY', 'QWEN')
    app = _make_app(tmp_path, 'second')
    _prepare(app)

    with app.app_context():
        assert run_first_run_bootstrap() == 'completed'
        manager = User.query.filter_by(username='manager').one()
        password_hash = manager.password_hash
        company = ConfigItem.query.filter_by(key='DEFAULT_COMPANY').one()
        company.value = 'ANTHROPIC'
        chunk = ConfigItem.query.filter_by(key='CHUNK_SIZE').one()
        db.session.delete(chunk)
        db.session.commit()
        user_count = User.query.count()
        config_count = ConfigItem.query.count()

        assert run_first_run_bootstrap() == 'skipped'

        manager = User.query.filter_by(username='manager').one()
        assert manager.password_hash == password_hash
        assert verify_password(manager.password_hash, manager.salt, 'Custom#2026')
        assert ConfigItem.query.filter_by(key='DEFAULT_COMPANY').one().value == 'ANTHROPIC'
        assert ConfigItem.query.filter_by(key='CHUNK_SIZE').first() is None
        assert User.query.count() == user_count
        assert ConfigItem.query.count() == config_count


def test_marker_blocks_recreate_after_accounts_removed(tmp_path, monkeypatch):
    monkeypatch.setenv('AUTH_BOOTSTRAP_SUPER_PASSWORD', 'Custom#2026')
    monkeypatch.setenv('DEFAULT_COMPANY', 'QWEN')
    app = _make_app(tmp_path, 'removed')
    _prepare(app)

    with app.app_context():
        assert run_first_run_bootstrap() == 'completed'
        User.query.delete()
        db.session.commit()
        assert User.query.count() == 0
        assert BootstrapMarker.query.filter_by(marker_key='first_run').count() == 1

        assert run_first_run_bootstrap() == 'skipped'
        assert User.query.count() == 0
        assert ConfigItem.query.filter_by(key='DEFAULT_COMPANY').one().value == 'QWEN'


def test_missing_marker_adds_only_absent_accounts_without_reset(tmp_path, monkeypatch):
    monkeypatch.setenv('AUTH_BOOTSTRAP_SUPER_PASSWORD', 'Custom#2026')
    monkeypatch.setenv('DEFAULT_COMPANY', 'QWEN')
    app = _make_app(tmp_path, 'partial')

    with app.app_context():
        db.create_all()
        from services.auth_migrations import get_default_department_id
        from services.auth_service import create_user

        dept_id = get_default_department_id()
        create_user(
            username='admin',
            password='Already#2026',
            role='super_admin',
            dept_id=dept_id,
        )
        original = User.query.filter_by(username='admin').one().password_hash

        assert run_first_run_bootstrap() == 'completed'
        admin = User.query.filter_by(username='admin').one()
        assert admin.password_hash == original
        assert verify_password(admin.password_hash, admin.salt, 'Already#2026')
        assert User.query.filter_by(username='manager', role='admin').count() == 1
        assert User.query.filter_by(username='member', role='user').count() == 1

        User.query.filter_by(username='member').delete()
        db.session.commit()
        assert run_first_run_bootstrap() == 'skipped'
        assert User.query.filter_by(username='member').count() == 0
