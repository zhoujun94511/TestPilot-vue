#!/usr/bin/python
# -*- coding: utf-8 -*-
"""项目隔离与同一条用例的保存冲突。"""

from __future__ import annotations

from collections.abc import Buffer
from datetime import datetime, timezone
from typing import cast

import pytest

pytest.importorskip('flask_session')


@pytest.fixture()
def project_app(tmp_path, monkeypatch):
    monkeypatch.setenv('AUTH_BOOTSTRAP_SUPER_PASSWORD', 'TestPilot@2026')
    from config.settings import settings

    settings.AUTH_REQUIRE_AUTH = True
    settings.AUTH_REGISTER_ENABLED = False

    from flask import Flask
    from flask_session import Session

    from blueprints.auth import auth_bp
    from blueprints.cases import cases_bp
    from blueprints.documents import documents_bp
    from blueprints.projects import projects_bp
    from models.auth_models import Project
    from models.models import TestCase, db
    from services.auth_gate import install_auth_gate
    from services.request_rate_limit import reset_rate_limits

    reset_rate_limits()
    from services.auth_migrations import get_default_department_id, run_auth_migrations
    from services.auth_service import create_user
    from services.project_service import backfill_projects

    db_path = tmp_path / 'project_scope.db'
    session_dir = tmp_path / 'sessions'
    session_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY='project-scope',
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{db_path}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_TYPE='filesystem',
        SESSION_FILE_DIR=str(session_dir),
        UPLOAD_FOLDER=str(tmp_path / 'uploads'),
    )
    (tmp_path / 'uploads' / 'documents').mkdir(parents=True)
    db.init_app(app)
    Session(app)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(cases_bp, url_prefix='/api/cases')
    app.register_blueprint(documents_bp, url_prefix='/api/documents')
    app.register_blueprint(projects_bp, url_prefix='/api')
    install_auth_gate(app)

    with app.app_context():
        db.create_all()
        run_auth_migrations()
        dept_id = get_default_department_id()
        create_user(username='editor', password='Editor@2026', role='user', dept_id=dept_id)
        other = Project(name='另一个项目', dept_id=dept_id)
        db.session.add(other)
        db.session.commit()
        default_project_id = Project.query.filter_by(dept_id=dept_id, name='默认项目').first().id
        stamp = datetime(2026, 11, 6, 8, 0, tzinfo=timezone.utc)
        db.session.add(TestCase(
            case_id='TC-DEFAULT',
            title='默认项目用例',
            description='',
            precondition='',
            steps='[]',
            expected_result='[]',
            priority='P2',
            category='functional',
            tags='',
            status='draft',
            created_by='test',
            dept_id=dept_id,
            project_id=default_project_id,
            updated_time=stamp,
        ))
        db.session.add(TestCase(
            case_id='TC-OTHER',
            title='另一个项目用例',
            description='',
            precondition='',
            steps='[]',
            expected_result='[]',
            priority='P2',
            category='functional',
            tags='',
            status='draft',
            created_by='test',
            dept_id=dept_id,
            project_id=other.id,
            updated_time=stamp,
        ))
        db.session.commit()
        backfill_projects()

    return app


def _login(client, username, password):
    response = client.post('/api/auth/login', json={'username': username, 'password': password})
    assert response.status_code == 200
    return response


def test_default_department_has_a_translation_key(project_app):
    from models.auth_models import Department

    with project_app.app_context():
        dept = Department.query.filter_by(code='default').one()
        assert dept.to_dict()['name_key'] == 'admin.users.dept.defaultName'


def test_lists_follow_the_current_project(project_app):
    client = project_app.test_client()
    _login(client, 'admin', 'TestPilot@2026')
    listed = client.get('/api/projects').get_json()['data']
    default_project = next(item for item in listed['projects'] if item['name'] == '默认项目')
    assert default_project['name_key'] == 'common.project.defaultName'
    current = listed['current_project_id']
    other = next(item['id'] for item in listed['projects'] if item['name'] == '另一个项目')

    first = {row['case_id'] for row in client.get('/api/cases/list').get_json()['cases']}
    assert first == {'TC-DEFAULT'}

    switched = client.put('/api/projects/current', json={'project_id': other})
    assert switched.status_code == 200
    assert switched.get_json()['data']['current_project_id'] == other
    assert current != other
    second = {row['case_id'] for row in client.get('/api/cases/list').get_json()['cases']}
    assert second == {'TC-OTHER'}
    hidden = client.get('/api/cases/TC-DEFAULT')
    assert hidden.status_code == 403


