#!/usr/bin/python
# -*- coding: utf-8 -*-
import time

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from config.settings import settings
from experiments.action_runtime.orchestrator import ExperimentalActionOrchestrator
from experiments.action_runtime.schemas import ActionRequest
from experiments.action_runtime.validation import (
    ExecuteRequestModel,
    ConfirmRequestModel,
    CancelRequestModel,
)
from models.models import ToolExecutionLog

experimental_actions_bp = Blueprint("experimental_actions", __name__, url_prefix="/api/experimental-actions")
orchestrator = ExperimentalActionOrchestrator()
_RATE_BUCKET: dict[str, list] = {}
_RATE_LIMIT_MAX = 12
_RATE_LIMIT_WINDOW_SECONDS = 60


def _ensure_enabled():
    if not getattr(settings, "ENABLE_EXPERIMENTAL_ACTIONS", False):
        return jsonify({
            "success": False,
            "message": "experimental actions disabled",
            "error": "feature_disabled",
        }), 403
    return None


def _persist_action_chat_message(result):
    """把确认或取消结果写入聊天记录，刷新后仍能看到。"""
    if getattr(result, "status", "") not in ("done", "failed", "cancelled"):
        return
    if getattr(result, "error", None) == "confirmation_required":
        return
    record = ToolExecutionLog.query.filter_by(execution_id=result.execution_id).first()
    session_id = getattr(record, "session_id", None) if record else None
    if not session_id:
        return
    try:
        from datetime import datetime, timezone
        from models.models import db, ChatHistory
        from services.action_message_service import build_compact_action_history_content

        db.session.add(ChatHistory(
            session_id=session_id,
            role="system",
            content=build_compact_action_history_content(result),
            message_type="action",
            created_time=datetime.now(timezone.utc),
        ))
        db.session.commit()
    except (SQLAlchemyError, TypeError, ValueError):
        from models.models import db
        db.session.rollback()


def _serialize_result(result):
    return {
        "success": result.success,
        "execution_id": result.execution_id,
        "status": result.status,
        "message": result.message,
        "plan": {
            "intent": result.plan.intent if result.plan else None,
            "tool_name": result.plan.tool_name if result.plan else None,
            "args": result.plan.args if result.plan else None,
            "risk_level": result.plan.risk_level if result.plan else None,
            "requires_confirmation": result.plan.requires_confirmation if result.plan else None,
            "reason": result.plan.reason if result.plan else None,
        } if result.plan else None,
        "tool_output": result.tool_output,
        "error": result.error,
        "created_at": result.created_at,
    }


def _rate_limit_key() -> str:
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr or "unknown"
    user_id = request.headers.get("X-Operator", "").strip() or "anonymous"
    return f"{client_ip}:{user_id}"


def _enforce_rate_limit():
    now = time.time()
    key = _rate_limit_key()
    bucket = _RATE_BUCKET.get(key, [])
    bucket = [ts for ts in bucket if now - ts <= _RATE_LIMIT_WINDOW_SECONDS]
    if len(bucket) >= _RATE_LIMIT_MAX:
        return jsonify({
            "success": False,
            "message": "请求过于频繁，请稍后重试",
            "error": "rate_limit_exceeded",
            "limit": _RATE_LIMIT_MAX,
            "window_seconds": _RATE_LIMIT_WINDOW_SECONDS,
        }), 429
    bucket.append(now)
    _RATE_BUCKET[key] = bucket
    return None


@experimental_actions_bp.route("/health", methods=["GET"])
def health():
    disabled_response = _ensure_enabled()
    if disabled_response:
        return disabled_response
    return jsonify({
        "success": True,
        "message": "experimental actions enabled",
        "tools": orchestrator.registry.list_tools(),
    })


@experimental_actions_bp.route("/execute", methods=["POST"])
def execute():
    disabled_response = _ensure_enabled()
    if disabled_response:
        return disabled_response
    limited_response = _enforce_rate_limit()
    if limited_response:
        return limited_response

    payload = request.get_json() or {}
    try:
        body = ExecuteRequestModel.model_validate(payload)
    except ValidationError as exc:
        return jsonify({
            "success": False,
            "message": "请求参数校验失败",
            "error": "bad_request",
            "details": exc.errors(),
        }), 400

    action_request = ActionRequest(
        query=body.query,
        session_id=body.session_id,
        user_id=body.user_id,
        require_confirmation=bool(body.require_confirmation),
        metadata=body.metadata if isinstance(body.metadata, dict) else {},
    )
    result = orchestrator.run(action_request)
    status_code = 200 if result.success else 500
    if result.status == "needs_confirmation":
        status_code = 202
    if result.status == "denied":
        status_code = 403
    return jsonify(_serialize_result(result)), status_code


@experimental_actions_bp.route("/confirm", methods=["POST"])
def confirm_execution():
    disabled_response = _ensure_enabled()
    if disabled_response:
        return disabled_response
    limited_response = _enforce_rate_limit()
    if limited_response:
        return limited_response

    payload = request.get_json() or {}
    try:
        body = ConfirmRequestModel.model_validate(payload)
    except ValidationError as exc:
        return jsonify({
            "success": False,
            "message": "请求参数校验失败",
            "error": "bad_request",
            "details": exc.errors(),
        }), 400

    result = orchestrator.confirm(execution_id=body.execution_id, metadata=body.metadata)
    _persist_action_chat_message(result)
    return jsonify(_serialize_result(result)), (200 if result.success else 400)


@experimental_actions_bp.route("/cancel", methods=["POST"])
def cancel_execution():
    disabled_response = _ensure_enabled()
    if disabled_response:
        return disabled_response
    limited_response = _enforce_rate_limit()
    if limited_response:
        return limited_response

    payload = request.get_json() or {}
    try:
        body = CancelRequestModel.model_validate(payload)
    except ValidationError as exc:
        return jsonify({
            "success": False,
            "message": "请求参数校验失败",
            "error": "bad_request",
            "details": exc.errors(),
        }), 400

    result = orchestrator.cancel(execution_id=body.execution_id, reason=body.reason)
    _persist_action_chat_message(result)
    return jsonify(_serialize_result(result)), (200 if result.success else 400)


@experimental_actions_bp.route("/execution/<string:execution_id>", methods=["GET"])
def get_execution(execution_id: str):
    disabled_response = _ensure_enabled()
    if disabled_response:
        return disabled_response

    target_id = str(execution_id or "").strip()
    if not target_id:
        return jsonify({
            "success": False,
            "message": "execution_id不能为空",
            "error": "bad_request",
        }), 400

    record = ToolExecutionLog.query.filter_by(execution_id=target_id).first()
    if not record:
        return jsonify({
            "success": False,
            "message": "执行记录不存在",
            "error": "not_found",
        }), 404
    return jsonify({
        "success": True,
        "execution": record.to_dict(),
    }), 200

