#!/usr/bin/python
# -*- coding: utf-8 -*-
"""聊天通道与实验动作通道分离。"""

from flask import Flask

from blueprints.experimental_actions import experimental_actions_bp
from config.settings import settings
from models.models import ChatHistory, db, TestCase


def _chat_app():
    from blueprints.chat import chat_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
    return app


def _experimental_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
    app.register_blueprint(experimental_actions_bp)
    return app


def _insert_case(app: Flask, case_id: str) -> None:
    with app.app_context():
        row = TestCase(
            case_id=case_id,
            title="channel test",
            description="",
            precondition="",
            steps="[]",
            expected_result="[]",
            priority="P2",
            category="functional",
            tags="",
            status="draft",
            created_by="tester",
        )
        db.session.add(row)
        db.session.commit()


def test_chat_message_rejects_action_mode():
    app = _chat_app()
    client = app.test_client()
    resp = client.post("/api/chat/message", json={
        "message": "列出用例",
        "mode": "action",
    })
    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload.get("error") == "action_mode_not_supported"
    assert payload.get("error_code") == "ACTION_MODE_NOT_SUPPORTED"
    assert payload.get("experimental_actions", {}).get("execute") == "/api/experimental-actions/execute"
    assert "experimental-actions" in (payload.get("message") or "")


def test_chat_stream_post_rejects_action_mode():
    app = _chat_app()
    client = app.test_client()
    resp = client.post("/api/chat/stream", json={
        "message": "hello",
        "mode": "action",
    })
    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload.get("error") == "action_mode_not_supported"


def test_chat_stream_get_rejects_action_mode():
    app = _chat_app()
    client = app.test_client()
    resp = client.get("/api/chat/stream?message=hello&mode=action")
    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload.get("error") == "action_mode_not_supported"


def test_experimental_health_reports_explicit_only(monkeypatch):
    old_flag = getattr(settings, "ENABLE_EXPERIMENTAL_ACTIONS", False)
    old_nl = getattr(settings, "EXPERIMENTAL_ACTIONS_ALLOW_NL", False)
    old_auth = getattr(settings, "AUTH_REQUIRE_AUTH", False)
    monkeypatch.setattr(settings, "AUTH_REQUIRE_AUTH", False)
    settings.ENABLE_EXPERIMENTAL_ACTIONS = True
    settings.EXPERIMENTAL_ACTIONS_ALLOW_NL = False
    try:
        app = _experimental_app()
        client = app.test_client()
        resp = client.get("/api/experimental-actions/health")
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload.get("explicit_only") is True
        assert payload.get("allow_nl") is False
        assert isinstance(payload.get("tools"), dict)
    finally:
        settings.ENABLE_EXPERIMENTAL_ACTIONS = old_flag
        settings.EXPERIMENTAL_ACTIONS_ALLOW_NL = old_nl
        settings.AUTH_REQUIRE_AUTH = old_auth


def test_experimental_execute_rejects_unknown_tool_name(monkeypatch):
    old_flag = getattr(settings, "ENABLE_EXPERIMENTAL_ACTIONS", False)
    old_nl = getattr(settings, "EXPERIMENTAL_ACTIONS_ALLOW_NL", False)
    old_auth = getattr(settings, "AUTH_REQUIRE_AUTH", False)
    monkeypatch.setattr(settings, "AUTH_REQUIRE_AUTH", False)
    settings.ENABLE_EXPERIMENTAL_ACTIONS = True
    settings.EXPERIMENTAL_ACTIONS_ALLOW_NL = False
    try:
        app = _experimental_app()
        client = app.test_client()
        resp = client.post("/api/experimental-actions/execute", json={
            "query": "列出最近 3 条用例",
            "tool_name": "not_registered_tool",
            "args": {},
        })
        assert resp.status_code == 400
        payload = resp.get_json()
        assert payload.get("error") == "unknown_tool"
    finally:
        settings.ENABLE_EXPERIMENTAL_ACTIONS = old_flag
        settings.EXPERIMENTAL_ACTIONS_ALLOW_NL = old_nl
        settings.AUTH_REQUIRE_AUTH = old_auth


def test_experimental_execute_rejects_without_tool_name_by_default(monkeypatch):
    old_flag = getattr(settings, "ENABLE_EXPERIMENTAL_ACTIONS", False)
    old_nl = getattr(settings, "EXPERIMENTAL_ACTIONS_ALLOW_NL", False)
    old_auth = getattr(settings, "AUTH_REQUIRE_AUTH", False)
    monkeypatch.setattr(settings, "AUTH_REQUIRE_AUTH", False)
    settings.ENABLE_EXPERIMENTAL_ACTIONS = True
    settings.EXPERIMENTAL_ACTIONS_ALLOW_NL = False
    try:
        app = _experimental_app()
        client = app.test_client()
        resp = client.post("/api/experimental-actions/execute", json={
            "query": "帮我为登录功能设计测试用例",
        })
        assert resp.status_code == 400
        payload = resp.get_json()
        assert payload.get("error") == "explicit_tool_required"
    finally:
        settings.ENABLE_EXPERIMENTAL_ACTIONS = old_flag
        settings.EXPERIMENTAL_ACTIONS_ALLOW_NL = old_nl
        settings.AUTH_REQUIRE_AUTH = old_auth


