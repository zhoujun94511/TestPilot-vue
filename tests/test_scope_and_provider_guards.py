#!/usr/bin/python
# -*- coding: utf-8 -*-
"""RAG 结果层部门过滤、文档分析路径限制、Claude 聊天参数裁剪。"""

from types import SimpleNamespace

import pytest
from flask import Flask
from pydantic import SecretStr

from models.models import RagFileRecord, db
from services.data_scope import filter_scoped_retrieval_items, set_g_user_for_tests


def _scope_app(tmp_path):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_path / "scope.db"}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app


def test_rag_items_from_other_department_are_dropped(tmp_path, monkeypatch):
    from config.settings import settings

    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', True)
    app = _scope_app(tmp_path)
    with app.app_context():
        db.create_all()
        mine = RagFileRecord(file_name='mine.md', file_path='k/mine.md', status='active', dept_id=1)
        other = RagFileRecord(file_name='other.md', file_path='k/other.md', status='active', dept_id=99)
        db.session.add_all([mine, other])
        db.session.commit()

        items = [
            SimpleNamespace(metadata={'file_id': mine.id}),
            SimpleNamespace(metadata={'file_id': other.id}),
            SimpleNamespace(metadata={}),
            SimpleNamespace(metadata=None),
        ]
        set_g_user_for_tests({'id': 1, 'role': 'user', 'dept_id': 1})
        kept = filter_scoped_retrieval_items(items)

    assert [item.metadata['file_id'] for item in kept] == [mine.id]


def test_chunks_awaiting_file_id_match_by_stored_name(tmp_path, monkeypatch):
    from config.settings import settings

    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', True)
    app = _scope_app(tmp_path)
    with app.app_context():
        db.create_all()
        db.session.add_all([
            RagFileRecord(file_name='需求.md', file_path='knowledge/需求_20261104.md', status='active', dept_id=1),
            RagFileRecord(file_name='other.md', file_path='knowledge/other_20261104.md', status='active', dept_id=99),
        ])
        db.session.commit()

        items = [
            SimpleNamespace(metadata={'source': r'D:\app\uploads\knowledge\需求_20261104.md'}),
            SimpleNamespace(metadata={'file_name': '需求_20261104.md'}),
            SimpleNamespace(metadata={'source': '/srv/uploads/knowledge/other_20261104.md'}),
        ]
        set_g_user_for_tests({'id': 1, 'role': 'user', 'dept_id': 1})
        kept = filter_scoped_retrieval_items(items)

    assert kept == items[:2]


def test_rag_items_untouched_without_auth(monkeypatch):
    from config.settings import settings

    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', False)
    items = [SimpleNamespace(metadata={})]
    assert filter_scoped_retrieval_items(items) == items


@pytest.fixture
def documents_client(monkeypatch):
    pytest.importorskip('flask_session')
    from app import create_app
    from config.settings import settings

    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', False)
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


@pytest.mark.parametrize('file_path', ['../.env', 'documents/../../.env', 'knowledge/x.md'])
def test_analyze_rejects_paths_outside_documents(documents_client, file_path):
    response = documents_client.post('/api/documents/analyze', json={'file_path': file_path})
    assert response.status_code == 400
    assert 'TestPilot-vue' not in response.get_data(as_text=True)


def test_upload_rejects_oversized_file_before_saving(documents_client, monkeypatch, tmp_path):
    from blueprints import documents as documents_blueprint

    monkeypatch.setattr(documents_blueprint, 'MAX_DOCUMENT_UPLOAD_BYTES', 10)
    documents_client.application.config['UPLOAD_FOLDER'] = str(tmp_path)
    payload = tmp_path / 'incoming.txt'
    payload.write_text('x' * 11, encoding='ascii')
    with payload.open('rb') as handle:
        response = documents_client.post(
            '/api/documents/upload',
            data={'file': (handle, 'big.txt')},
            content_type='multipart/form-data',
        )
    assert response.status_code == 413
    assert response.get_json()['error_code'] == 'FILE_TOO_LARGE'
    assert not (tmp_path / 'documents').exists()


def _chat_settings_for(model: str):
    from langchain_anthropic import ChatAnthropic
    from services.chat_service import build_llm_call_settings

    llm = ChatAnthropic.model_validate({
        'api_key': SecretStr('sk-ant-' + ('a' * 24)),
        'model': model,
        'max_tokens': 1000,
        'base_url': 'https://api.anthropic.com',
    })
    return build_llm_call_settings(llm, {'temperature': 0.2})


def test_claude_5_chat_settings_drop_sampling_and_penalties():
    llm_settings = _chat_settings_for('claude-sonnet-5-5')
    for key in ('temperature', 'top_p', 'frequency_penalty', 'presence_penalty'):
        assert key not in llm_settings


def test_openai_style_settings_unchanged():
    from services.chat_service import build_llm_call_settings

    llm = SimpleNamespace(model='deepseek-chat')
    llm_settings = build_llm_call_settings(llm, {'temperature': 0.9, 'max_tokens': 512})
    assert llm_settings == {
        'max_tokens': 512,
        'top_p': 1.0,
        'frequency_penalty': 0.0,
        'presence_penalty': 0.0,
        'temperature': 0.3,
    }


def test_older_claude_keeps_sampling_but_drops_penalties():
    llm_settings = _chat_settings_for('claude-3-haiku-20240307')
    assert llm_settings['temperature'] == 0.2
    assert 'frequency_penalty' not in llm_settings
    assert 'presence_penalty' not in llm_settings
