#!/usr/bin/python
# -*- coding: utf-8 -*-
"""代码审计后续修复：检索阈值、聊天参数钳制、确认执行抢占、上传提前拒绝、数据归属。"""

from __future__ import annotations

import io
from collections.abc import Buffer
from types import SimpleNamespace
from typing import cast

import pytest
from flask import Flask

from models.models import Requirement, ToolExecutionLog, db
from utils.utils_intelligent_retrieval.smart_retrieval_strategy import (
    RetrievalConfig,
    RetrievalStrategy,
    SmartRetrievalStrategy,
)


class _SemanticOnlyDb:
    """语义检索命中 0.9；关键词检索返回同一段内容但没有关键词命中。"""

    def similarity_search_with_score(self, _query, _k=5, **_kwargs):
        return [(SimpleNamespace(page_content='登录失败三次锁定账号', metadata={'file_id': 1}), 0.9)]

    @staticmethod
    def similarity_search(_query, _k=5, **_kwargs):
        return [SimpleNamespace(page_content='登录失败三次锁定账号', metadata={'file_id': 1})]


def _strategy(threshold=0.7):
    config = RetrievalConfig(score_threshold=threshold, top_k=5, enable_reranking=True)
    strategy = SmartRetrievalStrategy(config)
    strategy._live_score_threshold = lambda: threshold
    return strategy


def test_hybrid_keeps_strong_semantic_hit_above_threshold():
    results = _strategy(0.7).retrieve('锁定', _SemanticOnlyDb(), strategy=RetrievalStrategy.HYBRID)
    assert [item.content for item in results] == ['登录失败三次锁定账号']


def test_caller_threshold_can_relax_global_threshold():
    class _WeakDb(_SemanticOnlyDb):
        def similarity_search_with_score(self, _query, _k=5, **_kwargs):
            return [(SimpleNamespace(page_content='弱相关', metadata={}), 0.5)]

    strategy = _strategy(0.7)
    assert strategy.retrieve('q', _WeakDb(), strategy=RetrievalStrategy.SEMANTIC) == []
    relaxed = strategy.retrieve('q', _WeakDb(), strategy=RetrievalStrategy.SEMANTIC, score_threshold=0.3)
    assert len(relaxed) == 1


@pytest.mark.parametrize(
    'payload, expected',
    [
        ({'max_tokens': 10 ** 9, 'temperature': 9}, (4000, 2.0)),
        ({'settings': {'max_tokens': '128', 'temperature': '0.2'}}, (128, 0.2)),
        ({'max_tokens': 'abc', 'temperature': 'hot'}, (4000, 0.7)),
        ({'max_tokens': -5, 'temperature': -1}, (1, 0.0)),
        ({'max_tokens': True, 'temperature': float('nan')}, (4000, 0.7)),
    ],
)
def test_chat_generation_settings_are_clamped(monkeypatch, payload, expected):
    from blueprints import chat as chat_module

    monkeypatch.setattr(chat_module.config_settings, 'MAX_TOKENS', 4000)
    merged = chat_module._merge_generation_settings(payload)
    assert (merged['max_tokens'], merged['temperature']) == expected


@pytest.fixture()
def memory_app():
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()


def test_confirmation_can_be_claimed_only_once(memory_app):
    from experiments.action_runtime.orchestrator import ExperimentalActionOrchestrator

    db.session.add(ToolExecutionLog(
        execution_id='exec-1',
        session_id='s',
        user_id='1',
        query_text='q',
        intent='i',
        tool_name='rule_skeleton_cases',
        risk_level='medium',
        tool_args='{}',
        status='needs_confirmation',
        success=True,
    ))
    db.session.commit()
    assert ExperimentalActionOrchestrator._claim_for_execution('exec-1') is True
    assert ExperimentalActionOrchestrator._claim_for_execution('exec-1') is False
    assert ToolExecutionLog.query.filter_by(execution_id='exec-1').one().status == 'running'


def _requirement(req_id, req_type):
    return Requirement(req_id=req_id, title=req_id, content='', type=req_type, source_file='doc.md')


def test_comprehensive_replace_keeps_types_whose_analysis_came_back_empty(memory_app, monkeypatch):
    from config.settings import settings
    from services.document_service import DocumentService

    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', False)
    db.session.add_all([
        _requirement('OLD-FUNC', 'functional'),
        _requirement('OLD-POINT', 'test_point'),
        _requirement('OLD-RULE', 'business_rule'),
    ])
    db.session.commit()

    keep = {'functional'}
    with memory_app.test_request_context():
        saved, error = DocumentService._persist_requirement_rows(
            [{'req_id': 'NEW-POINT', 'type': 'test_point'}, {'req_id': 'NEW-RULE', 'type': 'business_rule'}],
            'uploads/documents/doc.md',
            replace_all=True,
            keep_types=keep,
        )
    assert error is None and len(saved) == 2
    remaining = {row.req_id for row in Requirement.query.all()}
    assert remaining == {'OLD-FUNC', 'NEW-POINT', 'NEW-RULE'}


def test_stamp_ownership_takes_department_from_project(memory_app, monkeypatch):
    from models.auth_models import Department, Project
    from services import auth_service, project_service

    dept_a = Department(code='A', name='A', is_active=True)
    dept_b = Department(code='B', name='B', is_active=True)
    db.session.add_all([dept_a, dept_b])
    db.session.commit()
    project_b = Project(name='B 项目', dept_id=dept_b.id)
    db.session.add(project_b)
    db.session.commit()

    monkeypatch.setattr(auth_service, 'current_user', lambda: {'id': 1, 'role': 'super_admin', 'dept_id': dept_a.id})
    monkeypatch.setattr(project_service, 'resolve_current_project_id', lambda: project_b.id)
    record = Requirement(req_id='REQ-STAMP', title='t', content='')
    auth_service.stamp_ownership(record)
    assert record.project_id == project_b.id
    assert record.dept_id == dept_b.id
    assert record.owner_user_id == 1

    from models.models import RagFileRecord

    knowledge = RagFileRecord(file_name='k.md', file_path='knowledge/k.md')
    auth_service.stamp_ownership(knowledge)
    assert knowledge.project_id is None
    assert knowledge.dept_id == dept_a.id


@pytest.fixture()
def full_client(monkeypatch):
    pytest.importorskip('flask_session')
    from app import create_app
    from config.settings import settings

    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', False)
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


def test_http_errors_keep_their_status_code(full_client):
    response = full_client.delete('/api/auth/check-auth')
    assert response.status_code == 405
    assert 'error_type' not in (response.get_json() or {})


def test_document_upload_rejected_by_content_length_before_parsing(full_client, monkeypatch, tmp_path):
    from blueprints import documents as documents_blueprint

    monkeypatch.setattr(documents_blueprint, 'MAX_DOCUMENT_UPLOAD_BYTES', 10)
    monkeypatch.setattr(documents_blueprint, 'MULTIPART_OVERHEAD_BYTES', 0)
    full_client.application.config['UPLOAD_FOLDER'] = str(tmp_path)
    payload = cast(Buffer, bytearray(b'x' * 2048))
    response = full_client.post(
        '/api/documents/upload',
        data={'file': (io.BytesIO(payload), 'big.txt')},
        content_type='multipart/form-data',
    )
    assert response.status_code == 413
    assert response.get_json()['error_code'] == 'FILE_TOO_LARGE'
    assert not (tmp_path / 'documents').exists()
