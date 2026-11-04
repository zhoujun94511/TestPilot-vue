#!/usr/bin/python
# -*- coding: utf-8 -*-
"""认证凭据校验（用户名/密码长度）。"""

from __future__ import annotations

import pytest

from services.auth_service import (
    PASSWORD_MAX_LEN,
    PASSWORD_MIN_LEN,
    USERNAME_MIN_LEN,
    validate_password,
    validate_username,
)


def test_validate_username_ok():
    assert validate_username('abc') == 'abc'
    assert validate_username('  admin_x  ') == 'admin_x'


def test_validate_username_too_short():
    with pytest.raises(ValueError, match='weak_username'):
        validate_username('ab')


def test_validate_password_bounds(monkeypatch):
    from config.settings import settings

    settings.AUTH_PASSWORD_REQUIRE_COMPLEXITY = False
    validate_password('a' * PASSWORD_MIN_LEN)
    with pytest.raises(ValueError, match='weak_password'):
        validate_password('a' * (PASSWORD_MIN_LEN - 1))
    with pytest.raises(ValueError, match='password_too_long'):
        validate_password('a' * (PASSWORD_MAX_LEN + 1))


def test_validate_password_complexity():
    from config.settings import settings

    settings.AUTH_PASSWORD_REQUIRE_COMPLEXITY = True
    validate_password('TestPilot@2026')
    with pytest.raises(ValueError, match='password_needs_symbol'):
        validate_password('TestPilot2026')


def test_create_user_rejects_weak_password(tmp_path, monkeypatch):
    pytest.importorskip('flask_session')
    monkeypatch.setenv('AUTH_BOOTSTRAP_SUPER_PASSWORD', 'TestPilot@2026')
    from config.settings import settings

    settings.AUTH_PASSWORD_REQUIRE_COMPLEXITY = False
    from flask import Flask
    from flask_session import Session

    from models.models import db
    from services.auth_migrations import run_auth_migrations
    from services.auth_service import create_user

    db_path = tmp_path / 'pwd_policy.db'
    session_dir = tmp_path / 'sessions'
    session_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY='pwd-policy',
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{db_path}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_TYPE='filesystem',
        SESSION_FILE_DIR=str(session_dir),
    )
    db.init_app(app)
    Session(app)

    with app.app_context():
        db.create_all()
        run_auth_migrations()
        with pytest.raises(ValueError, match='weak_password'):
            create_user(username='x' * USERNAME_MIN_LEN, password='short', role='user', dept_id=1)
