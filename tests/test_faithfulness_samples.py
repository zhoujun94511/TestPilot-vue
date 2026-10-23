# -*- coding: utf-8 -*-
"""标注样例：错误单位要拦截，边界数量和原文没写的操作不拦截。"""

from utils.utils_ai_quality.faithfulness_checker import (
    assess_quantified_claims,
    contradiction_issue,
    judge_sentences,
)


class _Reply:
    def __init__(self, content):
        self.content = content


class _StubLLM:
    def invoke(self, _messages):
        return _Reply('[{"index":1,"verdict":"contradicted"},{"index":2,"verdict":"not_mentioned"}]')


def _verdict(content, source, allow_unmentioned=False):
    claims = assess_quantified_claims(content, source, allow_unmentioned)
    return claims[0]["verdict"] if claims else ""


def main():
    source = "密码长度为8到16位。支付成功后由人工审核再发货。"
    checks = {
        "range_endpoint_ok": _verdict("密码长度至少8位", source) == "entailed",
        "wrong_unit_blocked": _verdict("有效期为8天", source) == "contradicted",
        "wrong_unit_reason": "单位不一致" in contradiction_issue(
            assess_quantified_claims("有效期为8天", source)[0]
        ),
        "missing_quantity_blocked": _verdict("退款在30天内完成", source) == "contradicted",
        "boundary_quantity_allowed": _verdict("输入7位密码应拒绝", source, allow_unmentioned=True) == "not_mentioned",
    }
    judged = judge_sentences(_StubLLM(), source, ["系统自动退款", "记录补充日志"])
    checks["invented_action_contradicted"] = judged[0]["verdict"] == "contradicted"
    checks["unmentioned_action_allowed"] = judged[1]["verdict"] == "not_mentioned"
    print(checks)
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