def test_experimental_design_cases_query_skips_tools_when_nl_enabled(monkeypatch):
    old_flag = getattr(settings, "ENABLE_EXPERIMENTAL_ACTIONS", False)
    old_nl = getattr(settings, "EXPERIMENTAL_ACTIONS_ALLOW_NL", False)
    old_auth = getattr(settings, "AUTH_REQUIRE_AUTH", False)
    monkeypatch.setattr(settings, "AUTH_REQUIRE_AUTH", False)
    settings.ENABLE_EXPERIMENTAL_ACTIONS = True
    settings.EXPERIMENTAL_ACTIONS_ALLOW_NL = True
    try:
        app = _experimental_app()
        _insert_case(app, "TC-CHAN-SKIP-01")
        client = app.test_client()
        resp = client.post("/api/experimental-actions/execute", json={
            "query": "帮我为登录功能设计测试用例",
        })
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["success"] is True
        assert payload["status"] == "skipped"
        plan = payload.get("plan") or {}
        assert not plan.get("tool_name")
    finally:
        settings.ENABLE_EXPERIMENTAL_ACTIONS = old_flag
        settings.EXPERIMENTAL_ACTIONS_ALLOW_NL = old_nl
        settings.AUTH_REQUIRE_AUTH = old_auth


def test_experimental_trace_nl_when_allow_nl_enabled(monkeypatch):
    old_flag = getattr(settings, "ENABLE_EXPERIMENTAL_ACTIONS", False)
    old_nl = getattr(settings, "EXPERIMENTAL_ACTIONS_ALLOW_NL", False)
    old_auth = getattr(settings, "AUTH_REQUIRE_AUTH", False)
    monkeypatch.setattr(settings, "AUTH_REQUIRE_AUTH", False)
    settings.ENABLE_EXPERIMENTAL_ACTIONS = True
    settings.EXPERIMENTAL_ACTIONS_ALLOW_NL = True
    try:
        app = _experimental_app()
        _insert_case(app, "TC-CHAN-LIST-01")
        client = app.test_client()
        resp = client.post("/api/experimental-actions/execute", json={
            "query": "做一次需求追溯",
        })
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["success"] is True
        assert payload["status"] == "done"
        assert payload["plan"]["tool_name"] == "trace_matrix"
    finally:
        settings.ENABLE_EXPERIMENTAL_ACTIONS = old_flag
        settings.EXPERIMENTAL_ACTIONS_ALLOW_NL = old_nl
        settings.AUTH_REQUIRE_AUTH = old_auth


def test_experimental_panel_requires_tool_name(monkeypatch):
    old_flag = getattr(settings, "ENABLE_EXPERIMENTAL_ACTIONS", False)
    old_auth = getattr(settings, "AUTH_REQUIRE_AUTH", False)
    monkeypatch.setattr(settings, "AUTH_REQUIRE_AUTH", False)
    settings.ENABLE_EXPERIMENTAL_ACTIONS = True
    try:
        app = _experimental_app()
        client = app.test_client()
        resp = client.post("/api/experimental-actions/execute", json={
            "query": "panel run",
            "metadata": {"send_source": "experimental_tool_panel"},
        })
        assert resp.status_code == 400
        assert resp.get_json().get("error") == "explicit_tool_required"
    finally:
        settings.ENABLE_EXPERIMENTAL_ACTIONS = old_flag
        settings.AUTH_REQUIRE_AUTH = old_auth


def test_experimental_execute_persists_chat_history(monkeypatch):
    old_flag = getattr(settings, "ENABLE_EXPERIMENTAL_ACTIONS", False)
    old_auth = getattr(settings, "AUTH_REQUIRE_AUTH", False)
    monkeypatch.setattr(settings, "AUTH_REQUIRE_AUTH", False)
    settings.ENABLE_EXPERIMENTAL_ACTIONS = True
    session_id = "sess-exp-persist-01"
    try:
        app = _experimental_app()
        _insert_case(app, "TC-CHAN-PERSIST-01")
        client = app.test_client()
        resp = client.post("/api/experimental-actions/execute", json={
            "query": "[trace_matrix] panel",
            "session_id": session_id,
            "tool_name": "trace_matrix",
            "args": {"limit": 1},
            "metadata": {"send_source": "experimental_tool_panel"},
        })
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["success"] is True
        assert payload["status"] == "done"
        with app.app_context():
            rows = ChatHistory.query.filter_by(session_id=session_id, message_type="action").all()
            assert len(rows) == 1
            assert rows[0].role == "system"
            assert "trace_matrix" in (rows[0].content or "")
            assert "1 条用例未关联需求" in (rows[0].content or "")
    finally:
        settings.ENABLE_EXPERIMENTAL_ACTIONS = old_flag
        settings.AUTH_REQUIRE_AUTH = old_auth


def test_experimental_execute_with_tool_name(monkeypatch):
    old_flag = getattr(settings, "ENABLE_EXPERIMENTAL_ACTIONS", False)
    old_auth = getattr(settings, "AUTH_REQUIRE_AUTH", False)
    monkeypatch.setattr(settings, "AUTH_REQUIRE_AUTH", False)
    settings.ENABLE_EXPERIMENTAL_ACTIONS = True
    try:
        app = _experimental_app()
        _insert_case(app, "TC-CHAN-EXPLICIT-01")
        client = app.test_client()
        resp = client.post("/api/experimental-actions/execute", json={
            "query": "设计登录用例（显式工具）",
            "tool_name": "trace_matrix",
            "args": {"limit": 2},
        })
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["success"] is True
        assert payload["status"] == "done"
        assert payload["plan"]["tool_name"] == "trace_matrix"
    finally:
        settings.ENABLE_EXPERIMENTAL_ACTIONS = old_flag
        settings.AUTH_REQUIRE_AUTH = old_auth
