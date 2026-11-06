#!/usr/bin/python
# -*- coding: utf-8 -*-
"""会话标题：第一轮有效问答后生成一次，用户重命名后不再自动改。"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional

from sqlalchemy import or_

from models.models import ChatHistory, ChatSession, db
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)

PLACEHOLDER_TITLE = '新会话'
TITLE_SOURCE_AUTO = 'auto'
TITLE_SOURCE_MANUAL = 'manual'
LOCKED_TITLE_SOURCES = (TITLE_SOURCE_AUTO, TITLE_SOURCE_MANUAL)

MAX_TITLE_LENGTH = 200
_CHAR_TITLE_CHARS = 16
_WORD_TITLE_CHARS = 48
_PROMPT_EXCERPT_CHARS = 600

# 按字计数的文字：中日韩、泰文、老挝文、缅文、高棉文。其余文字按词（空格）截断。
_CHAR_SCRIPT = re.compile(
    r'['
    r'\u0e00-\u0e7f'
    r'\u0e80-\u0eff'
    r'\u1000-\u109f'
    r'\u1780-\u17ff'
    r'\u3040-\u30ff'
    r'\u31f0-\u31ff'
    r'\u3400-\u9fff'
    r'\uac00-\ud7af'
    r'\uf900-\ufaff'
    r'\uff66-\uff9d'
    r']'
)
_SENTENCE_END = re.compile(r'[。！？!?；;\n]')
_EDGE_PUNCT = '\'"“”‘’「」『』《》【】()（）[]<>`*#_~:：,，.。、!！?？;；-—… \t'
_SIGNAL_STRIP = re.compile(r'[\s\W_]+', re.UNICODE)
_TITLE_PREFIX = re.compile(
    r'^(?:标题|会话标题|title|titre|título|titulo|titel|titolo|タイトル|제목|заголовок)\s*[:：]\s*',
    re.IGNORECASE,
)

_GREETING_TEXTS = (
    '你好', '您好', '你好呀', '你好啊', '嗨', '哈喽', '哈啰', '在吗', '在不在', '在么', '早', '早上好', '上午好',
    '中午好', '下午好', '晚上好', '晚安', '谢谢', '多谢', '感谢', '好的', '好', '嗯', '嗯嗯', '收到', '测试', 'test',
    'hi', 'hello', 'hey', 'yo', 'thanks', 'thankyou', 'ok', 'okay', 'goodmorning', 'goodevening',
    'こんにちは', 'こんばんは', 'おはよう', 'おはようございます', 'ありがとう', 'ありがとうございます', 'はい',
    '안녕하세요', '안녕', '감사합니다', '고마워요',
    'hola', 'gracias', 'buenosdias', 'bonjour', 'salut', 'merci', 'bonsoir',
    'hallo', 'danke', 'gutenmorgen', 'gutenabend', 'gutentag',
    'ola', 'obrigado', 'obrigada', 'bomdia', 'ciao', 'grazie', 'buongiorno', 'buonasera',
    'привет', 'здравствуйте', 'спасибо', 'مرحبا', 'شكرا', 'नमस्ते', 'धन्यवाद', 'สวัสดี', 'ขอบคุณ',
    'xinchao', 'camon',
)


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize('NFKD', str(text or ''))
    return ''.join(char for char in decomposed if not unicodedata.combining(char))


def _normalize_signal(text: str) -> str:
    return _SIGNAL_STRIP.sub('', _fold(text)).lower()


_GREETINGS = {_normalize_signal(item) for item in _GREETING_TEXTS}


def is_low_signal_message(text: str) -> bool:
    """问候、寒暄或去掉标点后不足 2 个字符的消息不足以命名会话。"""
    normalized = _normalize_signal(text)
    return len(normalized) < 2 or normalized in _GREETINGS


def _uses_character_limit(text: str) -> bool:
    return _CHAR_SCRIPT.search(text) is not None


def _truncate(text: str) -> str:
    if _uses_character_limit(text):
        return text if len(text) <= _CHAR_TITLE_CHARS else text[:_CHAR_TITLE_CHARS].rstrip() + '…'
    if len(text) <= _WORD_TITLE_CHARS:
        return text
    cut = text[:_WORD_TITLE_CHARS]
    space = cut.rfind(' ')
    if space >= _WORD_TITLE_CHARS // 2:
        cut = cut[:space]
    return cut.rstrip() + '…'


def fallback_title(text: str) -> str:
    """模型不可用时退回首句：去掉首尾标点与多余空白后截短。"""
    raw = str(text or '').strip()
    if not raw:
        return ''
    first = next((part for part in _SENTENCE_END.split(raw) if part.strip()), raw)
    cleaned = re.sub(r'\s+', ' ', first).strip(_EDGE_PUNCT)
    return _truncate(cleaned) if cleaned else ''


def clean_generated_title(raw: Any) -> str:
    text = str(raw or '').strip()
    line = next((item.strip() for item in text.splitlines() if item.strip()), '')
    line = _TITLE_PREFIX.sub('', line.strip(_EDGE_PUNCT))
    line = re.sub(r'\s+', ' ', line).strip(_EDGE_PUNCT)
    return _truncate(line) if line else ''


LIST_TITLE_SCAN_MESSAGES = 5


def resolve_list_title(chat_session: ChatSession, user_messages: Optional[List[str]] = None) -> str:
    """列表展示用标题。已定标题直接用；旧数据里手动改过的标题也保留；
    否则取前几条用户消息里第一条有效提问整理成短句。"""
    stored = str(chat_session.title or '').strip()
    if chat_session.title_source in LOCKED_TITLE_SOURCES and stored:
        return stored
    texts = [str(item or '').strip() for item in (user_messages or []) if str(item or '').strip()]
    first = texts[0] if texts else ''
    if stored and stored != PLACEHOLDER_TITLE:
        prefix = stored.rstrip('.…').strip()
        if not first or not first.startswith(prefix):
            return stored
    topic = next((text for text in texts if not is_low_signal_message(text)), '')
    return (fallback_title(topic) if topic else '') or PLACEHOLDER_TITLE


def _title_prompt(user_text: str, assistant_text: str) -> str:
    return (
        '为下面这段对话起一个简短的会话标题。\n'
        '要求：标题必须使用用户消息所用的语言，不要翻译成别的语言；概括话题，不要照抄用户原话；'
        '词与词之间不加空格的文字不超过 12 个字，用空格分词的文字不超过 6 个单词；'
        '不要引号、句号、表情，也不要“标题：”之类的前缀；只输出标题本身。\n\n'
        f'用户：{user_text[:_PROMPT_EXCERPT_CHARS]}\n'
        f'助手：{assistant_text[:_PROMPT_EXCERPT_CHARS]}'
    )


def _model_name(llm: Any, response: Any) -> Optional[str]:
    meta = getattr(response, 'response_metadata', None)
    if isinstance(meta, dict):
        for key in ('model_name', 'model'):
            if meta.get(key):
                return str(meta[key])
    for key in ('model_name', 'model'):
        value = getattr(llm, key, None)
        if value:
            return str(value)
    return None


def _generate_with_llm(llm: Any, user_text: str, assistant_text: str) -> str:
    from utils.utils_performance_monitoring.token_monitor import ensure_session_budget, record_message_usage
    from utils.utils_performance_monitoring.token_session import TokenSessionLimitExceeded

    try:
        ensure_session_budget()
    except TokenSessionLimitExceeded:
        logger.info('会话额度已用尽，标题改用首句')
        return ''
    try:
        response = llm.invoke(_title_prompt(user_text, assistant_text))
    except Exception as llm_error:  # noqa: BLE001 - 标题失败不影响对话，退回首句
        logger.warning('生成会话标题失败: %s', llm_error)
        return ''
    try:
        record_message_usage(response, source='chat_title', model_name=_model_name(llm, response))
    except Exception as usage_error:  # noqa: BLE001 - 记账失败不影响标题
        logger.warning('会话标题 Token 记账失败: %s', usage_error)
    content = getattr(response, 'content', response)
    if isinstance(content, list):
        content = ''.join(str(part.get('text', '')) if isinstance(part, dict) else str(part) for part in content)
    return clean_generated_title(content)


def _session_messages(session_id: str, limit: int = 12) -> List[ChatHistory]:
    return (
        ChatHistory.query.filter(
            ChatHistory.session_id == session_id,
            ChatHistory.role.in_(['user', 'assistant']),
        )
        .order_by(ChatHistory.created_time.asc(), ChatHistory.id.asc())
        .limit(limit)
        .all()
    )


def _title_payload(chat_session: ChatSession, generated: bool) -> Dict[str, Any]:
    return {
        'session_id': chat_session.session_id,
        'title': chat_session.title or PLACEHOLDER_TITLE,
        'title_source': chat_session.title_source,
        'generated': generated,
    }


def ensure_session_title(chat_session: ChatSession, llm: Any = None) -> Dict[str, Any]:
    """标题未定时，用第一条有效提问及其回复生成一次；已定或还没有有效问答时原样返回。"""
    if chat_session.title_source in LOCKED_TITLE_SOURCES:
        return _title_payload(chat_session, False)

    messages = _session_messages(chat_session.session_id)
    topic_index = next(
        (index for index, row in enumerate(messages)
         if row.role == 'user' and not is_low_signal_message(row.content)),
        None,
    )
    if topic_index is None:
        return _title_payload(chat_session, False)
    reply = next((row for row in messages[topic_index + 1:] if row.role == 'assistant'), None)
    if reply is None:
        return _title_payload(chat_session, False)

    topic = messages[topic_index].content
    title = _generate_with_llm(llm, topic, reply.content) if llm is not None else ''
    title = title or fallback_title(topic)
    if not title:
        return _title_payload(chat_session, False)

    # 模型生成要几秒，期间用户可能已经手动改名；只在标题仍未锁定时写入
    updated = ChatSession.query.filter(
        ChatSession.session_id == chat_session.session_id,
        or_(ChatSession.title_source.is_(None), ChatSession.title_source.notin_(LOCKED_TITLE_SOURCES)),
    ).update(
        {'title': title[:MAX_TITLE_LENGTH], 'title_source': TITLE_SOURCE_AUTO},
        synchronize_session=False,
    )
    db.session.commit()
    db.session.refresh(chat_session)
    return _title_payload(chat_session, bool(updated))
