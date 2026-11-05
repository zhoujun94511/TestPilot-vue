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
from services.auth_service import auth_required, current_user

experimental_actions_bp = Blueprint("experimental_actions", __name__, url_prefix="/api/experimental-actions")
orchestrator = ExperimentalActionOrchestrator()
_RATE_BUCKET: dict[str, list] = {}
_RATE_LIMIT_MAX = 12
_RATE_LIMIT_WINDOW_SECONDS = 60


def clear_rate_limit_for_tests() -> None:
    """测试隔离用：清空进程内限流计数。"""
    _RATE_BUCKET.clear()


def _ensure_enabled():
    if not getattr(settings, "ENABLE_EXPERIMENTAL_ACTIONS", True):
        return jsonify({
            "success": False,
            "message": "experimental actions disabled",
            "error": "feature_disabled",
            "message_key": "chat.experimentalTools.errors.featureDisabled",
        }), 403
    return None


def _require_login_when_auth_enabled():
    if auth_required() and current_user() is None:
        return jsonify({
            "success": False,
            "message": "未登录或会话已过期",
            "error": "unauthorized",
        }), 401
    return None


def _resolved_actor_user_id(fallback: str | None) -> str | None:
    """开启认证时强制使用当前登录用户，避免伪造 user_id。"""
    if not auth_required():
        return fallback
    user = current_user()
    if not user:
        return None
    return str(user.get("id"))


def _execution_guard(execution_id: str):
    target_id = str(execution_id or "").strip()
    if not target_id:
        return None, (
            jsonify({
                "success": False,
                "message": "execution_id不能为空",
                "error": "bad_request",
            }),
            400,
        )
    record = ToolExecutionLog.query.filter_by(execution_id=target_id).first()
    if not record:
        return None, (
            jsonify({
                "success": False,
                "message": "执行记录不存在",
                "error": "not_found",
            }),
            404,
        )
    if not can_access_execution(record):
        return None, (
            jsonify({
                "success": False,
                "message": "无权操作该执行记录",
                "error": "forbidden",
            }),
            403,
        )
    return record, None


def can_access_execution(record: ToolExecutionLog) -> bool:
    if not auth_required():
        return True
    user = current_user()
    if not user:
        return False
    if user.get("role") == "super_admin":
        return True
    # 无发起人的记录（匿名模式期间产生）无法判定部门，仅超管可见，上面已放行
    if record.user_id is None or str(record.user_id).strip() == "":
        return False
    return str(record.user_id) == str(user.get("id"))


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
    from services.auth_service import client_ip as resolve_client_ip

    client_ip = resolve_client_ip(request)
    user_id = "anonymous"
    if auth_required():
        user = current_user()
        if user and user.get("id") is not None:
            user_id = str(user.get("id"))
    else:
        user_id = request.headers.get("X-Operator", "").strip() or "anonymous"
    return f"{client_ip}:{user_id}"


def _explicit_tool_required_response(message: str | None = None):
    return jsonify({
        "success": False,
        "message": message or (
            "execute 仅接受显式 tool_name 与 args。"
            "自然语言推断已默认关闭；调试请设置 EXPERIMENTAL_ACTIONS_ALLOW_NL=true。"
        ),
        "error": "explicit_tool_required",
        "error_code": "EXPLICIT_TOOL_REQUIRED",
        "message_key": "chat.experimentalTools.errors.explicitRequired",
    }), 400


def _guard_explicit_execute(metadata: dict):
    tool_name = str(metadata.get("tool_name") or "").strip()
    if tool_name:
        return None
    if getattr(settings, "EXPERIMENTAL_ACTIONS_ALLOW_NL", False):
        return None
    send_source = str(metadata.get("send_source") or "").strip()
    if send_source in ("experimental_tool_panel", "experimental_tool_page"):
        return _explicit_tool_required_response("实验工具请求必须携带 tool_name")
    return _explicit_tool_required_response()


def _guard_registered_tool(metadata: dict):
    tool_name = str(metadata.get("tool_name") or "").strip()
    if not tool_name:
        return None
    if orchestrator.registry.get(tool_name):
        return None
    return jsonify({
        "success": False,
        "message": f"未注册的工具: {tool_name}",
        "error": "unknown_tool",
        "error_code": "UNKNOWN_EXPERIMENTAL_TOOL",
        "message_key": "chat.experimentalTools.errors.unknownTool",
        "message_params": {"tool": tool_name},
    }), 400


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
            "message_key": "chat.experimentalTools.errors.rateLimited",
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
    auth_response = _require_login_when_auth_enabled()
    if auth_response:
        return auth_response
    allow_nl = bool(getattr(settings, "EXPERIMENTAL_ACTIONS_ALLOW_NL", False))
    return jsonify({
        "success": True,
        "message": "experimental actions enabled",
        "tools": orchestrator.registry.list_tools(),
        "allow_nl": allow_nl,
        "explicit_only": not allow_nl,
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

    actor_id = _resolved_actor_user_id(body.user_id)
    if auth_required() and not actor_id:
        return jsonify({
            "success": False,
            "message": "未登录或会话已过期",
            "error": "unauthorized",
        }), 401

    metadata = dict(body.metadata) if isinstance(body.metadata, dict) else {}
    if body.tool_name and str(body.tool_name).strip():
        metadata["tool_name"] = str(body.tool_name).strip()
    if body.args:
        metadata["args"] = dict(body.args)

    blocked = _guard_explicit_execute(metadata)
    if blocked:
        return blocked
    unknown_tool = _guard_registered_tool(metadata)
    if unknown_tool:
        return unknown_tool

    action_request = ActionRequest(
        query=body.query,
        session_id=body.session_id,
        user_id=actor_id,
        require_confirmation=bool(body.require_confirmation),
        metadata=metadata,
    )
    result = orchestrator.run(action_request)
    _persist_action_chat_message(result)
    status_code = 200 if result.success else 500
    if not result.success and isinstance(result.tool_output, dict):
        status_code = 422
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

    _, denied = _execution_guard(body.execution_id)
    if denied:
        return denied

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

    _, denied = _execution_guard(body.execution_id)
    if denied:
        return denied

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

    record, denied = _execution_guard(target_id)
    if denied:
        return denied
    return jsonify({
        "success": True,
        "execution": record.to_dict(),
    }), 200

