from flask import Flask

from config.settings import settings
from blueprints.experimental_actions import experimental_actions_bp
from models.models import db, TestCase


def _build_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
    app.register_blueprint(experimental_actions_bp)
    return app


def _insert_case(app: Flask, case_id: str = "TC-EXP-01") -> None:
    with app.app_context():
        row = TestCase(
            case_id=case_id,
            title="exp delete target",
            description="for experimental action tests",
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


def test_experimental_execute_confirm_and_query():
    old_flag = getattr(settings, "ENABLE_EXPERIMENTAL_ACTIONS", False)
    settings.ENABLE_EXPERIMENTAL_ACTIONS = True
    try:
        app = _build_app()
        _insert_case(app, "TC-EXP-01")
        client = app.test_client()

        execute_resp = client.post("/api/experimental-actions/execute", json={
            "query": "删除用例 TC-EXP-01",
            "metadata": {"operator_role": "admin"},
        })
        assert execute_resp.status_code == 202
        execute_payload = execute_resp.get_json()
        assert execute_payload["success"] is True
        assert execute_payload["status"] == "needs_confirmation"
        assert execute_payload["plan"]["tool_name"] == "delete_case"

        execution_id = execute_payload["execution_id"]
        detail_resp = client.get(f"/api/experimental-actions/execution/{execution_id}")
        assert detail_resp.status_code == 200
        detail_payload = detail_resp.get_json()
        assert detail_payload["success"] is True
        assert detail_payload["execution"]["status"] == "needs_confirmation"

        confirm_resp = client.post("/api/experimental-actions/confirm", json={
            "execution_id": execution_id,
            "metadata": {"operator_role": "admin"},
        })
        assert confirm_resp.status_code == 200
        confirm_payload = confirm_resp.get_json()
        assert confirm_payload["success"] is True
        assert confirm_payload["status"] == "done"
        assert confirm_payload["tool_output"]["deleted"] is True
    finally:
        settings.ENABLE_EXPERIMENTAL_ACTIONS = old_flag


def test_experimental_cancel_flow():
    old_flag = getattr(settings, "ENABLE_EXPERIMENTAL_ACTIONS", False)
    settings.ENABLE_EXPERIMENTAL_ACTIONS = True
    try:
        app = _build_app()
        _insert_case(app, "TC-EXP-02")
        client = app.test_client()

        execute_resp = client.post("/api/experimental-actions/execute", json={
            "query": "删除用例 TC-EXP-02",
            "metadata": {"operator_role": "admin"},
        })
        assert execute_resp.status_code == 202
        execution_id = execute_resp.get_json()["execution_id"]

        cancel_resp = client.post("/api/experimental-actions/cancel", json={
            "execution_id": execution_id,
            "reason": "manual_abort",
        })
        assert cancel_resp.status_code == 200
        cancel_payload = cancel_resp.get_json()
        assert cancel_payload["success"] is True
        assert cancel_payload["status"] == "cancelled"
    finally:
        settings.ENABLE_EXPERIMENTAL_ACTIONS = old_flag


def test_experimental_generate_cases_action_without_model():
    old_flag = getattr(settings, "ENABLE_EXPERIMENTAL_ACTIONS", False)
    settings.ENABLE_EXPERIMENTAL_ACTIONS = True
    try:
        app = _build_app()
        client = app.test_client()
        resp = client.post("/api/experimental-actions/execute", json={
            "query": "请生成测试用例：登录功能",
            "metadata": {"case_count": 3}
        })
        assert resp.status_code == 500
        payload = resp.get_json()
        assert payload["success"] is False
        assert payload["plan"]["tool_name"] == "generate_cases"
    finally:
        settings.ENABLE_EXPERIMENTAL_ACTIONS = old_flag

