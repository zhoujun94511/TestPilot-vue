"""文档分析互斥与 Token 用量拆分。"""
import uuid

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

import utils.utils_business_logic.requirements_analyze as requirements_analyze
import utils.utils_performance_monitoring.token_monitor as token_monitor
from services.document_service import claim_document_analysis, release_document_analysis
from utils.utils_performance_monitoring.token_monitor import TokenMonitor, usage_from_message
from utils.utils_performance_monitoring.token_session import TokenSessionLimitExceeded


def test_same_document_analysis_is_single_flight():
    name = f"guard-{uuid.uuid4().hex}.txt"
    assert claim_document_analysis(name.upper()) is True
    assert claim_document_analysis(name.lower()) is False
    release_document_analysis(name)
    assert claim_document_analysis(name) is True
    release_document_analysis(name)


def test_provider_usage_splits_input_and_output():
    monitor = TokenMonitor("unit-test-model")
    result = monitor.record_call(
        832,
        is_actual=True,
        actual_tokens={"prompt_tokens": 1200, "completion_tokens": 340, "total_tokens": 1540},
    )
    assert result["input_tokens"] == 1200
    assert result["output_tokens"] == 340
    assert result["counted"] is True


def test_usage_fills_completion_from_total():
    class Message:
        response_metadata = {"token_usage": {"prompt_tokens": 10, "total_tokens": 25}}

    usage = usage_from_message(Message())
    assert usage["prompt_tokens"] == 10
    assert usage["completion_tokens"] == 15
    assert usage["total_tokens"] == 25


def test_budget_check_blocks_before_calling_model(monkeypatch):
    monitor = TokenMonitor("unit-test-model")
    monkeypatch.setattr(monitor, "apply_session_limits_from_settings", lambda: None)
    monitor.max_calls_per_session = 3
    monitor.call_count = 3
    monkeypatch.setattr(token_monitor, "_token_monitor", monitor)
    with pytest.raises(TokenSessionLimitExceeded):
        token_monitor.ensure_session_budget()


def test_spent_budget_does_not_trigger_fallback_call(monkeypatch):
    calls = []

    def fake_model(_prompt):
        calls.append(1)
        return AIMessage(content="[]")

    def over_limit(*_args, **_kwargs):
        raise TokenSessionLimitExceeded("calls", 101, 100)

    monkeypatch.setattr(requirements_analyze, "ensure_session_budget", lambda: None)
    monkeypatch.setattr(requirements_analyze, "record_message_usage", over_limit)
    with pytest.raises(TokenSessionLimitExceeded):
        requirements_analyze.analyze_requirement(RunnableLambda(fake_model), "用户可以登录")
    assert len(calls) == 1
