#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Standardized API response helpers for localized backend responses."""

from __future__ import annotations

from typing import Any, Dict, Optional

from flask import jsonify


DEFAULT_SUCCESS_MESSAGE = "Success"
DEFAULT_ERROR_MESSAGE = "Unknown error"


MESSAGE_NORMALIZATION_MAP: Dict[str, Dict[str, Any]] = {
    "请求数据格式错误": {
        "code": "INVALID_REQUEST_PAYLOAD",
        "message_key": "common.message.invalidRequest",
        "message": "Invalid request payload",
    },
    "没有上传文件": {
        "code": "FILE_UPLOAD_MISSING",
        "message_key": "common.message.noFileUploaded",
        "message": "No file was uploaded",
    },
    "没有选择文件": {
        "code": "FILE_NOT_SELECTED",
        "message_key": "common.message.noFileSelected",
        "message": "No file was selected",
    },
    "不支持的文件格式，请上传 JSON 或 YAML 文件": {
        "code": "UNSUPPORTED_FILE_FORMAT",
        "message_key": "common.message.unsupportedFileFormat",
        "message": "Unsupported file format. Please upload a JSON or YAML file",
    },
    "知识库功能已禁用（ENABLE_VECTOR_STORE=false）": {
        "code": "KNOWLEDGE_BASE_DISABLED",
        "message_key": "knowledge.message.disabled",
        "message": "Knowledge base is disabled",
    },
    "聊天模型尚未初始化，请先检查模型配置": {
        "code": "CHAT_LLM_NOT_INITIALIZED",
        "message_key": "chat.message.llmNotInitialized",
        "message": "Chat model is not initialized",
    },
    "消息内容不能为空": {
        "code": "VALIDATION_MESSAGE_EMPTY",
        "message_key": "common.message.messageRequired",
        "message": "Message content cannot be empty",
    },
    "请求内容不能为空": {
        "code": "VALIDATION_REQUEST_EMPTY",
        "message_key": "common.message.requestRequired",
        "message": "Request payload cannot be empty",
    },
    "导出失败": {
        "code": "EXPORT_FAILED",
        "message_key": "export.message.exportFailed",
        "message": "Export failed",
    },
}

STATUS_VALUE_MAP: Dict[str, Dict[str, str]] = {
    "处理中": {"value": "processing", "key": "enums.status.processing"},
    "在线": {"value": "online", "key": "enums.status.online"},
    "离线": {"value": "offline", "key": "enums.status.offline"},
    "空": {"value": "empty", "key": "enums.status.empty"},
    "异常": {"value": "abnormal", "key": "enums.status.abnormal"},
    "正常": {"value": "normal", "key": "enums.status.normal"},
    "危险": {"value": "danger", "key": "enums.status.danger"},
    "警告": {"value": "warning", "key": "enums.status.warning"},
    "良好": {"value": "good", "key": "enums.status.good"},
    "检测失败": {"value": "failed", "key": "enums.status.failed"},
}

