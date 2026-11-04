from pydantic import SecretStr

from config.settings import anthropic_rejects_sampling, resolve_anthropic_model
from langchain_anthropic import ChatAnthropic


def test_retired_claude_names_map_to_current_models():
    assert resolve_anthropic_model('sonnet') == 'claude-sonnet-5-5'
    assert resolve_anthropic_model('claude-3-5-sonnet') == 'claude-sonnet-5-5'
    assert resolve_anthropic_model('claude-sonnet-4-5-20250929') == 'claude-sonnet-5-5'
    assert resolve_anthropic_model('') == 'claude-sonnet-5-5'
    assert resolve_anthropic_model('claude-opus-4-8') == 'claude-opus-4-8'


def test_current_claude_does_not_send_temperature():
    assert anthropic_rejects_sampling('claude-sonnet-5-5')
    assert not anthropic_rejects_sampling('claude-3-haiku-20240307')

    llm = ChatAnthropic.model_validate({
        'api_key': SecretStr('sk-ant-' + ('a' * 24)),
        'model': 'claude-sonnet-5-5',
        'max_tokens': 8000,
        'timeout': 30,
        'base_url': 'https://api.anthropic.com',
    })
    assert llm.model == 'claude-sonnet-5-5'
    assert llm.max_tokens == 8000
    assert llm.temperature is None
