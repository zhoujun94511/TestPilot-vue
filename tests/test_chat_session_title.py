#!/usr/bin/python
# -*- coding: utf-8 -*-
"""会话标题：问候语不命名、第一轮有效问答后生成一次、用户重命名后锁定。"""

from __future__ import annotations

import pytest
from flask import Flask

from models.models import ChatHistory, ChatSession, db
from services.chat_session_title import (
    PLACEHOLDER_TITLE,
    TITLE_SOURCE_AUTO,
    TITLE_SOURCE_MANUAL,
    clean_generated_title,
    ensure_session_title,
    fallback_title,
    is_low_signal_message,
    resolve_list_title,
)


class _FakeResponse:
    def __init__(self, content):
        self.content = content


class _FakeLlm:
    def __init__(self, content: str | Exception = '登录用例设计'):
        self.content = content
        self.calls = 0
        self.prompts: list[str] = []

    def invoke(self, prompt: str):
        self.calls += 1
        self.prompts.append(prompt)
        content = self.content
        if isinstance(content, Exception):
            raise content
        return _FakeResponse(content)


@pytest.mark.parametrize('text', [
    '你好', '您好！', 'hi', 'Hello!!', '在吗？', '谢谢', '嗯', '?',
    'こんにちは', '안녕하세요', 'Bonjour !', 'Hola', 'Olá!', 'Привет',
])
def test_greetings_are_low_signal(text):
    assert is_low_signal_message(text)


@pytest.mark.parametrize('text', [
    '帮我设计登录页的测试用例',
    'How do I test a login form?',
    'ログイン画面のテスト観点を整理して',
    'Comment concevoir les cas de test de connexion ?',
])
def test_real_questions_are_not_low_signal(text):
    assert not is_low_signal_message(text)


def test_fallback_title_takes_first_sentence_and_truncates():
    assert fallback_title('  帮我写登录用例。另外还要注册  ') == '帮我写登录用例'
    assert fallback_title('请帮我把这个需求文档里的所有验收点逐条拆成测试用例') == '请帮我把这个需求文档里的所有验收…'
    long_en = 'Please help me design boundary value test cases for the checkout discount rules'
    result = fallback_title(long_en)
    assert result.endswith('…') and len(result) <= 49 and ' ' not in result[-2:]


def test_fallback_title_follows_the_users_writing_system():
    japanese = 'ログイン画面の境界値と異常系を含むテストケースを設計してください'
    japanese_title = fallback_title(japanese)
    assert japanese_title.endswith('…') and len(japanese_title) == 17
    korean = '로그인 화면의 경계값과 예외 흐름을 포함한 테스트 케이스를 작성해 주세요'
    assert len(fallback_title(korean)) <= 17
    french = 'Peux-tu concevoir des cas de test pour les regles de reduction du paiement en ligne'
    french_title = fallback_title(french)
    assert french_title.endswith('…') and ' ' in french_title[:-1]


def test_clean_generated_title_strips_noise():
    assert clean_generated_title('标题：“登录用例设计。”') == '登录用例设计'
    assert clean_generated_title('**Login test design**\n解释…') == 'Login test design'
    assert clean_generated_title('Titre : Conception des cas de connexion') == 'Conception des cas de connexion'
    assert clean_generated_title('タイトル：ログイン試験') == 'ログイン試験'
    assert clean_generated_title('') == ''


def _session(**overrides):
    values = {'session_id': 's1', 'title': PLACEHOLDER_TITLE, 'title_source': None}
    values.update(overrides)
    return ChatSession(**values)


def test_list_title_prefers_locked_title():
    assert resolve_list_title(_session(title='登录用例', title_source=TITLE_SOURCE_AUTO), ['你好']) == '登录用例'


def test_list_title_hides_greeting_only_session():
    assert resolve_list_title(_session(title='你好'), ['你好', '在吗']) == PLACEHOLDER_TITLE


def test_list_title_skips_greeting_to_first_real_question():
    messages = ['你好', '帮我设计登录功能测试用例', '如何补充登录接口测试用例？']
    assert resolve_list_title(_session(title='你好'), messages) == '帮我设计登录功能测试用例'


