#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
API错误处理工具模块
用于处理DeepSeek和OpenAI等远程API的错误响应
"""
import os
import re
import json
import requests
from typing import Tuple
from utils.utils_core.logger import get_logger
from utils.utils_core import error_codes as ec

logger = get_logger(__name__)

_PLACEHOLDER_PREFIXES = (
    "your_",
    "your-",
    "sk-your",
    "change_me",
    "change-me",
    "changeme",
    "replace_me",
    "replace-me",
    "placeholder",
    "todo_",
)
_PLACEHOLDER_EXACT = frozenset({"none", "null", "undefined", "todo", "n/a", "na", "xxx"})


def is_placeholder_secret(value) -> bool:
    """空值、掩码和模板占位符都不是可用密钥。

    只按前缀和整串判断。真实密钥是随机串，中间偶然出现 todo、example 不能被当成占位符。
    """
    text = "" if value is None else str(value).strip()
    if not text or text == "********":
        return True
    lowered = text.lower()
    if lowered in _PLACEHOLDER_EXACT or set(lowered) <= {"x", "*", "-", "_"}:
        return True
    return lowered.startswith(_PLACEHOLDER_PREFIXES)


def get_api_key_from_config_center(company: str) -> str | None:
    """
    从配置中心获取API Key
    
    参数:
        company: AI提供商名称 ('OPENAI', 'DEEPSEEK', 'GEMINI', 'QWEN')，会自动转换为大写
    
    返回:
        str | None: API Key值，None表示配置中心中没有配置
    """
    try:
        from services.config_center_service import config_center_service
        
        # 根据公司类型获取对应的配置键（配置中心使用大写的环境变量名）
        company_upper = company.upper() if company else "OPENAI"
        if company_upper == "OPENAI":
            api_key = config_center_service.get_config_value("OPENAI_API_KEY")
        elif company_upper == "DEEPSEEK":
            api_key = config_center_service.get_config_value("DEEPSEEK_API_KEY")
        elif company_upper == "GEMINI":
            api_key = config_center_service.get_config_value("GEMINI_API_KEY")
        elif company_upper == "QWEN":
            api_key = config_center_service.get_config_value("QWEN_API_KEY")
        elif company_upper == "ANTHROPIC":
            api_key = config_center_service.get_config_value("ANTHROPIC_API_KEY")
        else:
            logger.warning(f"不支持的AI提供商: {company}")
            return None
        
        # 检查API Key是否有效
        if api_key and isinstance(api_key, str) and api_key.strip():
            return api_key.strip()
        
        return None
        
    except Exception as e:
        logger.error(f"从配置中心获取API Key失败: {company}, 错误: {e}")
        return None


def get_api_key_with_fallback(company: str) -> Tuple[str | None, str | None, str]:
    """配置中心的可用密钥优先。.env 里的空值和占位符不参与选择。"""
    company_upper = company.upper() if company else "OPENAI"
    env_names = {
        "OPENAI": "OPENAI_API_KEY",
        "DEEPSEEK": "DEEPSEEK_API_KEY",
        "GEMINI": "GEMINI_API_KEY",
        "QWEN": "QWEN_API_KEY",
        "ANTHROPIC": "ANTHROPIC_API_KEY",
    }
    if company_upper not in env_names:
        return None, None, f"不支持的AI提供商: {company}"

    config_key = get_api_key_from_config_center(company_upper)
    if config_key and not is_placeholder_secret(config_key):
        return config_key.strip(), "config_center", "配置中心密钥可用"

    env_key = (os.getenv(env_names[company_upper]) or "").strip()
    if env_key and not is_placeholder_secret(env_key):
        return env_key, "env", "环境变量密钥可用"

    return None, None, f"{company_upper} 尚未配置可用 API Key"



def handle_api_error(response: requests.Response, service_name: str = "API") -> Tuple[bool, str]:
    """
    通用错误处理函数，适用于 DeepSeek 与 OpenAI 接口。
    
    参数:
        response: requests.Response 对象
        service_name: "DeepSeek" 或 "OpenAI"（仅用于日志输出）
    
    返回:
        Tuple[bool, str]: (是否可以重试, 错误描述)
            - True: 表示可以重试
            - False: 表示不应重试（需要修正参数或中断）
    """
    code = response.status_code
    text = response.text
    
    # 尝试从JSON响应中提取关键错误信息，但不输出完整JSON
    error_message = None
    try:
        error_data = json.loads(text)
        if isinstance(error_data, dict) and "error" in error_data:
            error_info = error_data["error"]
            if isinstance(error_info, dict):
                error_message = error_info.get("message", "")
    except (json.JSONDecodeError, AttributeError, KeyError):
        pass
    
    # 只记录状态码和关键错误信息，不输出完整JSON
    if error_message:
        logger.error(f"[{service_name}] 状态码: {code}, 错误: {error_message}")
    else:
        logger.error(f"[{service_name}] 状态码: {code}")

    # —— DeepSeek 特有错误码 ——  
    if service_name == "DeepSeek":
        if code == 400:
            error_msg = "DeepSeek: 请求体格式错误。请检查请求体 JSON 结构与字段。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        if code == 401:
            error_msg = "DeepSeek: 认证失败。请检查 API Key。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        if code == 402:
            error_msg = "DeepSeek: 余额不足。请充值或检查账户状态。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        if code == 422:
            error_msg = "DeepSeek: 参数错误。请检查每个字段是否符合文档要求。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        if code == 429:
            error_msg = "DeepSeek: 请求速率达到上限。稍后重试。"
            logger.warning(f"🚦 {error_msg}")
            return True, error_msg
        if code == 500:
            error_msg = "DeepSeek: 服务器故障。建议延迟后重试。"
            logger.warning(f"⚠️ {error_msg}")
            return True, error_msg
        if code == 503:
            error_msg = "DeepSeek: 服务器繁忙。建议稍后再试。"
            logger.warning(f"⚠️ {error_msg}")
            return True, error_msg

    # —— OpenAI 常见错误码 ——  
    if service_name == "OpenAI":
        if code == 400:
            error_msg = "OpenAI: 请求格式或参数错误。请检查 JSON 与必填字段。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        if code == 401:
            error_msg = "OpenAI: 身份认证失败。请检查 API Key 与组织。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        if code == 403:
            error_msg = "OpenAI: 禁止访问。可能模型/区域受限或权限不足。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        if code == 404:
            error_msg = "OpenAI: 资源未找到。检查模型名或 endpoint 是否正确。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        if code == 429:
            error_msg = "OpenAI: 请求速率或配额超限。稍后重试或申请更高限额。"
            logger.warning(f"🚦 {error_msg}")
            return True, error_msg
        if code == 500:
            error_msg = "OpenAI: 服务器内部错误。建议延迟后重试。"
            logger.warning(f"⚠️ {error_msg}")
            return True, error_msg
        if code == 503:
            error_msg = "OpenAI: 模型当前过载。建议稍后重试。"
            logger.warning(f"⚠️ {error_msg}")
            return True, error_msg

    # —— Qwen 常见错误码（OpenAI-compatible） ——  
    if service_name == "Qwen":
        if code == 400:
            error_msg = "Qwen: 请求格式或参数错误。请检查 JSON 与必填字段。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        if code == 401:
            error_msg = "Qwen: 身份认证失败。请检查 API Key。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        if code == 403:
            error_msg = "Qwen: 禁止访问。可能模型/区域受限或权限不足。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        if code == 404:
            error_msg = "Qwen: 资源未找到。检查模型名或 endpoint 是否正确。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        if code == 429:
            error_msg = "Qwen: 请求速率或配额超限。稍后重试或申请更高限额。"
            logger.warning(f"🚦 {error_msg}")
            return True, error_msg
        if code == 500:
            error_msg = "Qwen: 服务器内部错误。建议延迟后重试。"
            logger.warning(f"⚠️ {error_msg}")
            return True, error_msg
        if code == 503:
            error_msg = "Qwen: 模型当前过载。建议稍后重试。"
            logger.warning(f"⚠️ {error_msg}")
            return True, error_msg

    # —— Gemini 常见错误码 ——  
    if service_name == "Gemini":
        if code == 400:
            # 检查是否是API key错误
            if error_message and ("API key" in error_message or "API_KEY" in str(error_message)):
                error_msg = "Gemini: API Key 不存在或不可用"
            else:
                error_msg = "Gemini: 请求格式或参数错误"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        if code == 401:
            error_msg = "Gemini: API Key 不存在或不可用"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        if code == 403:
            error_msg = "Gemini: 禁止访问。可能API Key权限不足或配额用尽。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        if code == 404:
            error_msg = "Gemini: 资源未找到。检查模型名或 endpoint 是否正确。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        if code == 429:
            error_msg = "Gemini: 请求速率超限。稍后重试。"
            logger.warning(f"🚦 {error_msg}")
            return True, error_msg
        if code == 500:
            error_msg = "Gemini: 服务器内部错误。建议延迟后重试。"
            logger.warning(f"⚠️ {error_msg}")
            return True, error_msg
        if code == 503:
            error_msg = "Gemini: 服务暂时不可用。建议稍后重试。"
            logger.warning(f"⚠️ {error_msg}")
            return True, error_msg

    # —— 默认处理 ——  
    # 未被覆盖的其他状态码
    if 400 <= code < 500:
        error_msg = f"{service_name}: 客户端错误（{code}），请检查请求。"
        logger.error(f"❌ {error_msg}")
        return False, error_msg
    if 500 <= code < 600:
        error_msg = f"{service_name}: 服务端错误（{code}），建议重试。"
        logger.warning(f"⚠️ {error_msg}")
        return True, error_msg

    # 若不是错误状况（例如 200），则无需处理
    return False, ""


def check_api_key_configuration(company: str) -> Tuple[bool, str]:
    """
    检查API key配置是否完整，支持.env和配置中心的fallback机制
    
    参数:
        company: AI提供商名称 ('OPENAI', 'DEEPSEEK', 'OLLAMA', 'GEMINI', 'QWEN')，会自动转换为大写
    
    返回:
        Tuple[bool, str]: (配置是否完整, 错误描述)
    """
    if str(company or "").strip().upper() == "OLLAMA":
        # Ollama是本地服务，不需要API key检查
        return True, ""
    
    # 使用新的fallback机制获取API Key
    api_key, source, validation_result = get_api_key_with_fallback(company)
    
    if api_key is None:
        return False, validation_result
    
    # 记录API Key来源
    logger.info(f"{company.title()} API Key 来源: {source}, 验证结果: {validation_result}")
    
    return True, validation_result


def get_service_name(company: str) -> str:
    """
    根据公司名称获取服务名称
    
    参数:
        company: AI提供商名称
    
    返回:
        str: 服务显示名称
    """
    service_names = {
        "openai": "OpenAI",
        "deepseek": "DeepSeek",
        "ollama": "Ollama",
        "gemini": "Google Gemini",
        "qwen": "Qwen",
        "anthropic": "Anthropic",
    }
    return service_names.get(company, company.title())


def _extract_status_code_from_error_text(error_text: str) -> int | None:
    """从异常文本中尽量提取 HTTP 状态码。"""
    if not error_text:
        return None
    patterns = [
        r"\bstatus(?:\s*code)?\s*[:=]\s*(\d{3})\b",
        r"\bHTTP\s*(\d{3})\b",
        r"\bcode\s*[:=]\s*(\d{3})\b",
        r"\b(\d{3})\s*(?:Client|Server)\s*Error\b",
    ]
    for pattern in patterns:
        matched = re.search(pattern, error_text, re.IGNORECASE)
        if matched:
            try:
                code = int(matched.group(1))
                if 100 <= code <= 599:
                    return code
            except (TypeError, ValueError):
                continue
    return None


def normalize_provider_error(company: str, error: Exception | str) -> dict:
    """
    统一归一化不同模型供应商错误，避免直接向前端暴露原始 500/异常堆栈。

    返回:
        {
            "message": str,       # 友好错误信息
            "status_code": int,   # 建议 HTTP 状态码
            "error_code": str,    # 业务错误码
            "retryable": bool     # 是否建议重试
        }
    """
    from utils.utils_performance_monitoring.token_session import normalize_token_session_error

    token_session = normalize_token_session_error(error)
    if token_session:
        return token_session

    company_upper = (company or "OPENAI").upper()
    service_name = {
        "OPENAI": "OpenAI",
        "DEEPSEEK": "DeepSeek",
        "GEMINI": "Gemini",
        "QWEN": "Qwen",
        "ANTHROPIC": "Anthropic",
        "OLLAMA": "Ollama"
    }.get(company_upper, "OpenAI")

    raw_text = str(error or "").strip()
    status_code = _extract_status_code_from_error_text(raw_text)
    text_lower = raw_text.lower()

    # 优先按供应商状态码映射
    if status_code:
        if service_name == "DeepSeek":
            if status_code == 401:
                return {"message": "DeepSeek API Key 无效或已过期，请检查配置中心或 .env。", "status_code": 401, "error_code": ec.MODEL_AUTH_FAILED, "retryable": False}
            if status_code == 402:
                return {"message": "DeepSeek 账户余额不足，请充值后重试。", "status_code": 402, "error_code": ec.MODEL_AUTH_FAILED, "retryable": False}
            if status_code == 422:
                return {"message": "DeepSeek 请求参数不合法，请检查输入后重试。", "status_code": 422, "error_code": ec.MODEL_BAD_REQUEST, "retryable": False}
            if status_code == 429:
                return {"message": "DeepSeek 请求过于频繁，请稍后重试。", "status_code": 429, "error_code": ec.MODEL_RATE_LIMITED, "retryable": True}
        elif service_name == "OpenAI":
            if status_code == 401:
                return {"message": "OpenAI API Key 无效或权限不足，请检查配置。", "status_code": 401, "error_code": ec.MODEL_AUTH_FAILED, "retryable": False}
            if status_code == 403:
                return {"message": "OpenAI 权限受限，可能模型不可用或账号权限不足。", "status_code": 403, "error_code": ec.MODEL_AUTH_FAILED, "retryable": False}
            if status_code == 404:
                return {"message": "OpenAI 模型或接口不存在，请检查模型名与地址。", "status_code": 404, "error_code": ec.MODEL_BAD_REQUEST, "retryable": False}
            if status_code == 429:
                return {"message": "OpenAI 请求触发限流或配额限制，请稍后重试。", "status_code": 429, "error_code": ec.MODEL_RATE_LIMITED, "retryable": True}
        elif service_name == "Gemini":
            if status_code in (400, 401):
                return {"message": "Gemini API Key 无效或不可用，请检查配置。", "status_code": 401, "error_code": ec.MODEL_AUTH_FAILED, "retryable": False}
            if status_code == 403:
                return {"message": "Gemini 访问被拒绝，可能配额不足或权限不足。", "status_code": 403, "error_code": ec.MODEL_AUTH_FAILED, "retryable": False}
            if status_code == 429:
                return {"message": "Gemini 请求过于频繁，请稍后重试。", "status_code": 429, "error_code": ec.MODEL_RATE_LIMITED, "retryable": True}
        elif service_name == "Qwen":
            if status_code == 401:
                return {"message": "Qwen API Key 无效或已过期，请检查配置。", "status_code": 401, "error_code": ec.MODEL_AUTH_FAILED, "retryable": False}
            if status_code == 403:
                return {"message": "Qwen 权限不足或服务受限，请检查账号与模型权限。", "status_code": 403, "error_code": ec.MODEL_AUTH_FAILED, "retryable": False}
            if status_code == 429:
                return {"message": "Qwen 请求触发限流，请稍后重试。", "status_code": 429, "error_code": ec.MODEL_RATE_LIMITED, "retryable": True}

        if 500 <= status_code < 600:
            return {"message": f"{service_name} 服务暂时不可用（{status_code}），请稍后重试。", "status_code": 503, "error_code": ec.MODEL_SERVICE_UNAVAILABLE, "retryable": True}
        if 400 <= status_code < 500:
            return {"message": f"{service_name} 请求失败（{status_code}），请检查参数与配置。", "status_code": 400, "error_code": ec.MODEL_BAD_REQUEST, "retryable": False}

    # 无状态码时按关键字兜底
    if any(keyword in text_lower for keyword in ("api key", "apikey", "authentication", "unauthorized", "invalid key", "配置失败")):
        return {"message": f"{service_name} API Key 无效或缺失，请检查配置中心或 .env。", "status_code": 401, "error_code": ec.MODEL_AUTH_FAILED, "retryable": False}
    if any(keyword in text_lower for keyword in ("rate limit", "too many requests", "quota")):
        return {"message": f"{service_name} 请求过于频繁或配额不足，请稍后重试。", "status_code": 429, "error_code": ec.MODEL_RATE_LIMITED, "retryable": True}
    if any(keyword in text_lower for keyword in ("timeout", "timed out", "read timeout", "connect timeout")):
        return {"message": f"{service_name} 请求超时，请稍后重试。", "status_code": 504, "error_code": ec.MODEL_TIMEOUT, "retryable": True}
    if any(keyword in text_lower for keyword in ("connection", "dns", "network", "refused", "unreachable")):
        return {"message": f"{service_name} 网络连接失败，请检查网络或服务地址。", "status_code": 502, "error_code": ec.MODEL_NETWORK_ERROR, "retryable": True}

    return {
        "message": f"{service_name} 调用失败，请稍后重试或检查配置。",
        "status_code": 500,
        "error_code": ec.MODEL_UNKNOWN_ERROR,
        "retryable": False
    }


def build_model_error_result(
    company: str,
    error: Exception | str,
    *,
    fallback_message: str = "模型调用失败",
    include_raw_error: bool = False
) -> dict:
    """
    生成统一的业务错误结构，便于各服务层/蓝图层组件化复用。
    """
    normalized = normalize_provider_error(company, error)
    result = {
        "success": False,
        "message": normalized.get("message") or fallback_message,
        "error": normalized.get("error_code", "MODEL_CALL_FAILED"),
        "error_code": normalized.get("error_code", "MODEL_CALL_FAILED"),
        "retryable": bool(normalized.get("retryable", False)),
        "status_code": int(normalized.get("status_code", 500) or 500),
    }
    if normalized.get("message_key"):
        result["message_key"] = normalized["message_key"]
        result["message_params"] = normalized.get("message_params") or {}
    if include_raw_error:
        result["details"] = str(error or "")
    return result


def build_internal_error_result(
    *,
    message: str = "服务器内部错误",
    error_code: str = ec.INTERNAL_SERVER_ERROR,
    retryable: bool = False,
    status_code: int = 500
) -> dict:
    """
    生成统一的非模型类内部错误结构，避免在业务层散落 `str(e)`。
    """
    return {
        "success": False,
        "message": message,
        "error": error_code,
        "error_code": error_code,
        "retryable": retryable,
        "status_code": status_code
    }