def test_member_cannot_create_project(project_app):
    client = project_app.test_client()
    _login(client, 'editor', 'Editor@2026')
    denied = client.post('/api/projects', json={'name': '成员项目'})
    assert denied.status_code == 403


def test_case_update_without_revision_is_rejected(project_app):
    client = project_app.test_client()
    _login(client, 'admin', 'TestPilot@2026')
    missing = client.put('/api/cases/TC-DEFAULT', json={'title': '不带更新时间'})
    assert missing.status_code == 400
    assert missing.get_json().get('message_key') == 'common.conflict.revisionRequired'


def test_deleting_a_document_clears_requirements_in_every_project(project_app):
    from pathlib import Path

    from models.auth_models import Project
    from models.models import Requirement, db

    with project_app.app_context():
        projects = Project.query.order_by(Project.id.asc()).all()
        dept_id = projects[0].dept_id
        db.session.add(Requirement(
            req_id='REQ-A', title='A', content='a', source_file='shared.txt',
            dept_id=dept_id, project_id=projects[0].id,
        ))
        db.session.add(Requirement(
            req_id='REQ-B', title='B', content='b', source_file='shared.txt',
            dept_id=dept_id, project_id=projects[1].id,
        ))
        db.session.commit()
    Path(project_app.config['UPLOAD_FOLDER'], 'documents', 'shared.txt').write_text('shared', encoding='utf-8')

    client = project_app.test_client()
    _login(client, 'admin', 'TestPilot@2026')
    deleted = client.delete('/api/documents/shared.txt')
    assert deleted.status_code == 200
    with project_app.app_context():
        assert Requirement.query.filter_by(source_file='shared.txt').count() == 0


def test_knowledge_is_shared_across_projects_in_the_department(project_app):
    from pathlib import Path

    from flask import jsonify, request
    from models.auth_models import Project
    from models.models import RagFileRecord, db
    from services.knowledge_service import KnowledgeService

    upload = Path(project_app.config['UPLOAD_FOLDER'])
    (upload / 'knowledge').mkdir(parents=True)
    (upload / 'knowledge' / 'alpha.md').write_text('alpha-only-marker', encoding='utf-8')
    (upload / 'knowledge' / 'beta.md').write_text('beta-only-marker', encoding='utf-8')
    with project_app.app_context():
        projects = Project.query.order_by(Project.id.asc()).all()
        dept_id = projects[0].dept_id
        db.session.add(RagFileRecord(
            file_name='alpha.md', file_path='knowledge/alpha.md', status='active',
            dept_id=dept_id, project_id=projects[0].id,
        ))
        db.session.add(RagFileRecord(
            file_name='beta.md', file_path='knowledge/beta.md', status='active',
            dept_id=dept_id, project_id=projects[1].id,
        ))
        db.session.commit()
        current_id = projects[0].id

    @project_app.get('/__match')
    def _match():
        info = KnowledgeService._find_file_by_content(request.args.get('q', ''), app=project_app)
        return jsonify(info)

    client = project_app.test_client()
    _login(client, 'admin', 'TestPilot@2026')
    with client.session_transaction() as sess:
        sess['current_project_id'] = current_id
    other = client.get('/__match?q=beta-only-marker')
    own = client.get('/__match?q=alpha-only-marker')
    assert other.get_json()['file_name'] == 'beta.md'
    assert own.get_json()['file_name'] == 'alpha.md'