def test_list_title_keeps_legacy_custom_title():
    assert resolve_list_title(_session(title='我的需求讨论'), ['你好']) == '我的需求讨论'


def test_list_title_cleans_legacy_first_message_title():
    first = '帮我写登录用例。另外还要注册'
    assert resolve_list_title(_session(title=first[:50]), [first]) == '帮我写登录用例'


@pytest.fixture()
def app_ctx(tmp_path):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_path / "title.db"}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield app


def _add_session(messages, **overrides):
    chat_session = _session(**overrides)
    db.session.add(chat_session)
    for role, content in messages:
        db.session.add(ChatHistory(session_id=chat_session.session_id, role=role, content=content))
    db.session.commit()
    return chat_session


def test_greeting_only_session_stays_untitled(app_ctx):
    chat_session = _add_session([('user', '你好'), ('assistant', '你好，有什么可以帮你？')])
    llm = _FakeLlm()
    result = ensure_session_title(chat_session, llm)
    assert result['generated'] is False
    assert result['title_source'] is None
    assert llm.calls == 0


def test_title_prompt_keeps_the_users_language(app_ctx):
    chat_session = _add_session([
        ('user', 'ログイン画面のテスト観点を整理して'),
        ('assistant', '了解しました'),
    ])
    llm = _FakeLlm('ログイン試験')
    result = ensure_session_title(chat_session, llm)
    prompt = llm.prompts[0]
    assert result['title'] == 'ログイン試験'
    assert '用户消息所用的语言' in prompt
    assert '不要翻译成别的语言' in prompt
    assert '中文不超过' not in prompt
    assert '英文不超过' not in prompt
    assert 'ログイン画面のテスト観点を整理して' in prompt


def test_title_generated_from_first_real_question(app_ctx):
    chat_session = _add_session([
        ('user', '你好'),
        ('assistant', '你好'),
        ('user', '帮我设计登录页的测试用例'),
        ('assistant', '可以从账号、密码、验证码三个方面设计……'),
    ])
    llm = _FakeLlm('“登录页测试设计”')
    result = ensure_session_title(chat_session, llm)
    assert result == {
        'session_id': 's1',
        'title': '登录页测试设计',
        'title_source': TITLE_SOURCE_AUTO,
        'generated': True,
    }
    assert ensure_session_title(chat_session, llm)['generated'] is False
    assert llm.calls == 1


def test_llm_failure_falls_back_to_first_sentence(app_ctx):
    chat_session = _add_session([('user', '帮我写登录用例。另外还要注册'), ('assistant', '好的')])
    result = ensure_session_title(chat_session, _FakeLlm(RuntimeError('boom')))
    assert result['title'] == '帮我写登录用例'
    assert result['title_source'] == TITLE_SOURCE_AUTO


def test_manual_title_is_never_overwritten(app_ctx):
    chat_session = _add_session(
        [('user', '帮我写登录用例'), ('assistant', '好的')],
        title='我的命名',
        title_source=TITLE_SOURCE_MANUAL,
    )
    llm = _FakeLlm()
    assert ensure_session_title(chat_session, llm)['title'] == '我的命名'
    assert llm.calls == 0


def test_rename_during_generation_wins(app_ctx):
    chat_session = _add_session([('user', '帮我写登录用例'), ('assistant', '好的')])

    class _RenamingLlm(_FakeLlm):
        def invoke(self, prompt):
            db.session.execute(
                ChatSession.__table__.update()
                .where(ChatSession.session_id == 's1')
                .values(title='我的命名', title_source=TITLE_SOURCE_MANUAL)
            )
            db.session.commit()
            return super().invoke(prompt)

    result = ensure_session_title(chat_session, _RenamingLlm('登录用例设计'))
    assert result['generated'] is False
    assert result['title'] == '我的命名'
    assert result['title_source'] == TITLE_SOURCE_MANUAL


def test_no_reply_yet_keeps_placeholder(app_ctx):
    chat_session = _add_session([('user', '帮我写登录用例')])
    assert ensure_session_title(chat_session, _FakeLlm())['title'] == PLACEHOLDER_TITLE
