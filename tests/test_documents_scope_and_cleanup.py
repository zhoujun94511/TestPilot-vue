#!/usr/bin/python
# -*- coding: utf-8 -*-
"""文档删除/预览/需求查询：按文件名精确匹配、删需求时解除用例关联、只能访问 documents 目录下的文档。"""

import pytest
from flask import Flask

from blueprints.documents import documents_bp
from config.settings import settings
from models.models import Requirement, TestCase, db


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', False)
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_path / "docs.db"}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    (tmp_path / 'uploads' / 'documents').mkdir(parents=True)
    (tmp_path / 'uploads' / 'secret.txt').write_text('secret', encoding='utf-8')
    db.init_app(app)
    app.register_blueprint(documents_bp, url_prefix='/api/documents')
    with app.app_context():
        db.create_all()
    return app


def _req(req_id, source):
    return Requirement(req_id=req_id, title=req_id, content='c', type='functional', status='active', source_file=source)


def _case(case_id, req_id):
    return TestCase(case_id=case_id, title=case_id, description='', precondition='', steps='[]',
                    expected_result='[]', priority='P2', category='functional', tags='', status='draft',
                    created_by='t', requirement_id=req_id)


def test_delete_document_only_removes_its_own_requirements_and_unlinks_cases(app, tmp_path):
    docs = tmp_path / 'uploads' / 'documents'
    (docs / 'a.txt').write_text('a', encoding='utf-8')
    (docs / 'a.txt.meta.json').write_text('{}', encoding='utf-8')
    (docs / 'ba.txt').write_text('b', encoding='utf-8')
    with app.app_context():
        db.session.add_all([_req('R_A', 'a.txt'), _req('R_BA', 'ba.txt'), _case('TC_A', 'R_A'), _case('TC_BA', 'R_BA')])
        db.session.commit()

    resp = app.test_client().delete('/api/documents/a.txt')
    assert resp.status_code == 200
    assert not (docs / 'a.txt').exists()
    assert not (docs / 'a.txt.meta.json').exists()
    with app.app_context():
        assert {r.req_id for r in Requirement.query.all()} == {'R_BA'}
        assert TestCase.query.filter_by(case_id='TC_A').first().requirement_id is None
        assert TestCase.query.filter_by(case_id='TC_BA').first().requirement_id == 'R_BA'


def test_delete_requirement_unlinks_cases(app):
    with app.app_context():
        db.session.add_all([_req('R_X', 'x.txt'), _case('TC_X', 'R_X')])
        db.session.commit()
    resp = app.test_client().delete('/api/documents/requirements/R_X')
    assert resp.status_code == 200
    with app.app_context():
        assert Requirement.query.count() == 0
        assert TestCase.query.first().requirement_id is None


def test_requirements_exact_source_does_not_match_similar_names(app):
    with app.app_context():
        db.session.add_all([_req('R_A', 'a.txt'), _req('R_BA', 'ba.txt')])
        db.session.commit()
    client = app.test_client()
    exact = client.get('/api/documents/requirements?source_file=a.txt&exact_source=1').get_json()
    assert [r['req_id'] for r in exact['requirements']] == ['R_A']
    fuzzy = client.get('/api/documents/requirements?source_file=a.txt').get_json()
    assert {r['req_id'] for r in fuzzy['requirements']} == {'R_A', 'R_BA'}


@pytest.mark.parametrize('target', ['a.txt.meta.json', 'missing.txt'])
def test_preview_rejects_meta_and_missing_files(app, tmp_path, target):
    docs = tmp_path / 'uploads' / 'documents'
    (docs / 'a.txt').write_text('a', encoding='utf-8')
    (docs / 'a.txt.meta.json').write_text('{}', encoding='utf-8')
    resp = app.test_client().get(f'/api/documents/{target}/preview')
    assert resp.status_code == 404


@pytest.mark.parametrize('name', ['../secret.txt', '..\\secret.txt', '..', 'sub/a.txt', ''])
def test_document_file_stays_inside_documents_dir(app, tmp_path, name):
    from blueprints.documents import _document_file

    (tmp_path / 'uploads' / 'documents' / 'a.txt').write_text('a', encoding='utf-8')
    with app.app_context():
        assert _document_file(name) is None
        assert _document_file('a.txt') is not None


def test_list_documents_tolerates_zero_per_page(app, tmp_path):
    (tmp_path / 'uploads' / 'documents' / 'a.txt').write_text('a', encoding='utf-8')
    resp = app.test_client().get('/api/documents/list?per_page=0')
    assert resp.status_code == 200
    assert resp.get_json()['total'] == 1