def test_requirement_save_round_trip_uses_opened_revision(project_app):
    from models.auth_models import Project
    from models.models import Requirement, db

    with project_app.app_context():
        projects = Project.query.order_by(Project.id.asc()).all()
        stamp = datetime(2026, 11, 6, 8, 0, tzinfo=timezone.utc)
        db.session.add(Requirement(
            req_id='REQ-REV',
            title='原始需求',
            content='原始内容',
            type='functional',
            priority='P2',
            status='active',
            dept_id=projects[0].dept_id,
            project_id=projects[0].id,
            updated_time=stamp,
        ))
        db.session.add(Requirement(
            req_id='REQ-OTHER',
            title='另一个项目的需求',
            content='其他内容',
            type='functional',
            priority='P2',
            status='active',
            dept_id=projects[1].dept_id,
            project_id=projects[1].id,
            updated_time=stamp,
        ))
        db.session.commit()
        other_project_id = projects[1].id

    first = project_app.test_client()
    second = project_app.test_client()
    _login(first, 'admin', 'TestPilot@2026')
    _login(second, 'editor', 'Editor@2026')

    listed = first.get('/api/documents/requirements').get_json()
    visible_ids = {row['req_id'] for row in listed['requirements']}
    assert visible_ids == {'REQ-REV'}
    assert listed['requirements'][0]['updated_time']

    opened = first.get('/api/documents/requirements/REQ-REV').get_json()
    assert 'data' not in opened
    requirement = opened['requirement']
    stale = requirement['updated_time']
    assert stale
    assert requirement['title'] == '原始需求'

    missing = first.put('/api/documents/requirements/REQ-REV', json={
        'title': '不带更新时间',
        'content': '原始内容',
        'type': 'functional',
        'priority': 'P2',
        'status': 'active',
    })
    assert missing.status_code == 400
    assert missing.get_json().get('message_key') == 'common.conflict.revisionRequired'

    saved = second.put('/api/documents/requirements/REQ-REV', json={
        'title': '编辑者已保存',
        'content': '新内容',
        'type': 'functional',
        'priority': 'P2',
        'status': 'active',
        'updated_time': stale,
    })
    assert saved.status_code == 200
    assert saved.get_json()['requirement']['title'] == '编辑者已保存'
    assert saved.get_json()['requirement']['updated_time'] != stale

    conflict = first.put('/api/documents/requirements/REQ-REV', json={
        'title': '过期保存',
        'content': '原始内容',
        'type': 'functional',
        'priority': 'P2',
        'status': 'active',
        'updated_time': stale,
    })
    assert conflict.status_code == 409
    assert conflict.get_json().get('message') == 'Request failed'
    assert conflict.get_json().get('message_key') == 'common.conflict.stale'

    fresh_body = first.get('/api/documents/requirements/REQ-REV').get_json()['requirement']
    retry = first.put('/api/documents/requirements/REQ-REV', json={
        'title': '重新打开后保存',
        'content': fresh_body['content'],
        'type': fresh_body['type'],
        'priority': fresh_body['priority'],
        'status': fresh_body['status'],
        'updated_time': fresh_body['updated_time'],
    })
    assert retry.status_code == 200
    assert retry.get_json()['requirement']['title'] == '重新打开后保存'

    switched = first.put('/api/projects/current', json={'project_id': other_project_id})
    assert switched.status_code == 200
    hidden = {row['req_id'] for row in first.get('/api/documents/requirements').get_json()['requirements']}
    assert hidden == {'REQ-OTHER'}
    denied = first.put('/api/documents/requirements/REQ-REV', json={
        'title': '跨项目保存',
        'content': '原始内容',
        'updated_time': fresh_body['updated_time'],
    })
    assert denied.status_code == 403


def test_stale_case_update_is_rejected(project_app):
    first = project_app.test_client()
    second = project_app.test_client()
    _login(first, 'admin', 'TestPilot@2026')
    _login(second, 'editor', 'Editor@2026')

    opened = first.get('/api/cases/TC-DEFAULT').get_json()['data']
    stale = opened['updated_time']
    saved = second.put('/api/cases/TC-DEFAULT', json={'title': '编辑者已保存', 'updated_time': stale})
    assert saved.status_code == 200

    conflict = first.put('/api/cases/TC-DEFAULT', json={'title': '过期保存', 'updated_time': stale})
    assert conflict.status_code == 409
    assert conflict.get_json().get('message_key') == 'common.conflict.stale'

    fresh = first.get('/api/cases/TC-DEFAULT').get_json()['data']['updated_time']
    retry = first.put('/api/cases/TC-DEFAULT', json={'title': '重新打开后保存', 'updated_time': fresh})
    assert retry.status_code == 200
    assert retry.get_json()['case']['title'] == '重新打开后保存'


def _project_ids(app):
    from models.auth_models import Project

    with app.app_context():
        rows = Project.query.order_by(Project.id.asc()).all()
        return {row.name: row.id for row in rows}


def _listed_documents(client):
    return {row['filename'] for row in client.get('/api/documents/list').get_json()['documents']}


def test_uploaded_document_belongs_to_the_current_project(project_app):
    import io
    import json
    from pathlib import Path

    ids = _project_ids(project_app)
    client = project_app.test_client()
    _login(client, 'admin', 'TestPilot@2026')
    uploaded = client.post(
        '/api/documents/upload',
        data={'file': (io.BytesIO(cast(Buffer, bytearray(b'login spec'))), 'spec.txt')},
        content_type='multipart/form-data',
    )
    assert uploaded.status_code == 200
    stored = uploaded.get_json()['data']['filename']
    meta_path = Path(project_app.config['UPLOAD_FOLDER'], 'documents', f'{stored}.meta.json')
    assert json.loads(meta_path.read_text(encoding='utf-8'))['project_id'] == ids['默认项目']
    assert stored in _listed_documents(client)

    client.put('/api/projects/current', json={'project_id': ids['另一个项目']})
    assert stored not in _listed_documents(client)
    assert client.get(f'/api/documents/{stored}/preview').status_code == 403


