#!/usr/bin/python
# -*- coding: utf-8 -*-
"""向量 metadata 回填失败重试与 pending 跟踪。"""

from __future__ import annotations

from types import SimpleNamespace

from flask import Flask

from models.models import RagFileRecord, db
from services import knowledge_vector_scope as kvs


def test_patch_retries_then_clears_pending(tmp_path, monkeypatch):
    monkeypatch.setattr(kvs, '_PATCH_RETRY_ROUNDS', 1)
    kvs._VECTOR_META_PENDING.clear()

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_path / "vec_meta.db"}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    calls = {'n': 0}

    class FakeCollection:
        @staticmethod
        def update(*, ids, metadatas):
            if not ids or not metadatas:
                raise ValueError('expected ids and metadatas')
            calls['n'] += 1
            if calls['n'] == 1:
                raise RuntimeError('transient')

    vector_db = SimpleNamespace(_vector_db=SimpleNamespace(_collection=FakeCollection()))

    with app.app_context():
        db.create_all()
        record = RagFileRecord(
            file_name='demo.md',
            ids="['c1']",
            dept_id=1,
            status='active',
        )
        db.session.add(record)
        db.session.commit()

        assert kvs.patch_vector_metadata_for_record(record, vector_db) is False
        assert record.id in kvs.pending_vector_metadata_file_ids()

        assert kvs.patch_vector_metadata_for_record(record, vector_db) is True
        assert record.id not in kvs.pending_vector_metadata_file_ids()
