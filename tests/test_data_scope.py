#!/usr/bin/python
# -*- coding: utf-8 -*-
"""data_scope 单元测试（轻量，不加载完整 create_app）。"""

from types import SimpleNamespace

from flask import Flask


def test_null_dept_record_matches_default_department_only(monkeypatch):
    from config.settings import settings
    from services import auth_migrations
    from services.data_scope import can_access_record, set_g_user_for_tests

    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', True)
    monkeypatch.setattr(auth_migrations, 'find_default_department_id', lambda: 1)

    app = Flask(__name__)
    record = SimpleNamespace(dept_id=None)

    with app.app_context():
        set_g_user_for_tests({'id': 10, 'role': 'user', 'dept_id': 2})
        assert can_access_record(record, 'knowledge') is False

        set_g_user_for_tests({'id': 11, 'role': 'user', 'dept_id': 1})
        assert can_access_record(record, 'knowledge') is True

        set_g_user_for_tests({'id': 12, 'role': 'super_admin', 'dept_id': None})
        assert can_access_record(record, 'knowledge') is True


def test_document_filename_meta_ownership(tmp_path, monkeypatch):
    from config.settings import settings
    from services.data_scope import can_access_document_filename, set_g_user_for_tests

    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', True)

    app_root = tmp_path / 'uploads' / 'documents'
    app_root.mkdir(parents=True)
    meta = app_root / 'orphan.pdf.meta.json'
    meta.write_text('{"dept_id": 5, "owner_user_id": 99}', encoding='utf-8')

    app = __import__('flask').Flask(__name__)
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')

    with app.app_context():
        set_g_user_for_tests({'id': 1, 'role': 'user', 'dept_id': 5})
        assert can_access_document_filename('orphan.pdf') is True

        set_g_user_for_tests({'id': 2, 'role': 'user', 'dept_id': 6})
        assert can_access_document_filename('orphan.pdf') is False
