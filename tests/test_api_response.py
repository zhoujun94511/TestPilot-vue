from flask import Flask, jsonify

from utils.utils_core.api_response import (
    api_error,
    api_success,
    normalize_api_response_payload,
)
from utils.utils_core.error_handler import ErrorHandler


def test_api_success_shape():
    app = Flask(__name__)
    with app.app_context():
        response, status = api_success(
            data={"ok": True},
            code="CONFIG_SAVE_SUCCESS",
            message_key="config.message.saveSuccess",
            message="Configuration saved successfully",
        )
        payload = response.get_json()

    assert status == 200
    assert payload["success"] is True
    assert payload["code"] == "CONFIG_SAVE_SUCCESS"
    assert payload["message_key"] == "config.message.saveSuccess"
    assert payload["message"] == "Configuration saved successfully"
    assert payload["data"] == {"ok": True}


def test_api_error_shape():
    app = Flask(__name__)
    with app.app_context():
        response, status = api_error(
            code="DOCUMENT_UPLOAD_FAILED",
            message_key="documents.message.uploadFailed",
            message="Document upload failed",
            status=500,
            details={"reason": "disk full"},
        )
        payload = response.get_json()

    assert status == 500
    assert payload["success"] is False
    assert payload["code"] == "DOCUMENT_UPLOAD_FAILED"
    assert payload["message_key"] == "documents.message.uploadFailed"
    assert payload["message"] == "Document upload failed"
    assert payload["details"] == {"reason": "disk full"}


def test_normalize_legacy_payload_uses_route_map():
    payload = {
        "success": True,
        "message": "文件上传成功",
        "data": {"filename": "demo.txt"},
    }

    normalized = normalize_api_response_payload(
        payload,
        path="/api/documents/upload",
        method="POST",
        status_code=200,
    )

    assert normalized["success"] is True
    assert normalized["code"] == "DOCUMENT_UPLOAD_SUCCESS"
    assert normalized["message_key"] == "documents.message.uploadSuccess"
    assert normalized["message"] == "Document uploaded successfully"
    assert normalized["data"] == {"filename": "demo.txt"}


def test_normalize_legacy_error_payload_uses_english_fallback():
    payload = {
        "success": False,
        "message": "获取模型状态失败: timeout",
    }

    normalized = normalize_api_response_payload(
        payload,
        path="/api/model-status",
        method="GET",
        status_code=500,
    )

    assert normalized["success"] is False
    assert normalized["code"] == "MODEL_STATUS_FAILED"
    assert normalized["message_key"] == "model.message.statusFailed"
    assert normalized["message"] == "Failed to load model status"


def test_normalize_via_flask_after_request():
    app = Flask(__name__)

    @app.after_request
    def normalize(flask_response):
        if flask_response.is_json:
            legacy_payload = flask_response.get_json()
            normalized = normalize_api_response_payload(
                legacy_payload,
                path="/api/chat/message",
                method="POST",
                status_code=flask_response.status_code,
            )
            new_response = jsonify(normalized)
            new_response.status_code = flask_response.status_code
            return new_response
        return flask_response

    @app.route("/api/chat/message", methods=["POST"])
    def legacy_chat():
        return jsonify({"success": False, "message": "聊天消息发送失败"})

    client = app.test_client()
    response = client.post("/api/chat/message")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is False
    assert payload["code"] == "CHAT_MESSAGE_FAILED"
    assert payload["message_key"] == "chat.message.sendFailed"
    assert payload["message"] == "Failed to send message"


def test_normalize_nested_system_status_values():
    payload = {
        "success": True,
        "system": {
            "ai_service": {"status": "在线", "model": "gpt-5"},
            "knowledge": {"status": "异常", "docs": 12},
            "performance": {"status": "良好", "cpu": 12.5},
        },
    }

    normalized = normalize_api_response_payload(
        payload,
        path="/api/stats/system-status",
        method="GET",
        status_code=200,
    )

    assert normalized["system"]["ai_service"]["status"] == "online"
    assert normalized["system"]["ai_service"]["status_key"] == "enums.status.online"
    assert normalized["system"]["knowledge"]["status"] == "abnormal"
    assert normalized["system"]["knowledge"]["status_key"] == "enums.status.abnormal"
    assert normalized["system"]["performance"]["status"] == "good"
    assert normalized["system"]["performance"]["status_key"] == "enums.status.good"


def test_error_handler_uses_english_messages():
    result = ErrorHandler.handle_document_analysis_error(
        Exception("Unsupported file format"),
        "demo.txt",
    )

    assert result["error_code"] == "UNSUPPORTED_FORMAT"
    assert result["message_key"] == "errors.document.unsupportedFormat"
    assert "Unsupported file format" in result["user_message"]
