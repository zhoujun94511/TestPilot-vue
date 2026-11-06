#!/usr/bin/python
# -*- coding: utf-8 -*-
from flask import Flask

from models.models import db


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


def test_quick_reply_feedback_ignores_body_user_id(monkeypatch):
    import blueprints.chat as chat_module

    recorded = []

    class FakeGenerator:
        @staticmethod
        def update_user_preferences(user_id, _text, _clicked):
            recorded.append(user_id)

    monkeypatch.setattr(chat_module, "SmartQuickReplyGenerator", FakeGenerator)
    monkeypatch.setattr(chat_module, "current_user", lambda: {"id": 7, "role": "user"})

    client = _chat_app().test_client()
    resp = client.post("/api/chat/quick-reply/feedback", json={
        "suggestion_text": "继续",
        "was_clicked": True,
        "user_id": "999",
    })

    assert resp.status_code == 200
    assert recorded == ["7"]


def test_chat_sessions_per_page_is_capped():
    client = _chat_app().test_client()
    resp = client.get("/api/chat/sessions?per_page=100000")
    assert resp.status_code == 200
    assert resp.get_json()["pagination"]["per_page"] == 200
