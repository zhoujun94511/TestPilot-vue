#!/usr/bin/python
# -*- coding: utf-8 -*-
"""实验工具（追溯、覆盖评审）的数据范围。"""

from flask import Flask

from models.models import Requirement, TestCase as TestCaseModel, db
from services.data_scope import set_g_user_for_tests


def _app(tmp_path):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_path / "tool_scope.db"}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app


def test_trace_matrix_only_counts_own_department(tmp_path, monkeypatch):
    from config.settings import settings
    from experiments.action_runtime.toolkit import tool_trace_matrix

    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', True)
    app = _app(tmp_path)
    with app.app_context():
        db.create_all()
        db.session.add(Requirement(req_id='REQ-MINE', title='mine', content='x', dept_id=1))
        db.session.add(Requirement(req_id='REQ-OTHER', title='other', content='x', dept_id=99))
        db.session.add(TestCaseModel(case_id='TC-OTHER', title='other', steps='[]', dept_id=99))
        db.session.commit()

        set_g_user_for_tests({'id': 1, 'role': 'user', 'dept_id': 1})
        result = tool_trace_matrix()

    assert result['requirement_total'] == 1
    assert result['case_total'] == 0
    assert [row['req_id'] for row in result['requirements_without_cases']] == ['REQ-MINE']


def test_coverage_review_denies_other_department(tmp_path, monkeypatch):
    from config.settings import settings
    from experiments.action_runtime.toolkit import tool_ac_coverage_review

    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', True)
    app = _app(tmp_path)
    with app.app_context():
        db.create_all()
        db.session.add(Requirement(req_id='REQ-OTHER', title='other', content='系统展示搜索结果', dept_id=99))
        db.session.commit()

        set_g_user_for_tests({'id': 1, 'role': 'user', 'dept_id': 1})
        result = tool_ac_coverage_review('REQ-OTHER')

    assert result['success'] is False
    assert result['message'] == '没有权限访问该需求'
    assert result['message_key'] == 'requirement_forbidden'
