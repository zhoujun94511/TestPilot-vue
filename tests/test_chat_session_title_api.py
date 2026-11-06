#!/usr/bin/python
# -*- coding: utf-8 -*-
"""会话标题接口：新建不再用首句、重命名锁定、列表优先已保存标题。"""

from __future__ import annotations

import pytest
from flask import Flask

from models.models import ChatHistory, ChatSession, db
from services.chat_session_title import PLACEHOLDER_TITLE, TITLE_SOURCE_MANUAL


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from blueprints.chat import chat_bp
    from config.settings import settings

    monkeypatch.setattr(settings, 'AUTH_REQUIRE_AUTH', False)
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_path / "chat_title_api.db"}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    with app.app_context():
        db.create_all()
        yield app.test_client()


def _list_titles(client):
    payload = client.get('/api/chat/sessions').get_json()
    return {item['session_id']: (item['title'], item['title_source']) for item in payload['sessions']}


def test_create_without_title_is_untitled(client):
    session = client.post('/api/chat/sessions', json={}).get_json()['session']
    assert session['title'] == PLACEHOLDER_TITLE
    assert session['title_source'] is None


def test_rename_locks_title_and_list_keeps_it(client):
    session_id = client.post('/api/chat/sessions', json={}).get_json()['session_id']
    db.session.add(ChatHistory(session_id=session_id, role='user', content='你好'))
    db.session.commit()

    resp = client.put(f'/api/chat/session/{session_id}', json={'title': '  登录需求讨论  '})
    assert resp.get_json()['session']['title_source'] == TITLE_SOURCE_MANUAL

    assert _list_titles(client)[session_id] == ('登录需求讨论', TITLE_SOURCE_MANUAL)

    generated = client.post(f'/api/chat/session/{session_id}/title').get_json()['session']
    assert generated['title'] == '登录需求讨论'
    assert generated['generated'] is False


def test_rename_rejects_blank_title(client):
    session_id = client.post('/api/chat/sessions', json={}).get_json()['session_id']
    resp = client.put(f'/api/chat/session/{session_id}', json={'title': '   '})
    assert resp.status_code == 400


def test_list_hides_greeting_first_message(client):
    session_id = client.post('/api/chat/sessions', json={}).get_json()['session_id']
    db.session.add(ChatHistory(session_id=session_id, role='user', content='你好'))
    db.session.commit()
    assert _list_titles(client)[session_id] == (PLACEHOLDER_TITLE, None)


def test_list_skips_greeting_to_real_question(client):
    session_id = client.post('/api/chat/sessions', json={}).get_json()['session_id']
    for role, content in [('user', '你好'), ('assistant', '你好'), ('user', '帮我设计登录功能测试用例')]:
        db.session.add(ChatHistory(session_id=session_id, role=role, content=content))
    db.session.commit()
    assert _list_titles(client)[session_id] == ('帮我设计登录功能测试用例', None)


def test_title_endpoint_falls_back_without_model(client, monkeypatch):
    session_id = client.post('/api/chat/sessions', json={}).get_json()['session_id']
    db.session.add(ChatHistory(session_id=session_id, role='user', content='帮我写登录用例。顺便看看注册'))
    db.session.add(ChatHistory(session_id=session_id, role='assistant', content='好的'))
    db.session.commit()

    from blueprints import chat as chat_module

    monkeypatch.setattr(chat_module.chat_service, 'llm', None)
    generated = client.post(f'/api/chat/session/{session_id}/title').get_json()['session']
    assert generated['title'] == '帮我写登录用例'
    assert generated['title_source'] == 'auto'
    assert db.session.get(ChatSession, 1).title == '帮我写登录用例'
