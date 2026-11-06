#!/usr/bin/python
# -*- coding: utf-8 -*-
"""对话正文只给本人：管理员只能看部门计数，不能读他人正文；超管不受限。"""

from __future__ import annotations

import pytest
from flask import Flask

import services.data_scope as data_scope
import services.stats_scope as stats_scope
from models.models import ChatHistory, ChatSession, db
from services.data_scope import can_access_record, set_g_user_for_tests

ADMIN_ID = 10
COLLEAGUE_ID = 11
OTHER_DEPT_ID = 20
DEPT = 1


@pytest.fixture()
def chat_app(tmp_path, monkeypatch):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_path / "chat_privacy.db"}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    monkeypatch.setattr(data_scope, 'auth_required', lambda: True)
    with app.app_context():
        db.create_all()
        db.session.add_all([
            ChatSession(session_id='mine', title='我的', dept_id=DEPT, owner_user_id=ADMIN_ID),
            ChatSession(session_id='colleague', title='同事的', dept_id=DEPT, owner_user_id=COLLEAGUE_ID),
            ChatSession(session_id='elsewhere', title='别的部门', dept_id=OTHER_DEPT_ID, owner_user_id=OTHER_DEPT_ID),
        ])
        db.session.add_all([
            ChatHistory(session_id='mine', role='user', content='我的问题'),
            ChatHistory(session_id='colleague', role='user', content='同事的私人问题'),
            ChatHistory(session_id='colleague', role='assistant', content='同事的回答'),
            ChatHistory(session_id='elsewhere', role='user', content='别部门的问题'),
        ])
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


def _session(session_id):
    return ChatSession.query.filter_by(session_id=session_id).one()


def test_admin_reads_only_own_message_bodies(chat_app):
    set_g_user_for_tests({'id': ADMIN_ID, 'role': 'admin', 'dept_id': DEPT})
    bodies = {row.content for row in data_scope.scoped_chat_history_query().all()}
    assert bodies == {'我的问题'}


def test_admin_cannot_open_a_colleagues_session(chat_app):
    set_g_user_for_tests({'id': ADMIN_ID, 'role': 'admin', 'dept_id': DEPT})
    assert can_access_record(_session('mine'), 'chat') is True
    assert can_access_record(_session('colleague'), 'chat') is False


def test_admin_sees_department_counts_without_bodies(chat_app):
    set_g_user_for_tests({'id': ADMIN_ID, 'role': 'admin', 'dept_id': DEPT})
    assert stats_scope.scoped_chat_sessions_query().count() == 2
    assert stats_scope.scoped_chat_message_stats_query().count() == 3
    assert data_scope.scoped_chat_history_query().count() == 1


def test_regular_user_sees_only_own_sessions_and_counts(chat_app):
    set_g_user_for_tests({'id': COLLEAGUE_ID, 'role': 'user', 'dept_id': DEPT})
    assert stats_scope.scoped_chat_sessions_query().count() == 1
    assert stats_scope.scoped_chat_message_stats_query().count() == 2
    assert {row.content for row in data_scope.scoped_chat_history_query().all()} == {
        '同事的私人问题',
        '同事的回答',
    }
    assert can_access_record(_session('mine'), 'chat') is False


def test_super_admin_still_sees_everything(chat_app):
    set_g_user_for_tests({'id': 1, 'role': 'super_admin', 'dept_id': None})
    assert data_scope.scoped_chat_history_query().count() == 4
    assert can_access_record(_session('colleague'), 'chat') is True
    assert can_access_record(_session('elsewhere'), 'chat') is True


def test_legacy_session_without_owner_is_listed_for_its_user(chat_app):
    db.session.add(ChatSession(session_id='legacy', title='老会话', dept_id=DEPT, user_id=str(COLLEAGUE_ID)))
    db.session.add(ChatHistory(session_id='legacy', role='user', content='老问题'))
    db.session.commit()

    set_g_user_for_tests({'id': COLLEAGUE_ID, 'role': 'user', 'dept_id': DEPT})
    assert can_access_record(_session('legacy'), 'chat') is True
    assert '老问题' in {row.content for row in data_scope.scoped_chat_history_query().all()}

    set_g_user_for_tests({'id': ADMIN_ID, 'role': 'admin', 'dept_id': DEPT})
    assert can_access_record(_session('legacy'), 'chat') is False
    assert '老问题' not in {row.content for row in data_scope.scoped_chat_history_query().all()}


def test_admin_from_another_department_gets_nothing(chat_app):
    set_g_user_for_tests({'id': OTHER_DEPT_ID, 'role': 'admin', 'dept_id': OTHER_DEPT_ID})
    assert stats_scope.scoped_chat_sessions_query().count() == 1
    assert {row.content for row in data_scope.scoped_chat_history_query().all()} == {'别部门的问题'}