ROUTE_RESPONSE_MAP: Dict[str, Dict[str, Dict[str, Any]]] = {
    "GET:/api/config/categories": {
        "success": {
            "code": "CONFIG_CATEGORY_LIST_SUCCESS",
            "message_key": "configCenter.message.categoryListLoaded",
            "message": "Configuration categories loaded successfully",
        },
    },
    "POST:/api/config/import": {
        "success": {
            "code": "CONFIG_IMPORT_SUCCESS",
            "message_key": "config.message.importSuccess",
            "message": "Configuration imported successfully",
        },
        "error": {
            "code": "CONFIG_IMPORT_FAILED",
            "message_key": "config.message.importFailed",
            "message": "Failed to import configuration",
        },
    },
    "POST:/api/config/<category>": {
        "success": {
            "code": "CONFIG_BATCH_UPDATE_SUCCESS",
            "message_key": "configCenter.message.batchUpdateSuccess",
            "message": "Configuration items updated successfully",
        },
        "error": {
            "code": "CONFIG_BATCH_UPDATE_FAILED",
            "message_key": "configCenter.message.batchUpdateFailed",
            "message": "Failed to update configuration items",
        },
    },
    "PUT:/api/config/item/<key>": {
        "success": {
            "code": "CONFIG_ITEM_UPDATE_SUCCESS",
            "message_key": "configCenter.message.itemUpdateSuccess",
            "message": "Configuration item updated successfully",
        },
        "error": {
            "code": "CONFIG_ITEM_UPDATE_FAILED",
            "message_key": "configCenter.message.itemUpdateFailed",
            "message": "Failed to update configuration item",
        },
    },
    "DELETE:/api/config/item/<key>": {
        "success": {
            "code": "CONFIG_ITEM_DELETE_SUCCESS",
            "message_key": "configCenter.message.itemDeleteSuccess",
            "message": "Configuration item deleted successfully",
        },
        "error": {
            "code": "CONFIG_ITEM_DELETE_FAILED",
            "message_key": "configCenter.message.itemDeleteFailed",
            "message": "Failed to delete configuration item",
        },
    },
    "GET:/api/documents/list": {
        "success": {
            "code": "DOCUMENT_LIST_SUCCESS",
            "message_key": "documents.message.listSuccess",
            "message": "Document list loaded successfully",
        },
        "error": {
            "code": "DOCUMENT_LIST_FAILED",
            "message_key": "documents.message.listFailed",
            "message": "Failed to load document list",
        },
    },
    "POST:/api/documents/upload": {
        "success": {
            "code": "DOCUMENT_UPLOAD_SUCCESS",
            "message_key": "documents.message.uploadSuccess",
            "message": "Document uploaded successfully",
        },
        "error": {
            "code": "DOCUMENT_UPLOAD_FAILED",
            "message_key": "documents.message.uploadFailed",
            "message": "Document upload failed",
        },
    },
    "POST:/api/documents/analyze": {
        "success": {
            "code": "DOCUMENT_ANALYZE_SUCCESS",
            "message_key": "documents.message.analyzeSuccess",
            "message": "Document analyzed successfully",
        },
        "error": {
            "code": "DOCUMENT_ANALYZE_FAILED",
            "message_key": "documents.message.analyzeFailed",
            "message": "Document analysis failed",
        },
    },
    "DELETE:/api/documents/<path:file_path>": {
        "success": {
            "code": "DOCUMENT_DELETE_SUCCESS",
            "message_key": "documents.message.deleteSuccess",
            "message": "Document deleted successfully",
        },
        "error": {
            "code": "DOCUMENT_DELETE_FAILED",
            "message_key": "documents.message.deleteFailed",
            "message": "Failed to delete document",
        },
    },
    "POST:/api/cases/generate": {
        "success": {
            "code": "CASE_GENERATE_SUCCESS",
            "message_key": "cases.message.generateSuccess",
            "message": "Test cases generated successfully",
        },
        "error": {
            "code": "CASE_GENERATE_FAILED",
            "message_key": "cases.message.generateFailed",
            "message": "Failed to generate test cases",
        },
    },
    "POST:/api/cases/batch-generate": {
        "success": {
            "code": "CASE_BATCH_GENERATE_SUCCESS",
            "message_key": "cases.message.batchGenerateSuccess",
            "message": "Test cases generated successfully",
        },
        "error": {
            "code": "CASE_BATCH_GENERATE_FAILED",
            "message_key": "cases.message.batchGenerateFailed",
            "message": "Failed to generate test cases",
        },
    },
    "POST:/api/knowledge/upload": {
        "success": {
            "code": "KNOWLEDGE_UPLOAD_SUCCESS",
            "message_key": "knowledge.message.uploadSuccess",
            "message": "Knowledge file uploaded successfully",
        },
        "error": {
            "code": "KNOWLEDGE_UPLOAD_FAILED",
            "message_key": "knowledge.message.uploadFailed",
            "message": "Knowledge file upload failed",
        },
    },
    "POST:/api/knowledge/rebuild": {
        "success": {
            "code": "KNOWLEDGE_REBUILD_SUCCESS",
            "message_key": "knowledge.message.rebuildSuccess",
            "message": "Knowledge base rebuilt successfully",
        },
        "error": {
            "code": "KNOWLEDGE_REBUILD_FAILED",
            "message_key": "knowledge.message.rebuildFailed",
            "message": "Failed to rebuild knowledge base",
        },
    },
    "POST:/api/chat/message": {
        "success": {
            "code": "CHAT_MESSAGE_SUCCESS",
            "message_key": "chat.message.sendSuccess",
            "message": "Message sent successfully",
        },
        "error": {
            "code": "CHAT_MESSAGE_FAILED",
            "message_key": "chat.message.sendFailed",
            "message": "Failed to send message",
        },
    },
    "GET:/api/export/cases/excel": {
        "success": {
            "code": "EXPORT_CASES_SUCCESS",
            "message_key": "export.message.downloadSuccess",
            "message": "Export completed successfully",
        },
        "error": {
            "code": "EXPORT_CASES_FAILED",
            "message_key": "export.message.casesFailed",
            "message": "Failed to export test cases",
        },
    },
    "GET:/api/model-status": {
        "success": {
            "code": "MODEL_STATUS_SUCCESS",
            "message_key": "model.message.statusLoaded",
            "message": "Model status loaded successfully",
        },
        "error": {
            "code": "MODEL_STATUS_FAILED",
            "message_key": "model.message.statusFailed",
            "message": "Failed to load model status",
        },
    },
    "GET:/api/stats/system-status": {
        "success": {
            "code": "SYSTEM_STATUS_SUCCESS",
            "message_key": "stats.message.systemStatusLoaded",
            "message": "System status loaded successfully",
        },
        "error": {
            "code": "SYSTEM_STATUS_FAILED",
            "message_key": "stats.message.systemStatusFailed",
            "message": "Failed to load system status",
        },
    },
}


