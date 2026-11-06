#!/usr/bin/python
# -*- coding: utf-8 -*-
"""聊天消息可见范围：软删除会话的消息不计入总览、最近活动、搜索与导出。"""

from __future__ import annotations

import pytest
from flask import Flask

from models.models import ChatHistory, ChatSession, db
import services.data_scope as data_scope


@pytest.fixture()
def app_ctx(tmp_path, monkeypatch):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_path / "scope.db"}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    monkeypatch.setattr(data_scope, 'auth_required', lambda: False)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _seed():
    live = ChatSession(session_id='live', title='在用会话', is_deleted=False)
    deleted = ChatSession(session_id='deleted', title='已删会话', is_deleted=True)
    db.session.add_all([live, deleted])
    rows = [
        ChatHistory(session_id='live', role='user', content='问题一'),
        ChatHistory(session_id='live', role='assistant', content='回答一'),
        ChatHistory(session_id='deleted', role='user', content='已删问题'),
        ChatHistory(session_id='deleted', role='assistant', content='已删回答'),
        ChatHistory(session_id='deleted', role='user', content='已删问题二'),
        ChatHistory(session_id='ghost', role='user', content='没有会话记录的消息'),
    ]
    db.session.add_all(rows)
    db.session.commit()


def test_soft_deleted_session_messages_are_not_counted(app_ctx):
    _seed()
    visible = data_scope.scoped_chat_history_query().all()
    assert sorted(row.content for row in visible) == ['回答一', '问题一']


def test_count_matches_visible_sessions_after_session_delete(app_ctx):
    _seed()
    assert data_scope.scoped_chat_history_query().count() == 2
    live = ChatSession.query.filter_by(session_id='live').one()
    live.is_deleted = True
    db.session.commit()
    assert data_scope.scoped_chat_history_query().count() == 0


def test_clearing_messages_reduces_count(app_ctx):
    _seed()
    ChatHistory.query.filter_by(session_id='live').delete()
    db.session.commit()
    assert data_scope.scoped_chat_history_query().count() == 0
