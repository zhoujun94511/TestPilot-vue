#!/usr/bin/python
# -*- coding: utf-8 -*-
"""确定性规则：先把能写死的用例写出来，模型只补规则覆盖不到的业务步骤。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

MAX_CRITERIA = 20
DEFAULT_MAX_LENGTH = 255

_CRITERIA_SPLIT = re.compile(r"[\n。；;！!？?]+")
_LEADING_MARKER = re.compile(r"^\s*(?:[-*•·]|\d+[.、)）](?!\d)|[（(]\d+[）)]|[一二三四五六七八九十]+[、.])\s*")
_MAX_LENGTH_PATTERNS = (
    re.compile(r"(?:最多|不超过|不能超过|最长|上限为?|限制为?)\s*(\d{1,5})\s*个?(?:字符|字|位)"),
    re.compile(r"(\d{1,5})\s*个?(?:字符|字|位)以内"),
    re.compile(r"(?:max(?:imum)?|up to|no more than)\s*(\d{1,5})\s*char", re.IGNORECASE),
)
_LOCK_PATTERN = re.compile(r"(?:失败|错误)\s*(\d{1,2})\s*次")
_LOCK_EN_PATTERN = re.compile(r"(\d{1,2})\s*(?:failed|wrong|invalid)\s*attempts?", re.IGNORECASE)


@dataclass(frozen=True)
class Scenario:
    key: str
    label: str
    keywords: tuple


SCENARIOS = (
    Scenario("search", "搜索", ("搜索", "查询", "检索", "查找", "search", "query")),
    Scenario("login", "登录", ("登录", "登陆", "密码", "验证码", "login", "sign in", "password")),
    Scenario("form", "表单", ("表单", "填写", "提交", "注册", "保存", "输入框", "form", "submit", "register")),
)


@dataclass
class RuleContext:
    requirement_text: str
    max_length: int = DEFAULT_MAX_LENGTH
    lock_attempts: int | None = None
    explicit_max_length: bool = False
    scenarios: List[str] = field(default_factory=list)


def extract_acceptance_criteria(text: str) -> List[str]:
    """按行、句号、分号拆出验收点。去掉序号，丢掉过短的碎片并去重。"""
    seen: set[str] = set()
    criteria: List[str] = []
    for raw in _CRITERIA_SPLIT.split(str(text or "")):
        item = _LEADING_MARKER.sub("", raw).strip(" \t，,：:")
        if len(item) < 4 or item in seen:
            continue
        seen.add(item)
        criteria.append(item)
        if len(criteria) >= MAX_CRITERIA:
            break
    return criteria


def detect_scenarios(text: str) -> List[str]:
    lowered = str(text or "").lower()
    return [s.key for s in SCENARIOS if any(k in lowered for k in s.keywords)]


def build_context(requirement_text: str) -> RuleContext:
    text = str(requirement_text or "")
    ctx = RuleContext(requirement_text=text, scenarios=detect_scenarios(text))
    for pattern in _MAX_LENGTH_PATTERNS:
        match = pattern.search(text)
        if match:
            ctx.max_length = max(1, int(match.group(1)))
            ctx.explicit_max_length = True
            break
    lock = _LOCK_PATTERN.search(text) or _LOCK_EN_PATTERN.search(text)
    if lock:
        ctx.lock_attempts = max(1, int(lock.group(1)))
    return ctx


def _case(rule_id: str, scenario: str, title: str, steps: List[str], expected: List[str],
          priority: str = "P2", test_method: str = "等价类划分") -> Dict[str, Any]:
    label = next((s.label for s in SCENARIOS if s.key == scenario), scenario)
    return {
        "rule_id": rule_id,
        "source": "rule",
        "scenario": scenario,
        "title": f"{label}：{title}",
        "precondition": "",
        "steps": steps,
        "expected_result": expected,
        "priority": priority,
        "category": "functional",
        "test_method": test_method,
        "module": label,
        "tags": ["规则骨架", label],
    }


def _search_rules(ctx: RuleContext) -> List[Dict[str, Any]]:
    over = ctx.max_length + 1
    return [
        _case("search.valid", "search", "输入存在的关键词",
              ["在搜索框输入一个已存在的关键词", "执行搜索"],
              ["展示与关键词匹配的结果", "结果数量与条件一致"], "P1"),
        _case("search.no_match", "search", "输入不存在的关键词",
              ["在搜索框输入一个不存在的关键词", "执行搜索"],
              ["结果为空并给出无结果提示", "页面不报错"]),
        _case("search.empty", "search", "搜索框为空时执行搜索",
              ["清空搜索框", "执行搜索"],
              ["按需求给出必填提示或返回默认列表", "不触发异常请求"]),
        _case("search.special_chars", "search", "输入特殊字符",
              ["在搜索框输入 %_'\"<>;-- 等特殊字符", "执行搜索"],
              ["按普通文本处理，不被当作通配符或脚本执行", "页面不报错"], "P2", "错误推测"),
        _case("search.overlong", "search", f"输入超长字符串（{over} 个字符）",
              [f"在搜索框输入 {over} 个字符", "执行搜索"],
              [f"超出 {ctx.max_length} 个字符时被截断或给出长度提示", "页面不报错"], "P2", "边界值分析"),
        _case("search.repeat", "search", "连续多次执行搜索",
              ["输入同一关键词", "快速连续执行搜索 5 次"],
              ["结果一致，不出现重复渲染或请求错乱"], "P3", "错误推测"),
    ]


def _login_rules(ctx: RuleContext) -> List[Dict[str, Any]]:
    rules = [
        _case("login.valid", "login", "正确的账号和密码",
              ["输入已存在账号与正确密码", "点击登录"],
              ["登录成功并进入首页"], "P0"),
        _case("login.wrong_password", "login", "密码错误",
              ["输入已存在账号与错误密码", "点击登录"],
              ["登录失败并提示账号或密码错误", "提示不泄露账号是否存在"], "P1"),
        _case("login.unknown_account", "login", "账号不存在",
              ["输入不存在的账号与任意密码", "点击登录"],
              ["登录失败，提示与密码错误一致"], "P1"),
        _case("login.empty", "login", "账号或密码为空",
              ["账号与密码分别留空", "点击登录"],
              ["给出必填提示，不发起登录请求"]),
        _case("login.injection", "login", "账号输入注入字符",
              ["账号输入 ' OR '1'='1", "输入任意密码并点击登录"],
              ["登录失败，不出现服务端错误"], "P1", "错误推测"),
    ]
    if ctx.lock_attempts:
        n = ctx.lock_attempts
        rules.append(_case(
            "login.lockout", "login", f"连续失败 {n} 次触发锁定",
            [f"使用错误密码连续登录 {n} 次", "再用正确密码登录"],
            ["账号被锁定并提示解锁时间", "锁定期间正确密码也无法登录"], "P1", "边界值分析"))
        if n > 1:
            rules.append(_case(
                "login.below_lockout", "login", f"连续失败 {n - 1} 次不锁定",
                [f"使用错误密码连续登录 {n - 1} 次", "再用正确密码登录"],
                ["登录成功，失败次数被重置"], "P2", "边界值分析"))
    return rules


def _form_rules(ctx: RuleContext) -> List[Dict[str, Any]]:
    limit = ctx.max_length
    rules = [
        _case("form.valid", "form", "所有字段填写合法值后提交",
              ["按要求填写所有必填字段", "提交"],
              ["提交成功并给出成功反馈"], "P1"),
        _case("form.required_empty", "form", "必填字段为空时提交",
              ["保留一个必填字段为空", "提交"],
              ["阻止提交并标出缺失字段"], "P1"),
        _case("form.overlong", "form", f"字段超过 {limit} 个字符",
              [f"在文本字段输入 {limit + 1} 个字符", "提交"],
              ["给出长度提示或截断，数据不被写坏"], "P2", "边界值分析"),
        _case("form.special_chars", "form", "字段输入脚本和特殊字符",
              ["在文本字段输入 <script>alert(1)</script>", "提交后查看回显"],
              ["内容按文本显示，不执行脚本"], "P2", "错误推测"),
        _case("form.double_submit", "form", "重复点击提交",
              ["填写合法值", "快速连续点击提交 3 次"],
              ["只生成一条记录"], "P2", "错误推测"),
    ]
    if ctx.explicit_max_length:
        rules.insert(2, _case(
            "form.max_length", "form", f"字段恰好 {limit} 个字符",
            [f"在文本字段输入 {limit} 个字符", "提交"],
            ["提交成功，内容完整保存"], "P2", "边界值分析"))
    return rules


_RULE_BUILDERS = {"search": _search_rules, "login": _login_rules, "form": _form_rules}


def build_rule_cases(requirement_text: str) -> Dict[str, Any]:
    """返回 {scenarios, criteria, cases, max_length, lock_attempts}。未识别场景时 cases 为空。"""
    ctx = build_context(requirement_text)
    cases: List[Dict[str, Any]] = []
    for key in ctx.scenarios:
        cases.extend(_RULE_BUILDERS[key](ctx))
    return {
        "scenarios": ctx.scenarios,
        "criteria": extract_acceptance_criteria(requirement_text),
        "cases": cases,
        "max_length": ctx.max_length if ctx.explicit_max_length else None,
        "lock_attempts": ctx.lock_attempts,
    }


def _bigrams(text: str) -> set[str]:
    compact = re.sub(r"\s+", "", str(text or "").lower())
    if len(compact) < 2:
        return {compact} if compact else set()
    return {compact[i:i + 2] for i in range(len(compact) - 1)}


def overlap_score(criterion: str, case_text: str) -> float:
    """验收点的二字片段有多少落在用例文本里，0–1。"""
    crit = _bigrams(criterion)
    if not crit:
        return 0.0
    return len(crit & _bigrams(case_text)) / len(crit)