def test_legacy_document_follows_its_requirements_project(project_app):
    import json
    from pathlib import Path

    from models.auth_models import Project
    from models.models import Requirement, db
    from services.project_service import backfill_document_projects

    ids = _project_ids(project_app)
    doc = Path(project_app.config['UPLOAD_FOLDER'], 'documents', 'legacy.txt')
    doc.write_text('legacy', encoding='utf-8')
    with project_app.app_context():
        dept_id = db.session.get(Project, ids['另一个项目']).dept_id
        db.session.add(Requirement(
            req_id='REQ-LEGACY', title='历史', content='x', source_file='legacy.txt',
            dept_id=dept_id, project_id=ids['另一个项目'],
        ))
        db.session.commit()
        backfill_document_projects()
    meta = json.loads(Path(f'{doc}.meta.json').read_text(encoding='utf-8'))
    assert meta['project_id'] == ids['另一个项目']

    client = project_app.test_client()
    _login(client, 'admin', 'TestPilot@2026')
    assert 'legacy.txt' not in _listed_documents(client)
    client.put('/api/projects/current', json={'project_id': ids['另一个项目']})
    assert 'legacy.txt' in _listed_documents(client)


def test_project_header_scopes_each_tab_separately(project_app):
    ids = _project_ids(project_app)
    client = project_app.test_client()
    _login(client, 'admin', 'TestPilot@2026')

    other_tab = client.get('/api/cases/list', headers={'X-Project-Id': str(ids['另一个项目'])})
    assert {row['case_id'] for row in other_tab.get_json()['cases']} == {'TC-OTHER'}
    default_tab = client.get('/api/cases/list', headers={'X-Project-Id': str(ids['默认项目'])})
    assert {row['case_id'] for row in default_tab.get_json()['cases']} == {'TC-DEFAULT'}

    foreign = client.get('/api/cases/list', headers={'X-Project-Id': '99999'})
    assert foreign.status_code == 200
    listed = client.get('/api/projects', headers={'X-Project-Id': '99999'}).get_json()['data']
    assert listed['current_project_id'] in ids.values()


def test_tab_header_does_not_change_the_default_for_new_tabs(project_app):
    ids = _project_ids(project_app)
    client = project_app.test_client()
    _login(client, 'admin', 'TestPilot@2026')
    client.put('/api/projects/current', json={'project_id': ids['默认项目']})

    client.get('/api/cases/list', headers={'X-Project-Id': str(ids['另一个项目'])})
    new_tab = client.get('/api/projects').get_json()['data']
    assert new_tab['current_project_id'] == ids['默认项目']


def test_unassigned_case_only_shows_in_the_default_project(project_app):
    from models.auth_models import Project
    from models.models import TestCase, db

    ids = _project_ids(project_app)
    with project_app.app_context():
        dept_id = db.session.get(Project, ids['默认项目']).dept_id
        db.session.add(TestCase(
            case_id='TC-LOOSE', title='没有项目', description='', precondition='', steps='[]',
            expected_result='[]', priority='P2', category='functional', tags='', status='draft',
            created_by='test', dept_id=dept_id, project_id=None,
        ))
        db.session.commit()

    client = project_app.test_client()
    _login(client, 'admin', 'TestPilot@2026')
    default_cases = {row['case_id'] for row in client.get('/api/cases/list').get_json()['cases']}
    assert 'TC-LOOSE' in default_cases
    assert client.get('/api/cases/TC-LOOSE').status_code == 200

    client.put('/api/projects/current', json={'project_id': ids['另一个项目']})
    other_cases = {row['case_id'] for row in client.get('/api/cases/list').get_json()['cases']}
    assert 'TC-LOOSE' not in other_cases
    assert client.get('/api/cases/TC-LOOSE').status_code == 403


