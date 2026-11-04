#!/usr/bin/python
# -*- coding: utf-8 -*-
"""batch 导出 chat 过滤（纯函数 + 内存库）。"""

from __future__ import annotations

from flask import Flask

from models.models import ChatHistory, ChatSession, db
from services.data_scope import set_g_user_for_tests


def test_batch_chat_item_filter_by_scoped_sessions(tmp_path):
    from config.settings import settings
    from blueprints.export import _scope_batch_export_config

    settings.AUTH_REQUIRE_AUTH = True

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_path / "batch_scope.db"}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
        dept_a = 1
        dept_b = 2
        db.session.add(
            ChatSession(
                session_id='sess-a',
                title='a',
                dept_id=dept_a,
                owner_user_id=10,
                is_deleted=False,
            )
        )
        db.session.add(
            ChatSession(
                session_id='sess-b',
                title='b',
                dept_id=dept_b,
                owner_user_id=20,
                is_deleted=False,
            )
        )
        db.session.add(
            ChatHistory(session_id='sess-a', role='user', content='ok', message_type='chat')
        )
        db.session.add(
            ChatHistory(session_id='sess-b', role='user', content='no', message_type='chat')
        )
        db.session.commit()

        visible = ChatHistory.query.filter_by(session_id='sess-a').first()
        hidden = ChatHistory.query.filter_by(session_id='sess-b').first()
        assert visible and hidden

        set_g_user_for_tests({'id': 10, 'role': 'admin', 'dept_id': dept_a})
        scoped = _scope_batch_export_config(
            {
                'export_chat': True,
                'chat_history': [
                    {'id': visible.id, 'session_id': 'sess-a', 'content': 'ok'},
                    {'id': hidden.id, 'session_id': 'sess-b', 'content': 'no'},
                    {'session_id': 'sess-b', 'content': 'no-id'},
                ],
            }
        )

    assert len(scoped['chat_history']) == 1
    assert scoped['chat_history'][0]['session_id'] == 'sess-a'


def test_batch_export_config_filters_foreign_cases(tmp_path):
    from config.settings import settings
    from blueprints.export import _scope_batch_export_config
    from models.models import TestCase

    settings.AUTH_REQUIRE_AUTH = True

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_path / "batch_cases.db"}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
        db.session.add(
            TestCase(
                case_id='TC-OK',
                title='ok',
                description='',
                precondition='',
                steps='[]',
                expected_result='[]',
                priority='P2',
                category='functional',
                tags='',
                status='draft',
                created_by='test',
                dept_id=1,
            )
        )
        db.session.add(
            TestCase(
                case_id='TC-NO',
                title='no',
                description='',
                precondition='',
                steps='[]',
                expected_result='[]',
                priority='P2',
                category='functional',
                tags='',
                status='draft',
                created_by='test',
                dept_id=2,
            )
        )
        db.session.commit()

        set_g_user_for_tests({'id': 1, 'role': 'admin', 'dept_id': 1})
        scoped = _scope_batch_export_config(
            {
                'export_cases': True,
                'cases': [{'case_id': 'TC-OK'}, {'case_id': 'TC-NO'}],
            }
        )

    assert len(scoped['cases']) == 1
    assert scoped['cases'][0]['case_id'] == 'TC-OK'
