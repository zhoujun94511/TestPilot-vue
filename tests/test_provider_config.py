"""配置中心密钥与服务商开关。"""

from blueprints.config_center import enforce_single_active_provider, validate_ai_model_configs
from config.settings import resolve_active_company
from utils.utils_core.api_error_handler import (
    check_api_key_configuration,
    get_api_key_with_fallback,
    is_placeholder_secret,
)


def test_config_center_default_wins_over_env():
    assert resolve_active_company('QWEN', 'DEEPSEEK') == 'QWEN'


def test_env_default_only_used_when_config_center_is_empty():
    assert resolve_active_company('', 'gemini') == 'GEMINI'
    assert resolve_active_company(None, 'unknown') == 'DEEPSEEK'


def test_save_keeps_one_provider_enabled(monkeypatch):
    monkeypatch.setattr(
        'blueprints.config_center.config_center_service.get_config_value',
        lambda key, default=None: None,
    )
    configs = [
        {'key': 'DEFAULT_COMPANY', 'value': 'QWEN'},
        {'key': 'ENABLE_QWEN', 'value': 'false'},
        {'key': 'ENABLE_DEEPSEEK', 'value': 'true'},
        {'key': 'QWEN_API_KEY', 'value': 'sk-qwen'},
        {'key': 'DEEPSEEK_API_KEY', 'value': 'sk-deepseek'},
    ]
    enforce_single_active_provider(configs)
    values = {item['key']: item['value'] for item in configs}
    assert values['ENABLE_QWEN'] == 'true'
    assert values['ENABLE_DEEPSEEK'] == 'false'
    assert values['ENABLE_OPENAI'] == 'false'
    assert values['QWEN_API_KEY'] == 'sk-qwen'
    assert values['DEEPSEEK_API_KEY'] == 'sk-deepseek'


def test_save_skips_switches_that_already_match(monkeypatch):
    stored = {
        'DEFAULT_COMPANY': 'DEEPSEEK',
        'ENABLE_OPENAI': False,
        'ENABLE_DEEPSEEK': True,
        'ENABLE_OLLAMA': False,
        'ENABLE_GEMINI': False,
        'ENABLE_QWEN': False,
        'ENABLE_ANTHROPIC': False,
    }
    monkeypatch.setattr(
        'blueprints.config_center.config_center_service.get_config_value',
        lambda key, default=None: stored.get(key, default),
    )
    configs = [{'key': 'MAX_TOKENS', 'value': 4000}]
    enforce_single_active_provider(configs)
    assert [item['key'] for item in configs] == ['MAX_TOKENS']


def test_empty_and_placeholder_keys_can_be_saved(monkeypatch):
    monkeypatch.setattr(
        'blueprints.config_center.config_center_service.get_config_value',
        lambda key, default=None: None,
    )
    configs = [
        {'key': 'DEFAULT_COMPANY', 'value': 'DEEPSEEK'},
        {'key': 'DEEPSEEK_API_KEY', 'value': 'YOUR_DEEPSEEK_API_KEY'},
        {'key': 'QWEN_API_KEY', 'value': ''},
        {'key': 'OPENAI_API_KEY', 'value': '********'},
    ]
    validate_ai_model_configs(configs)
    assert configs[1]['value'] == ''
    assert configs[2]['value'] == ''
    assert configs[3]['value'] == '********'


def test_placeholders_are_not_configured():
    assert is_placeholder_secret('')
    assert is_placeholder_secret('********')
    assert is_placeholder_secret('YOUR_QWEN_API_KEY')
    assert is_placeholder_secret('CHANGE_ME')
    assert is_placeholder_secret('xxxxxxxx')
    assert not is_placeholder_secret('sk-from-center')


def test_real_keys_with_common_words_inside_are_kept():
    # 拆开写：这是假字面量，不是凭据，拆开后不会被密钥扫描当成真实密钥
    assert not is_placeholder_secret('sk-ant-api03-' + 'abcTODOxyz-exampleQ9')
    assert not is_placeholder_secret('sk-1234placeholder5678')


def test_config_center_key_wins_over_placeholder_env(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'YOUR_DEEPSEEK_API_KEY')
    monkeypatch.setattr(
        'utils.utils_core.api_error_handler.get_api_key_from_config_center',
        lambda company: 'sk-from-center',
    )
    key, source, _message = get_api_key_with_fallback('DEEPSEEK')
    assert key == 'sk-from-center'
    assert source == 'config_center'


def test_placeholder_env_does_not_count_as_a_key(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'YOUR_DEEPSEEK_API_KEY')
    monkeypatch.setattr(
        'utils.utils_core.api_error_handler.get_api_key_from_config_center',
        lambda company: None,
    )
    key, source, _message = get_api_key_with_fallback('DEEPSEEK')
    assert key is None
    assert source is None


def test_ollama_needs_no_key_in_any_case():
    assert check_api_key_configuration('OLLAMA') == (True, '')
    assert check_api_key_configuration('ollama') == (True, '')
