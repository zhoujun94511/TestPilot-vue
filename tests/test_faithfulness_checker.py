# -*- coding: utf-8 -*-
"""忠实度检查：错误单位要拦截，边界数量和原文没写的操作不拦截。"""

from utils.utils_ai_quality.faithfulness_checker import (
    assess_quantified_claims,
    contradiction_issue,
    judge_sentences,
)

SOURCE = "密码长度为8到16位。支付成功后由人工审核再发货。"


class _Reply:
    def __init__(self, content):
        self.content = content


class _StubLLM:
    @staticmethod
    def invoke(_messages):
        return _Reply('[{"index":1,"verdict":"contradicted"},{"index":2,"verdict":"not_mentioned"}]')


def _verdict(content, source=SOURCE, allow_unmentioned=False):
    claims = assess_quantified_claims(content, source, allow_unmentioned)
    return claims[0]["verdict"] if claims else ""


def test_range_endpoint_is_entailed():
    assert _verdict("密码长度至少8位") == "entailed"


def test_wrong_unit_is_contradicted():
    assert _verdict("有效期为8天") == "contradicted"


def test_wrong_unit_reason_mentions_unit_mismatch():
    claim = assess_quantified_claims("有效期为8天", SOURCE)[0]
    assert "单位不一致" in contradiction_issue(claim)


def test_missing_quantity_is_contradicted():
    assert _verdict("退款在30天内完成") == "contradicted"


def test_boundary_quantity_is_allowed_when_flagged():
    assert _verdict("输入7位密码应拒绝", allow_unmentioned=True) == "not_mentioned"


def test_invented_action_is_contradicted():
    judged = judge_sentences(_StubLLM(), SOURCE, ["系统自动退款", "记录补充日志"])
    assert judged[0]["verdict"] == "contradicted"


def test_unmentioned_action_is_allowed():
    judged = judge_sentences(_StubLLM(), SOURCE, ["系统自动退款", "记录补充日志"])
    assert judged[1]["verdict"] == "not_mentioned"