def _normalize_message(message: Optional[str]) -> str:
    if not message:
        return DEFAULT_SUCCESS_MESSAGE

    normalized = MESSAGE_NORMALIZATION_MAP.get(message)
    if normalized:
        return normalized["message"]

    if any("\u4e00" <= char <= "\u9fff" for char in message):
        return ""

    return message


def normalize_message_response(
    payload: Any,
    *,
    default_code: str = "UNKNOWN_ERROR",
    default_message_key: str = "errors.unknown",
    default_message: str = DEFAULT_ERROR_MESSAGE,
    message_params: Optional[Dict[str, Any]] = None,
    details: Optional[Any] = None,
    status: Optional[int] = None,
) -> Dict[str, Any]:
    """Normalize an existing message payload into the new localized response shape."""
    if isinstance(payload, dict):
        message = payload.get("message")
        code = payload.get("code") or default_code
        message_key = payload.get("message_key") or default_message_key
        message_params = payload.get("message_params") or message_params or {}
        normalized = {
            **payload,
            "success": payload.get("success", False),
            "code": code,
            "message_key": message_key,
            "message": _normalize_message(message) if isinstance(message, str) else default_message,
            "message_params": message_params,
        }
        if details is not None and "details" not in normalized:
            normalized["details"] = details
        if status is not None and "status" not in normalized:
            normalized["status"] = status
        return normalized

    normalized: Dict[str, Any] = {
        "success": False,
        "code": default_code,
        "message_key": default_message_key,
        "message": _normalize_message(payload if isinstance(payload, str) else None) or default_message,
        "message_params": message_params or {},
    }
    if details is not None:
        normalized["details"] = details
    if status is not None:
        normalized["status"] = status
    return normalized


