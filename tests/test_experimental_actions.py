import json

import pytest
from flask import Flask

from config.settings import settings
from blueprints.experimental_actions import clear_rate_limit_for_tests, experimental_actions_bp
from models.models import db, TestCase, Requirement, ToolExecutionLog


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    clear_rate_limit_for_tests()
    yield
    clear_rate_limit_for_tests()

SEARCH_REQUIREMENT = (
    "用户可以通过搜索框搜索商品，关键词最多 50 个字符。\n"
    "1. 系统展示符合条件的搜索结果\n"
    "2. 结果按销量排序"
)


class _FakeLLM:
    def __init__(self, content):
        self.content = content
        self.calls = 0

    def invoke(self, _prompt):
        self.calls += 1
        return type("Resp", (), {"content": self.content})()


def _build_app(llm=None):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
    app.register_blueprint(experimental_actions_bp)
    app.llm_case_generation = llm
    return app


def _insert_requirement(app, req_id="REQ-SEARCH-01", content=SEARCH_REQUIREMENT):
    with app.app_context():
        db.session.add(Requirement(req_id=req_id, title="商品搜索", content=content))
        db.session.commit()


def _insert_case(app, case_id, title, steps, expected, requirement_id=None):
    with app.app_context():
        db.session.add(TestCase(
            case_id=case_id,
            title=title,
            steps=json.dumps(steps, ensure_ascii=False),
            expected_result=json.dumps(expected, ensure_ascii=False),
            priority="P2",
            category="functional",
            status="draft",
            created_by="tester",
            requirement_id=requirement_id,
        ))
        db.session.commit()


