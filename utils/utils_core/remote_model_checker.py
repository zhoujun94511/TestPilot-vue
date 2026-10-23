#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
远程模型可用性检查服务
用于在应用启动时检查远程AI模型的可用性
"""
import requests
from typing import Dict, Any, Tuple
from config.settings import resolve_deepseek_model, resolve_gemini_model, resolve_openai_model, settings
from utils.utils_core.api_error_handler import handle_api_error, get_service_name, get_api_key_with_fallback
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


class RemoteModelChecker:
    """远程模型可用性检查器"""
    
    def __init__(self):
        self.timeout = 10  # 请求超时时间（秒）
    
    def check_model_availability(self, company: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        检查指定公司的模型可用性
        
        参数:
            company: AI提供商名称 ('OPENAI', 'DEEPSEEK', 'OLLAMA', 'GEMINI', 'QWEN')，会自动转换为大写
        
        返回:
            Tuple[bool, str, Dict]: (是否可用, 状态描述, 详细信息)
        """
        # 统一转换为大写
        company_upper = company.upper() if company else "OPENAI"
        logger.info(f"开始检查 {get_service_name(company_upper)} 模型可用性...")
        
        # 如果是本地模型，直接返回可用
        if company_upper == "OLLAMA":
            return self._check_ollama_availability()
        
        # 根据公司类型进行不同的检查（API Key 检查已在各方法内部进行）
        if company_upper == "OPENAI":
            return self._check_openai_availability()
        elif company_upper == "DEEPSEEK":
            return self._check_deepseek_availability()
        elif company_upper == "GEMINI":
            return self._check_gemini_availability()
        elif company_upper == "QWEN":
            return self._check_qwen_availability()
        else:
            return False, f"不支持的AI提供商: {company_upper}", {"error_type": "unsupported"}
    
    def _check_openai_availability(self) -> Tuple[bool, str, Dict[str, Any]]:
        """检查OpenAI模型可用性"""
        try:
            # 使用fallback机制获取API Key
            api_key, source, validation_result = get_api_key_with_fallback("openai")
            if api_key is None:
                return False, validation_result, {"error_type": "config", "details": validation_result}
            
            base_url = getattr(settings, 'OPENAI_BASE_URL', 'https://api.openai.com/v1')
            model = resolve_openai_model(getattr(settings, 'OPENAI_MODEL', None))
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # 构建测试请求
            test_payload: Dict[str, Any] = {
                "model": model,
                "messages": [{"role": "user", "content": "Hello"}]
            }
            
            # GPT-5 使用 max_completion_tokens，其他模型使用 max_tokens
            if "gpt-5" in model.lower():
                test_payload["max_completion_tokens"] = 10
            else:
                test_payload["max_tokens"] = 10
            
            # 发送请求
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=test_payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.info("✅ OpenAI 模型可用性检查通过")
                return True, "OpenAI 模型可用", {
                    "model": model,
                    "base_url": base_url,
                    "status_code": response.status_code
                }
            else:
                can_retry, error_msg = handle_api_error(response, "OpenAI")
                return False, error_msg, {
                    "error_type": "api_error",
                    "status_code": response.status_code,
                    "can_retry": can_retry,
                    "details": error_msg
                }
                
        except requests.exceptions.Timeout:
            error_msg = "OpenAI: 请求超时。请检查网络连接或稍后重试。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, {"error_type": "timeout", "can_retry": True}
        except requests.exceptions.ConnectionError:
            error_msg = "OpenAI: 网络连接失败。请检查网络连接和代理设置。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, {"error_type": "connection", "can_retry": True}
        except Exception as e:
            error_msg = f"OpenAI: 检查过程中发生未知错误: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, {"error_type": "unknown", "can_retry": False}
    
    def _check_deepseek_availability(self) -> Tuple[bool, str, Dict[str, Any]]:
        """检查DeepSeek模型可用性"""
        try:
            # 使用fallback机制获取API Key
            api_key, source, validation_result = get_api_key_with_fallback("DEEPSEEK")
            if api_key is None:
                return False, validation_result, {"error_type": "config", "details": validation_result}
            
            base_url = getattr(settings, 'DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
            model = resolve_deepseek_model(getattr(settings, 'DEEPSEEK_MODEL', None))
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # 构建测试请求
            test_payload = {
                "model": model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            
            # 发送请求
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=test_payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.info("✅ DeepSeek 模型可用性检查通过")
                return True, "DeepSeek 模型可用", {
                    "model": model,
                    "base_url": base_url,
                    "status_code": response.status_code
                }
            else:
                can_retry, error_msg = handle_api_error(response, "DeepSeek")
                return False, error_msg, {
                    "error_type": "api_error",
                    "status_code": response.status_code,
                    "can_retry": can_retry,
                    "details": error_msg
                }
                
        except requests.exceptions.Timeout:
            error_msg = "DeepSeek: 请求超时。请检查网络连接或稍后重试。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, {"error_type": "timeout", "can_retry": True}
        except requests.exceptions.ConnectionError:
            error_msg = "DeepSeek: 网络连接失败。请检查网络连接和代理设置。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, {"error_type": "connection", "can_retry": True}
        except Exception as e:
            error_msg = f"DeepSeek: 检查过程中发生未知错误: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, {"error_type": "unknown", "can_retry": False}
    @staticmethod
    def _check_ollama_availability() -> Tuple[bool, str, Dict[str, Any]]:
        """检查Ollama本地模型可用性"""
        try:
            base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
            model = getattr(settings, 'OLLAMA_MODEL', None)
            
            if not model:
                return False, "Ollama: 模型名称未配置", {"error_type": "config"}
            
            # 检查Ollama服务是否运行
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            
            if response.status_code == 200:
                # 检查指定模型是否可用
                models_data = response.json()
                available_models = [m.get('name', '') for m in models_data.get('models', [])]
                
                if model in available_models:
                    logger.info("✅ Ollama 模型可用性检查通过")
                    return True, "Ollama 模型可用", {
                        "model": model,
                        "base_url": base_url,
                        "available_models": available_models
                    }
                else:
                    error_msg = f"Ollama: 模型 '{model}' 未找到。可用模型: {', '.join(available_models)}"
                    logger.error(f"❌ {error_msg}")
                    return False, error_msg, {
                        "error_type": "model_not_found",
                        "available_models": available_models
                    }
            else:
                error_msg = f"Ollama: 服务不可用 (状态码: {response.status_code})"
                logger.error(f"❌ {error_msg}")
                return False, error_msg, {"error_type": "service_unavailable"}
                
        except requests.exceptions.ConnectionError:
            error_msg = "Ollama: 无法连接到本地服务。请确保 Ollama 服务正在运行。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, {"error_type": "connection", "can_retry": True}
        except Exception as e:
            error_msg = f"Ollama: 检查过程中发生错误: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, {"error_type": "unknown", "can_retry": False}
    
    def _check_gemini_availability(self) -> Tuple[bool, str, Dict[str, Any]]:
        """检查Gemini模型可用性"""
        try:
            # 使用fallback机制获取API Key
            api_key, source, validation_result = get_api_key_with_fallback("GEMINI")
            if api_key is None:
                return False, validation_result, {"error_type": "config", "details": validation_result}
            
            base_url = getattr(settings, 'GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta')
            model = resolve_gemini_model(getattr(settings, 'GEMINI_MODEL', None))
            
            # 构建请求头
            headers = {
                "Content-Type": "application/json"
            }
            
            # 构建测试请求
            test_payload = {
                "contents": [{"parts": [{"text": "Hello"}]}],
                "generationConfig": {"maxOutputTokens": 10}
            }
            
            # 发送请求
            response = requests.post(
                f"{base_url}/models/{model}:generateContent?key={api_key}",
                headers=headers,
                json=test_payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.info("✅ Gemini 模型可用性检查通过")
                return True, "Gemini 模型可用", {
                    "model": model,
                    "base_url": base_url,
                    "status_code": response.status_code
                }
            else:
                can_retry, error_msg = handle_api_error(response, "Gemini")
                return False, error_msg, {
                    "error_type": "api_error",
                    "status_code": response.status_code,
                    "can_retry": can_retry,
                    "details": error_msg
                }
                
        except requests.exceptions.Timeout:
            error_msg = "Gemini: 请求超时。请检查网络连接或稍后重试。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, {"error_type": "timeout", "can_retry": True}
        except requests.exceptions.ConnectionError:
            error_msg = "Gemini: 网络连接失败。请检查网络连接和代理设置。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, {"error_type": "connection", "can_retry": True}
        except Exception as e:
            error_msg = f"Gemini: 检查过程中发生未知错误: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, {"error_type": "unknown", "can_retry": False}
    
    def _check_qwen_availability(self) -> Tuple[bool, str, Dict[str, Any]]:
        """检查Qwen模型可用性"""
        try:
            # 使用fallback机制获取API Key
            api_key, source, validation_result = get_api_key_with_fallback("QWEN")
            if api_key is None:
                return False, validation_result, {"error_type": "config", "details": validation_result}
            
            base_url = getattr(settings, 'QWEN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
            model = getattr(settings, 'QWEN_MODEL', 'qwen-flash')
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # 构建测试请求（使用 OpenAI-compatible API）
            test_payload = {
                "model": model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            
            # 发送请求
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=test_payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.info("✅ Qwen 模型可用性检查通过")
                return True, "Qwen 模型可用", {
                    "model": model,
                    "base_url": base_url,
                    "status_code": response.status_code
                }
            else:
                can_retry, error_msg = handle_api_error(response, "Qwen")
                return False, error_msg, {
                    "error_type": "api_error",
                    "status_code": response.status_code,
                    "can_retry": can_retry,
                    "details": error_msg
                }
                
        except requests.exceptions.Timeout:
            error_msg = "Qwen: 请求超时。请检查网络连接或稍后重试。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, {"error_type": "timeout", "can_retry": True}
        except requests.exceptions.ConnectionError:
            error_msg = "Qwen: 网络连接失败。请检查网络连接和代理设置。"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, {"error_type": "connection", "can_retry": True}
        except Exception as e:
            error_msg = f"Qwen: 检查过程中发生未知错误: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, {"error_type": "unknown", "can_retry": False}
    
    def get_model_status_summary(self, company: str) -> Dict[str, Any]:
        """
        获取模型状态摘要
        
        参数:
            company: AI提供商名称
        
        返回:
            Dict: 包含状态信息的字典
        """
        is_available, message, details = self.check_model_availability(company)
        
        return {
            "company": company,
            "service_name": get_service_name(company),
            "is_available": is_available,
            "message": message,
            "details": details,
            "timestamp": self._get_current_timestamp()
        }
    
    @staticmethod
    def _get_current_timestamp() -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


# 全局检查器实例
model_checker = RemoteModelChecker()