def _route_signature(path: str, method: str) -> str:
    if not path.startswith("/api/"):
        return ""
    if path == "/api/config/categories":
        return f"{method}:/api/config/categories"
    if path == "/api/config/audit-logs":
        return f"{method}:/api/config/audit-logs"
    if path.startswith("/api/config/validate/"):
        return f"{method}:/api/config/validate/<key>"
    if path.startswith("/api/config/item/"):
        return f"{method}:/api/config/item/<key>"
    if path.startswith("/api/config/item/"):
        return f"{method}:/api/config/item/<key>"
    if path == "/api/config/export":
        return f"{method}:/api/config/export"
    if path == "/api/config/import":
        return f"{method}:/api/config/import"
    if path.startswith("/api/config/") and path != "/api/config/import" and path != "/api/config/export" and path != "/api/config/audit-logs" and path != "/api/config/validate" and path != "/api/config/categories":
        return f"{method}:/api/config/<category>"
    if path.startswith("/api/documents/") and path.endswith("/upload"):
        return f"{method}:/api/documents/upload"
    if path.startswith("/api/documents/") and path.endswith("/analyze"):
        return f"{method}:/api/documents/analyze"
    if path.startswith("/api/documents/list"):
        return f"{method}:/api/documents/list"
    if path.startswith("/api/documents/") and method == "DELETE":
        return f"{method}:/api/documents/<path:file_path>"
    if path.startswith("/api/documents/requirements/") and method == "GET":
        return f"{method}:/api/documents/requirements/<string:req_id>"
    if path.startswith("/api/documents/requirements/") and method == "PUT":
        return f"{method}:/api/documents/requirements/<string:req_id>"
    if path.startswith("/api/documents/requirements/") and method == "DELETE":
        return f"{method}:/api/documents/requirements/<string:req_id>"
    if path.startswith("/api/knowledge/upload"):
        return f"{method}:/api/knowledge/upload"
    if path.startswith("/api/knowledge/search"):
        return f"{method}:/api/knowledge/search"
    if path.startswith("/api/knowledge/list"):
        return f"{method}:/api/knowledge/list"
    if path.startswith("/api/knowledge/") and method == "DELETE":
        return f"{method}:/api/knowledge/<int:file_id>"
    if path.startswith("/api/knowledge/") and method == "PUT":
        return f"{method}:/api/knowledge/<int:file_id>"
    if path.startswith("/api/knowledge/") and method == "GET":
        return f"{method}:/api/knowledge/<int:file_id>"
    if path.startswith("/api/knowledge/rebuild"):
        return f"{method}:/api/knowledge/rebuild"
    if path.startswith("/api/cases/generate-from-analysis"):
        return f"{method}:/api/cases/generate"
    if path.startswith("/api/cases/batch-generate"):
        return f"{method}:/api/cases/batch-generate"
    if path.startswith("/api/cases/generate"):
        return f"{method}:/api/cases/generate"
    if path.startswith("/api/cases/") and method in {"GET", "PUT", "DELETE"}:
        return f"{method}:/api/cases/<string:case_id>"
    if path.startswith("/api/knowledge/rebuild"):
        return f"{method}:/api/knowledge/rebuild"
    if path.startswith("/api/chat/message"):
        return f"{method}:/api/chat/message"
    if path.startswith("/api/chat/stream"):
        return f"{method}:/api/chat/stream"
    if path.startswith("/api/chat/history"):
        return f"{method}:/api/chat/history"
    if path.startswith("/api/chat/clear"):
        return f"{method}:/api/chat/clear"
    if path.startswith("/api/chat/session/"):
        return f"{method}:/api/chat/session/<session_id>"
    if path.startswith("/api/export/cases/excel"):
        return f"{method}:/api/export/cases/excel"
    if path.startswith("/api/export/cases/csv"):
        return f"{method}:/api/export/cases/csv"
    if path.startswith("/api/export/cases/json"):
        return f"{method}:/api/export/cases/json"
    if path.startswith("/api/export/requirements/excel"):
        return f"{method}:/api/export/requirements/excel"
    if path.startswith("/api/export/chat/history"):
        return f"{method}:/api/export/chat/history"
    if path.startswith("/api/export/template/cases"):
        return f"{method}:/api/export/template/cases"
    if path.startswith("/api/export/batch"):
        return f"{method}:/api/export/batch"
    if path == "/api/model-status":
        return f"{method}:/api/model-status"
    if path == "/api/stats/system-status":
        return f"{method}:/api/stats/system-status"
    return f"{method}:{path}"