def _enable(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_REQUIRE_AUTH", False)
    monkeypatch.setattr(settings, "ENABLE_EXPERIMENTAL_ACTIONS", True)


def test_health_lists_only_new_tools(monkeypatch):
    _enable(monkeypatch)
    client = _build_app().test_client()
    tools = client.get("/api/experimental-actions/health").get_json()["tools"]
    assert set(tools) == {"rule_skeleton_cases", "ac_coverage_review", "trace_matrix"}
    assert tools["rule_skeleton_cases"] == "medium"


def test_removed_tools_are_unknown(monkeypatch):
    _enable(monkeypatch)
    client = _build_app().test_client()
    for name in ("list_cases", "generate_cases", "delete_case", "search_knowledge"):
        resp = client.post("/api/experimental-actions/execute", json={"query": "x", "tool_name": name, "args": {}})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "unknown_tool"


def test_rule_skeleton_preview_then_confirm_saves_preview(monkeypatch):
    _enable(monkeypatch)
    llm = _FakeLLM('```json\n[{"title": "按销量排序展示结果", "steps": ["搜索手机", "查看排序"], '
                   '"expected_result": ["销量高的在前"], "priority": "P1", "covers": "结果按销量排序"}]\n```')
    app = _build_app(llm)
    _insert_requirement(app)
    client = app.test_client()

    resp = client.post("/api/experimental-actions/execute", json={
        "query": "[rule_skeleton_cases]",
        "tool_name": "rule_skeleton_cases",
        "args": {"requirement_id": "REQ-SEARCH-01", "case_count": 3, "use_llm": True,
                 "save": True, "preview_cases": [{"title": "forged"}]},
    })
    assert resp.status_code == 202
    payload = resp.get_json()
    assert payload["status"] == "needs_confirmation"
    output = payload["tool_output"]
    assert output["dry_run"] is True
    assert output["scenarios"] == ["search"]
    assert output["max_length"] == 50
    titles = [case["title"] for case in output["cases"]]
    assert "搜索：输入超长字符串（51 个字符）" in titles
    assert output["llm_count"] == 1
    assert "preview_cases" not in payload["plan"]["args"]
    with app.app_context():
        assert TestCase.query.count() == 0

    confirm = client.post("/api/experimental-actions/confirm", json={"execution_id": payload["execution_id"]})
    assert confirm.status_code == 200
    saved = confirm.get_json()["tool_output"]
    assert saved["dry_run"] is False
    assert saved["count"] == len(output["cases"])
    assert llm.calls == 1
    with app.app_context():
        rows = TestCase.query.all()
        assert len(rows) == len(output["cases"])
        assert {row.requirement_id for row in rows} == {"REQ-SEARCH-01"}
        assert "forged" not in {row.title for row in rows}
        record = ToolExecutionLog.query.filter_by(execution_id=payload["execution_id"]).one()
        assert record.status == "done"

    again = client.post("/api/experimental-actions/confirm", json={"execution_id": payload["execution_id"]})
    assert again.status_code == 400
    with app.app_context():
        assert TestCase.query.count() == len(output["cases"])


def test_rule_skeleton_without_model_still_returns_rules(monkeypatch):
    _enable(monkeypatch)
    client = _build_app(None).test_client()
    resp = client.post("/api/experimental-actions/execute", json={
        "query": "[rule_skeleton_cases]",
        "tool_name": "rule_skeleton_cases",
        "args": {"requirement_text": "登录时密码错误 5 次锁定 30 分钟", "use_llm": True},
    })
    assert resp.status_code == 202
    output = resp.get_json()["tool_output"]
    assert output["llm_count"] == 0
    assert output["llm_note"]
    titles = [case["title"] for case in output["cases"]]
    assert "登录：连续失败 5 次触发锁定" in titles
    assert "登录：连续失败 4 次不锁定" in titles


def test_rule_skeleton_unknown_requirement_returns_reason(monkeypatch):
    _enable(monkeypatch)
    client = _build_app().test_client()
    resp = client.post("/api/experimental-actions/execute", json={
        "query": "[rule_skeleton_cases]",
        "tool_name": "rule_skeleton_cases",
        "args": {"requirement_id": "REQ-NOPE"},
    })
    assert resp.status_code == 422
    assert resp.get_json()["message"] == "需求不存在"


def test_coverage_review_lists_gaps_and_structure(monkeypatch):
    _enable(monkeypatch)
    app = _build_app()
    _insert_requirement(app)
    _insert_case(app, "TC-COV-1", "搜索结果展示", ["输入手机", "执行搜索"],
                 ["系统展示符合条件的搜索结果"], "REQ-SEARCH-01")
    _insert_case(app, "TC-COV-2", "空", ["检查"], [], "REQ-SEARCH-01")
    _insert_case(app, "TC-OTHER", "按销量排序", ["结果按销量排序"], ["ok"], None)
    client = app.test_client()

    resp = client.post("/api/experimental-actions/execute", json={
        "query": "[ac_coverage_review]",
        "tool_name": "ac_coverage_review",
        "args": {"requirement_id": "REQ-SEARCH-01"},
    })
    assert resp.status_code == 200
    output = resp.get_json()["tool_output"]
    assert output["case_count"] == 2
    by_text = {row["criterion"]: row for row in output["criteria"]}
    assert by_text["系统展示符合条件的搜索结果"]["covered"] is True
    assert by_text["系统展示符合条件的搜索结果"]["case_id"] == "TC-COV-1"
    assert "结果按销量排序" in output["gaps"]
    issues = {item["case_id"]: item["issues"] for item in output["structure_issues"]}
    assert set(issues["TC-COV-2"]) >= {"title_too_short", "steps_too_few", "steps_vague", "expected_missing"}


def test_trace_matrix_groups(monkeypatch):
    _enable(monkeypatch)
    app = _build_app()
    _insert_requirement(app, "REQ-A")
    _insert_requirement(app, "REQ-B")
    _insert_case(app, "TC-A", "a", ["s1", "s2"], ["e"], "REQ-A")
    _insert_case(app, "TC-GHOST", "ghost", ["s1", "s2"], ["e"], "REQ-GONE")
    _insert_case(app, "TC-FREE", "free", ["s1", "s2"], ["e"], None)
    client = app.test_client()

    resp = client.post("/api/experimental-actions/execute", json={
        "query": "[trace_matrix]",
        "tool_name": "trace_matrix",
        "args": {"limit": 10},
    })
    assert resp.status_code == 200
    output = resp.get_json()["tool_output"]
    assert [row["req_id"] for row in output["requirements_without_cases"]] == ["REQ-B"]
    assert [row["case_id"] for row in output["cases_with_missing_requirement"]] == ["TC-GHOST"]
    assert [row["case_id"] for row in output["cases_unlinked"]] == ["TC-FREE"]
    assert output["requirements_with_cases"][0] == {"req_id": "REQ-A", "title": "商品搜索", "case_count": 1}


def test_criteria_keep_decimal_numbers():
    from experiments.action_runtime.rule_skeleton import extract_acceptance_criteria

    assert extract_acceptance_criteria("2.5 秒内返回结果\n1. 支持翻页") == ["2.5 秒内返回结果", "支持翻页"]


def test_unknown_args_are_ignored(monkeypatch):
    _enable(monkeypatch)
    client = _build_app().test_client()
    resp = client.post("/api/experimental-actions/execute", json={
        "query": "[trace_matrix]",
        "tool_name": "trace_matrix",
        "args": {"limit": 5, "case_id": "TC-OLD"},
    })
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "done"


def test_cancel_skeleton_preview(monkeypatch):
    _enable(monkeypatch)
    app = _build_app()
    client = app.test_client()
    resp = client.post("/api/experimental-actions/execute", json={
        "query": "[rule_skeleton_cases]",
        "tool_name": "rule_skeleton_cases",
        "args": {"requirement_text": "提交注册表单", "use_llm": False},
    })
    assert resp.status_code == 202
    cancel = client.post("/api/experimental-actions/cancel", json={
        "execution_id": resp.get_json()["execution_id"],
        "reason": "manual_abort",
    })
    assert cancel.status_code == 200
    assert cancel.get_json()["status"] == "cancelled"
    with app.app_context():
        assert TestCase.query.count() == 0
