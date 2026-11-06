#!/usr/bin/python
# -*- coding: utf-8 -*-
"""审计修复回归：重建先写后删、部分写入回滚、向量库范围过滤、历史最新页、空用例、LIKE 转义、限流清理。"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from flask import Flask

from config.settings import settings
from models.models import ChatHistory, ChatSession, RagFileRecord, TestCase, db


class _RecordingVectorDb:
    def __init__(self, ids=()):
        self.ids = list(ids)
        self.deleted: list[str] = []

    def delete(self, ids):
        self.deleted.extend(ids)
        self.ids = [i for i in self.ids if i not in set(ids)]

    def get(self):
        return {'ids': list(self.ids)}


@pytest.fixture()
def kb_app(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', False)
    (tmp_path / 'knowledge').mkdir()
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{tmp_path / "kb.db"}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=str(tmp_path),
    )
    db.init_app(app)
    with app.app_context():
        db.create_all()
    return app


def _kb_record(tmp_path, name, ids):
    (tmp_path / 'knowledge' / name).write_text('x', encoding='utf-8')
    record = RagFileRecord(file_name=name, file_path=f'knowledge/{name}', status='active', ids=str(ids))
    db.session.add(record)
    db.session.commit()
    return record


def _service(monkeypatch, outcomes):
    import services.knowledge_vector_scope as scope_module
    from services.knowledge_service import KnowledgeService

    monkeypatch.setattr(scope_module, 'patch_vector_metadata_for_record', lambda *_a, **_k: None)
    service = KnowledgeService()
    calls = iter(outcomes)
    monkeypatch.setattr(service, 'process_knowledge_file', lambda **_kw: next(calls))
    return service


def test_rebuild_writes_new_vectors_before_dropping_old(kb_app, tmp_path, monkeypatch):
    service = _service(monkeypatch, [{'success': True, 'document_ids': ['n1', 'n2']}])
    vdb = _RecordingVectorDb(['o1', 'o2'])
    with kb_app.test_request_context():
        record = _kb_record(tmp_path, 'a.txt', ['o1', 'o2'])
        result = service.rebuild_knowledge_base(vector_db=vdb)
        assert result['success'] is True
        assert result['info']['processed'] == 1
        assert vdb.deleted == ['o1', 'o2']
        assert db.session.get(RagFileRecord, record.id).ids == str(['n1', 'n2'])


def test_rebuild_failure_keeps_old_vectors(kb_app, tmp_path, monkeypatch):
    service = _service(monkeypatch, [{'success': False, 'message': '解析失败'}])
    vdb = _RecordingVectorDb(['o1'])
    with kb_app.test_request_context():
        record = _kb_record(tmp_path, 'a.txt', ['o1'])
        result = service.rebuild_knowledge_base(vector_db=vdb)
        assert result['info']['failed'] == 1
        assert vdb.deleted == []
        assert db.session.get(RagFileRecord, record.id).ids == str(['o1'])


def test_clear_all_rebuild_drops_only_orphans(kb_app, tmp_path, monkeypatch):
    service = _service(monkeypatch, [
        {'success': True, 'document_ids': ['n1']},
        {'success': False, 'message': '解析失败'},
    ])
    vdb = _RecordingVectorDb(['o1', 'o2', 'orphan'])
    with kb_app.test_request_context():
        _kb_record(tmp_path, 'a.txt', ['o1'])
        _kb_record(tmp_path, 'b.txt', ['o2'])
        result = service.rebuild_knowledge_base(vector_db=vdb, clear_all=True)
        assert result['info']['processed'] == 1
        assert sorted(vdb.deleted) == ['o1', 'orphan']


def test_partial_vector_write_is_rolled_back(monkeypatch):
    from services.knowledge_service import KnowledgeService

    service = KnowledgeService()
    vdb = _RecordingVectorDb()
    assert service.discard_vectors(['a', 'b'], vdb) is True
    assert vdb.deleted == ['a', 'b']
    assert service.discard_vectors([], vdb) is True


class _FakeEmbeddings:
    @staticmethod
    def embed_query(_text):
        return [1.0, 0.0, 0.0, 0.0]

    def embed_documents(self, texts):
        return [self.embed_query(t) for t in texts]


def test_sqlite_store_applies_dept_filter_before_ranking(tmp_path, monkeypatch):
    from utils.utils_ai_models.sqlite_vector_store import Document, SQLiteVectorStore

    monkeypatch.setattr(settings, 'EMBEDDING_DIM', 4)
    store = SQLiteVectorStore(db_path=str(tmp_path / 'v.db'), embedding_function=_FakeEmbeddings())
    store.add_documents([
        Document(f'dept1 chunk {i}', metadata={'chunk_id': f'a{i}', 'dept_id': 1, 'file_id': 10}) for i in range(5)
    ] + [Document('dept2 chunk', metadata={'chunk_id': 'b0', 'dept_id': 2, 'file_id': 20})])

    hits = store.similarity_search_with_score('chunk', k=2, filter={'dept_id': {'$in': [2]}})
    assert [doc.metadata.get('dept_id') for doc, _ in hits] == [2]
    assert store.similarity_search_with_score('chunk', k=2, filter={'file_id': {'$in': []}}) == []


def _chat_app(monkeypatch):
    from blueprints.chat import chat_bp

    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', False)
    app = Flask(__name__)
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
                      SQLALCHEMY_TRACK_MODIFICATIONS=False)
    db.init_app(app)
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    with app.app_context():
        db.create_all()
        db.session.add(ChatSession(session_id='s1', title='t'))
        for i in range(5):
            db.session.add(ChatHistory(session_id='s1', role='user', content=f'm{i}'))
        db.session.commit()
    return app


def test_history_last_page_returns_latest_messages(monkeypatch):
    client = _chat_app(monkeypatch).test_client()
    body = client.get('/api/chat/history?session_id=s1&page=last&per_page=2').get_json()
    assert body['pagination']['page'] == 3
    assert [m['content'] for m in body['messages']] == ['m4']


def test_empty_case_generation_is_not_success(monkeypatch):
    from services.case_service import CaseService

    service = CaseService()
    monkeypatch.setattr(service, '_generate_function_cases', lambda **_kw: [])
    monkeypatch.setattr(service, '_apply_hallucination_guard', lambda cases, *_a: (cases, None))
    result = service.generate_cases('需求', llm=object(), start_monitoring=False)
    assert result['success'] is False
    assert result['status_code'] == 422


def test_case_search_treats_percent_literally(monkeypatch):
    from blueprints.cases import cases_bp

    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', False)
    app = Flask(__name__)
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
                      SQLALCHEMY_TRACK_MODIFICATIONS=False)
    db.init_app(app)
    app.register_blueprint(cases_bp, url_prefix='/api/cases')
    with app.app_context():
        db.create_all()
        db.session.add(TestCase(case_id='c1', title='折扣 50% 校验', steps=json.dumps([])))
        db.session.add(TestCase(case_id='c2', title='普通登录', steps=json.dumps([])))
        db.session.commit()
    body = app.test_client().get('/api/cases/list?search=%25').get_json()
    titles = [c['title'] for c in body['cases']]
    assert titles == ['折扣 50% 校验']


def test_rate_limit_table_prunes_idle_keys(monkeypatch):
    import services.request_rate_limit as rl

    rl.reset_rate_limits()
    monkeypatch.setattr(rl, '_PRUNE_THRESHOLD', 3)
    now = [1000.0]
    monkeypatch.setattr(rl, 'time', SimpleNamespace(time=lambda: now[0]))
    for i in range(4):
        assert rl.sliding_window_allow(f'k{i}', max_calls=1, window_seconds=60)
    now[0] += rl._IDLE_SECONDS + 1
    rl.sliding_window_allow('fresh', max_calls=1, window_seconds=60)
    assert set(rl._buckets) == {'fresh'}
    rl.reset_rate_limits()