def test_project_rename_and_delete_rules(project_app):
    from models.auth_models import AuthAuditLog

    ids = _project_ids(project_app)
    client = project_app.test_client()
    _login(client, 'admin', 'TestPilot@2026')

    locked = client.patch(f"/api/projects/{ids['默认项目']}", json={'name': '改名'})
    assert locked.status_code == 400
    assert locked.get_json()['message_key'] == 'common.project.defaultLocked'

    renamed = client.patch(f"/api/projects/{ids['另一个项目']}", json={'name': '支付项目'})
    assert renamed.status_code == 200
    assert renamed.get_json()['data']['project']['name'] == '支付项目'

    busy = client.delete(f"/api/projects/{ids['另一个项目']}")
    assert busy.status_code == 409
    assert busy.get_json()['message_key'] == 'common.project.notEmpty'

    created = client.post('/api/projects', json={'name': '临时项目'}).get_json()['data']
    empty_id = created['project']['id']
    usage = {
        row['id']: row['usage']
        for row in client.get('/api/projects?with_usage=1').get_json()['data']['projects']
    }
    assert usage[empty_id] == {'documents': 0, 'requirements': 0, 'cases': 0}
    assert usage[ids['另一个项目']]['cases'] == 1

    removed = client.delete(f'/api/projects/{empty_id}')
    assert removed.status_code == 200
    assert removed.get_json()['data']['current_project_id'] != empty_id

    member = project_app.test_client()
    _login(member, 'editor', 'Editor@2026')
    assert member.patch(f"/api/projects/{ids['另一个项目']}", json={'name': 'x'}).status_code == 403
    assert member.delete(f"/api/projects/{ids['另一个项目']}").status_code == 403

    with project_app.app_context():
        events = {row.event_type for row in AuthAuditLog.query.all()}
    assert {'project_created', 'project_renamed', 'project_deleted'} <= events


def test_delete_still_fails_when_a_case_lands_after_the_empty_check(project_app, monkeypatch):
    from sqlalchemy.exc import IntegrityError

    from models.auth_models import Project
    from models.models import Requirement, TestCase, db
    import services.project_service as project_service

    client = project_app.test_client()
    _login(client, 'admin', 'TestPilot@2026')
    created = client.post('/api/projects', json={'name': '待删除'}).get_json()['data']['project']
    project_id = created['id']
    with project_app.app_context():
        db.session.add(TestCase(
            case_id='TC-LATE',
            title='晚到的用例',
            steps='[]',
            dept_id=created['dept_id'],
            project_id=project_id,
        ))
        db.session.commit()

    # 事先的计数已经过期，删除语句自己仍要发现这条例
    monkeypatch.setattr(
        project_service,
        'project_usage',
        lambda _project_id: {'documents': 0, 'requirements': 0, 'cases': 0},
    )
    denied = client.delete(f'/api/projects/{project_id}')
    assert denied.status_code == 409
    with project_app.app_context():
        assert db.session.get(Project, project_id) is not None

    empty_id = client.post('/api/projects', json={'name': '空项目'}).get_json()['data']['project']['id']
    assert client.delete(f'/api/projects/{empty_id}').status_code == 200
    with project_app.app_context():
        dept_id = created['dept_id']
        db.session.add(TestCase(
            case_id='TC-GHOST',
            title='孤儿用例',
            steps='[]',
            dept_id=dept_id,
            project_id=empty_id,
        ))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        db.session.add(Requirement(
            req_id='REQ-GHOST',
            title='孤儿需求',
            content='迟到的需求',
            dept_id=dept_id,
            project_id=empty_id,
        ))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        assert TestCase.query.filter_by(case_id='TC-GHOST').count() == 0
        assert Requirement.query.filter_by(req_id='REQ-GHOST').count() == 0


def test_document_stamp_drops_a_project_that_was_just_deleted(project_app, monkeypatch):
    import io
    import json
    from pathlib import Path

    client = project_app.test_client()
    _login(client, 'admin', 'TestPilot@2026')
    created = client.post('/api/projects', json={'name': '刚删'}).get_json()['data']['project']
    gone = created['id']
    assert client.delete(f'/api/projects/{gone}').status_code == 200

    class _StaleProject:
        id = gone
        dept_id = created['dept_id']

    monkeypatch.setattr('services.document_meta._upload_project', lambda _user: _StaleProject())
    uploaded = client.post(
        '/api/documents/upload',
        data={'file': (io.BytesIO(cast(Buffer, bytearray(b'late spec'))), 'late.txt')},
        content_type='multipart/form-data',
    )
    assert uploaded.status_code == 200
    stored = uploaded.get_json()['data']['filename']
    meta = json.loads(
        Path(project_app.config['UPLOAD_FOLDER'], 'documents', f'{stored}.meta.json').read_text(encoding='utf-8')
    )
    assert meta.get('project_id') != gone
