#!/usr/bin/python
# -*- coding: utf-8 -*-
"""知识库：向量删不掉时保留记录、单文件大小限制、检索单例并发时部门过滤不串。"""

import io
import threading
from collections.abc import Buffer
from types import SimpleNamespace
from typing import cast

import pytest
from flask import Flask

import blueprints.knowledge as knowledge_module
from blueprints.knowledge import knowledge_bp
from config.settings import settings
from models.models import RagFileRecord, db
from utils.utils_intelligent_retrieval.smart_retrieval_strategy import RetrievalStrategy, SmartRetrievalStrategy


class _FailingVectorDb:
    def delete(self, ids):
        raise RuntimeError('vector store down')


class _OkVectorDb:
    def __init__(self):
        self.deleted = []

    def delete(self, ids):
        self.deleted.extend(ids)


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', False)
    monkeypatch.setattr(settings, 'ENABLE_VECTOR_STORE', True)
    knowledge_dir = tmp_path / 'uploads' / 'knowledge'
    knowledge_dir.mkdir(parents=True)
    monkeypatch.setattr(knowledge_module, 'get_knowledge_uploads_path', lambda: knowledge_dir)
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_path / "kb.db"}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    app.config['ALLOWED_EXTENSIONS'] = {'txt', 'md'}
    db.init_app(app)
    app.register_blueprint(knowledge_bp, url_prefix='/api/knowledge')
    with app.app_context():
        db.create_all()
    return app


def _add_record(app, tmp_path, name='a.txt'):
    (tmp_path / 'uploads' / 'knowledge' / name).write_text('x', encoding='utf-8')
    with app.app_context():
        record = RagFileRecord(file_name=name, file_path=f'knowledge/{name}', status='active', ids=str(['v1', 'v2']))
        db.session.add(record)
        db.session.commit()
        return record.id


def test_delete_keeps_record_when_vector_delete_fails(app, tmp_path):
    file_id = _add_record(app, tmp_path)
    app.vector_db = _FailingVectorDb()
    resp = app.test_client().delete(f'/api/knowledge/{file_id}')
    assert resp.status_code == 500
    assert resp.get_json()['error'] == 'vector_delete_failed'
    with app.app_context():
        assert db.session.get(RagFileRecord, file_id) is not None
    assert (tmp_path / 'uploads' / 'knowledge' / 'a.txt').exists()


def test_batch_delete_counts_vector_failures(app, tmp_path):
    file_id = _add_record(app, tmp_path)
    app.vector_db = _FailingVectorDb()
    body = app.test_client().post('/api/knowledge/batch-delete', json={'file_ids': [file_id]}).get_json()
    assert body['deleted_count'] == 0 and body['failed_count'] == 1
    with app.app_context():
        assert db.session.get(RagFileRecord, file_id) is not None


def test_delete_removes_vectors_file_and_record(app, tmp_path):
    file_id = _add_record(app, tmp_path)
    vdb = _OkVectorDb()
    app.vector_db = vdb
    assert app.test_client().delete(f'/api/knowledge/{file_id}').status_code == 200
    assert vdb.deleted == ['v1', 'v2']
    assert not (tmp_path / 'uploads' / 'knowledge' / 'a.txt').exists()
    with app.app_context():
        assert db.session.get(RagFileRecord, file_id) is None


def test_upload_rejects_file_over_single_file_limit(app):
    app.config['MAX_CONTENT_LENGTH'] = 6 * 1024
    payload = cast(Buffer, bytearray(b'x' * 2048))
    data = {'file': (io.BytesIO(payload), 'big.txt')}
    resp = app.test_client().post('/api/knowledge/upload', data=data, content_type='multipart/form-data')
    assert resp.status_code == 413
    assert resp.get_json()['error_code'] == 'FILE_TOO_LARGE'


def test_concurrent_retrievals_keep_their_own_filter_and_top_k():
    strategy = SmartRetrievalStrategy()
    strategy.config.enable_reranking = False
    configured_top_k = strategy.config.top_k
    strategy._live_score_threshold = lambda: 0.0
    barrier = threading.Barrier(2)
    seen = {}

    class _Db:
        def __init__(self, name):
            self.name = name

        def similarity_search_with_score(self, _query, k, **kwargs):
            barrier.wait(timeout=5)
            seen[self.name] = (k, kwargs.get('filter'))
            return [(SimpleNamespace(page_content=f'{self.name}-{i}', metadata={}), 0.9) for i in range(k)]

    def run(name, k, dept):
        strategy.retrieve('q', _Db(name), strategy=RetrievalStrategy.SEMANTIC, top_k=k,
                          vector_search_kwargs={'filter': {'dept_id': dept}})

    threads = [threading.Thread(target=run, args=('a', 2, 1)), threading.Thread(target=run, args=('b', 5, 2))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert seen == {'a': (2, {'dept_id': 1}), 'b': (5, {'dept_id': 2})}
    assert strategy.config.top_k == configured_top_k
