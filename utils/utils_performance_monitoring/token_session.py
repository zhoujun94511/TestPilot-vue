#!/usr/bin/python
# -*- coding: utf-8 -*-
"""词元会话熔断：结构化异常与 API 友好文案。"""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from utils.utils_core import error_codes as ec

LimitKind = Literal["tokens", "calls"]

# 达到上限的该比例时触发「即将用尽」预警（仅提示，不阻断）
TOKEN_SESSION_WARN_RATIO = 0.8


class TokenSessionLimitExceeded(Exception):
    """单进程会话累计词元或调用次数超过配置上限。"""

    def __init__(self, limit_kind: LimitKind, used: int, limit: int):
        self.limit_kind = limit_kind
        self.used = int(used)
        self.limit = int(limit)
        super().__init__(self.user_message_zh)

    @property
    def error_code(self) -> str:
        if self.limit_kind == "calls":
            return ec.TOKEN_SESSION_CALL_LIMIT
        return ec.TOKEN_SESSION_TOKEN_LIMIT

    @property
    def message_key(self) -> str:
        if self.limit_kind == "calls":
            return "common.tokenSession.exceededCalls"
        return "common.tokenSession.exceededTokens"

    @property
    def message_params(self) -> Dict[str, Any]:
        return {"used": self.used, "limit": self.limit}

    @property
    def user_message_zh(self) -> str:
        if self.limit_kind == "calls":
            return (
                f"本服务会话的模型调用次数已达上限（{self.used}/{self.limit}）。"
                "可在配置中心调整「单会话模型调用次数上限」，或重启后端服务以重置计数。"
            )
        return (
            f"本服务会话的累计词元已达上限（{self.used:,}/{self.limit:,}）。"
            "可在配置中心调整「单会话累计词元上限」，或重启后端服务以重置计数。"
        )

    @property
    def user_message_en(self) -> str:
        if self.limit_kind == "calls":
            return (
                f"Model call limit reached for this server session ({self.used}/{self.limit}). "
                "Raise TOKEN_MAX_CALLS_PER_SESSION in Config Center or restart the backend to reset."
            )
        return (
            f"Token budget exhausted for this server session ({self.used:,}/{self.limit:,}). "
            "Raise TOKEN_MAX_PER_SESSION in Config Center or restart the backend to reset."
        )

    def to_normalize_dict(self) -> Dict[str, Any]:
        return {
            "message": self.user_message_zh,
            "status_code": 429,
            "error_code": self.error_code,
            "retryable": False,
            "message_key": self.message_key,
            "message_params": self.message_params,
        }


def normalize_token_session_error(error: Exception | str) -> Optional[Dict[str, Any]]:
    if isinstance(error, TokenSessionLimitExceeded):
        return error.to_normalize_dict()

    text = str(error or "").strip() if not isinstance(error, str) else error.strip()
    if not text:
        return None
    lower = text.lower()
    if "调用次数超过限制" in text:
        base = TokenSessionLimitExceeded("calls", 0, 0).to_normalize_dict()
        base["message"] = text
        return base
    if "token消耗超过限制" in lower:
        base = TokenSessionLimitExceeded("tokens", 0, 0).to_normalize_dict()
        base["message"] = text
        return base
    return None


def usage_percent(used: int, limit: int) -> float:
    if limit <= 0:
        return 0.0
    return round(min(100.0, max(0.0, (used / limit) * 100)), 1)


def session_level(
    token_used: int,
    token_max: int,
    call_used: int,
    call_max: int,
) -> Literal["ok", "warning"]:
    token_ratio = (token_used / token_max) if token_max > 0 else 0.0
    call_ratio = (call_used / call_max) if call_max > 0 else 0.0
    peak = max(token_ratio, call_ratio)
    if peak >= TOKEN_SESSION_WARN_RATIO:
        return "warning"
    return "ok"


def warning_message_key(token_used: int, token_max: int, call_used: int, call_max: int) -> Optional[str]:
    token_ratio = (token_used / token_max) if token_max > 0 else 0.0
    call_ratio = (call_used / call_max) if call_max > 0 else 0.0
    if call_ratio >= TOKEN_SESSION_WARN_RATIO and call_ratio >= token_ratio:
        return "common.tokenSession.warningCalls"
    if token_ratio >= TOKEN_SESSION_WARN_RATIO:
        return "common.tokenSession.warningTokens"
    return None
