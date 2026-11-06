#!/usr/bin/python
# -*- coding: utf-8 -*-
"""用例导入模板下载文件名后缀回归测试。"""

from __future__ import annotations

import pytest


@pytest.fixture()
def template_client(monkeypatch):
    from flask import Flask

    from blueprints.export import export_bp
    from config.settings import settings

    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', False)
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(export_bp, url_prefix='/api/export')
    return app.test_client()


@pytest.mark.parametrize(
    ('template_type', 'expected_suffix'),
    [
        ('excel', '.xlsx'),
        ('csv', '.csv'),
    ],
)
def test_cases_template_filename_uses_real_extension(template_client, template_type, expected_suffix):
    response = template_client.get(f'/api/export/template/cases?type={template_type}')

    assert response.status_code == 200
    disposition = response.headers.get('Content-Disposition', '')
    assert f'test_cases_template{expected_suffix}' in disposition
    assert '.excel' not in disposition
