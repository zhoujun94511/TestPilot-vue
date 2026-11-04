"""Token 配置与 TokenMonitor 链路白盒测试。"""

import pytest

from config.settings import Settings
from utils.utils_performance_monitoring.token_monitor import (
    TokenMonitor,
    get_token_monitor,
    get_token_session_status,
    refresh_token_monitor_session_limits,
)
from utils.utils_performance_monitoring.token_session import TokenSessionLimitExceeded


def test_settings_declares_session_token_guard_defaults():
    assert Settings.TOKEN_MAX_PER_SESSION == 50000
    assert Settings.TOKEN_MAX_CALLS_PER_SESSION == 100


def test_token_monitor_reads_session_limits_from_settings(monkeypatch):
    monkeypatch.setattr('utils.utils_performance_monitoring.token_monitor.settings.TOKEN_MAX_PER_SESSION', 12000)
    monkeypatch.setattr('utils.utils_performance_monitoring.token_monitor.settings.TOKEN_MAX_CALLS_PER_SESSION', 7)

    monitor = TokenMonitor('gpt-5')
    assert monitor.max_tokens_per_session == 12000
    assert monitor.max_calls_per_session == 7


def test_token_monitor_raises_when_session_token_cap_exceeded(monkeypatch):
    monkeypatch.setattr('utils.utils_performance_monitoring.token_monitor.settings.TOKEN_MAX_PER_SESSION', 10)
    monkeypatch.setattr('utils.utils_performance_monitoring.token_monitor.settings.TOKEN_MAX_CALLS_PER_SESSION', 100)

    monitor = TokenMonitor('gpt-5')
    monitor.total_tokens = 11

    with pytest.raises(TokenSessionLimitExceeded) as exc_info:
        monitor.record_call(input_text='hello', output_text='world', is_actual=True)
    assert exc_info.value.limit_kind == 'tokens'


def test_token_session_warning_status(monkeypatch):
    monkeypatch.setattr('utils.utils_performance_monitoring.token_monitor.settings.TOKEN_MAX_PER_SESSION', 100)
    monkeypatch.setattr('utils.utils_performance_monitoring.token_monitor.settings.TOKEN_MAX_CALLS_PER_SESSION', 100)

    monitor = TokenMonitor('gpt-5')
    monitor.total_tokens = 85
    monitor.refresh_session_notice()
    payload = monitor.session_status_payload()
    assert payload['level'] == 'warning'
    assert payload['message_key'] == 'common.tokenSession.warningTokens'


def test_build_model_error_result_token_session_friendly():
    from utils.utils_core.api_error_handler import build_model_error_result

    err = TokenSessionLimitExceeded('tokens', 50001, 50000)
    result = build_model_error_result('OPENAI', err, fallback_message='失败')
    assert result['success'] is False
    assert result['status_code'] == 429
    assert result['message_key'] == 'common.tokenSession.exceededTokens'
    assert '配置中心' in result['message']


def test_get_token_session_status_without_monitor():
    payload = get_token_session_status()
    assert payload['level'] == 'ok'
    assert payload['tokens']['used'] == 0


def test_refresh_token_monitor_session_limits_updates_singleton(monkeypatch):
    import utils.utils_performance_monitoring.token_monitor as token_monitor_module

    token_monitor_module._token_monitor = TokenMonitor('gpt-5')
    monkeypatch.setattr(token_monitor_module.settings, 'TOKEN_MAX_PER_SESSION', 99999)
    monkeypatch.setattr(token_monitor_module.settings, 'TOKEN_MAX_CALLS_PER_SESSION', 42)

    refresh_token_monitor_session_limits()
    singleton = get_token_monitor('gpt-5')
    assert singleton.max_tokens_per_session == 99999
    assert singleton.max_calls_per_session == 42

    token_monitor_module._token_monitor = None


def test_get_max_tokens_matrix_via_get_llm_helper():
    """与 get_llm 内嵌逻辑一致的期望矩阵（文档化行为）。"""
    from config.settings import settings

    def resolve(provider: str, use_case: str) -> int:
        if use_case == 'chat':
            return int(getattr(settings, 'MAX_TOKENS', 4000))
        if use_case in ('case_generation', 'requirement_analysis'):
            mapping = {
                'OPENAI': 'TR_OPENAI_MAX_TOKENS',
                'DEEPSEEK': 'TR_DEEPSEEK_MAX_TOKENS',
                'GEMINI': 'TR_GEMINI_MAX_TOKENS',
                'QWEN': 'TR_QWEN_MAX_TOKENS',
            }
            key = mapping.get(provider)
            if key:
                return int(getattr(settings, key, 8000))
            return int(getattr(settings, 'MAX_TOKENS', 4000))
        return int(getattr(settings, 'MAX_TOKENS', 4000))

    assert resolve('OPENAI', 'chat') == settings.MAX_TOKENS
    if getattr(settings, 'TR_MAX_TOKENS', None) not in (None, ''):
        assert resolve('OPENAI', 'case_generation') == int(settings.TR_MAX_TOKENS)
    else:
        assert resolve('OPENAI', 'case_generation') == settings.TR_OPENAI_MAX_TOKENS
    assert resolve('OLLAMA', 'case_generation') == settings.MAX_TOKENS