def _normalize_status_payload(status_payload: Any) -> Any:
    if not isinstance(status_payload, dict):
        return status_payload

    normalized = dict(status_payload)
    status_value = normalized.get("status")
    if isinstance(status_value, str):
        mapped = STATUS_VALUE_MAP.get(status_value)
        if mapped:
            normalized["status"] = mapped["value"]
            normalized["status_key"] = mapped["key"]
    return normalized


def normalize_api_response_payload(payload: Any, *, path: str, method: str, status_code: int) -> Any:
    """Normalize legacy API payloads into the standardized localized shape."""
    if not isinstance(payload, dict) or "success" not in payload:
        return payload

    route_key = _route_signature(path, method)
    route_map = ROUTE_RESPONSE_MAP.get(route_key, {})

    normalized = dict(payload)
    is_success = bool(payload.get("success"))

    if is_success:
        defaults = route_map.get("success", {})
        normalized.setdefault("code", defaults.get("code", "SUCCESS"))
        normalized.setdefault("message_key", defaults.get("message_key", "common.message.success"))
        normalized.setdefault("message_params", payload.get("message_params") or {})
        message = payload.get("message")
        if not message:
            normalized["message"] = defaults.get("message", DEFAULT_SUCCESS_MESSAGE)
        elif isinstance(message, str):
            normalized["message"] = _normalize_message(message) or defaults.get("message", DEFAULT_SUCCESS_MESSAGE)
    else:
        defaults = route_map.get("error", {})
        normalized.setdefault("code", defaults.get("code", "UNKNOWN_ERROR"))
        normalized.setdefault("message_key", defaults.get("message_key", "errors.unknown"))
        normalized.setdefault("message_params", payload.get("message_params") or {})
        message = payload.get("message")
        if not message:
            normalized["message"] = defaults.get("message", DEFAULT_ERROR_MESSAGE)
        elif isinstance(message, str):
            normalized["message"] = _normalize_message(message) or defaults.get("message", DEFAULT_ERROR_MESSAGE)

    if "details" not in normalized and status_code >= 500:
        normalized["details"] = payload.get("error")

    if route_key == "GET:/api/stats/system-status" and isinstance(normalized.get("system"), dict):
        system_payload = dict(normalized["system"])
        for section in ("ai_service", "knowledge", "performance"):
            if isinstance(system_payload.get(section), dict):
                system_payload[section] = _normalize_status_payload(system_payload[section])
        normalized["system"] = system_payload

    return normalized


def api_success(
    data: Any = None,
    *,
    code: str = "SUCCESS",
    message_key: str = "common.message.success",
    message: str = DEFAULT_SUCCESS_MESSAGE,
    message_params: Optional[Dict[str, Any]] = None,
    status: int = 200,
    **extra: Any,
):
    """Create a standardized success response."""
    payload: Dict[str, Any] = {
        "success": True,
        "code": code,
        "message_key": message_key,
        "message": message,
        "message_params": message_params or {},
    }
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return jsonify(payload), status


def api_error(
    code: str = "UNKNOWN_ERROR",
    *,
    message_key: str = "errors.unknown",
    message: str = DEFAULT_ERROR_MESSAGE,
    message_params: Optional[Dict[str, Any]] = None,
    details: Optional[Any] = None,
    status: int = 400,
    **extra: Any,
):
    """Create a standardized error response."""
    payload: Dict[str, Any] = {
        "success": False,
        "code": code,
        "message_key": message_key,
        "message": message,
        "message_params": message_params or {},
    }
    if details is not None:
        payload["details"] = details
    payload.update(extra)
    return jsonify(payload), status
