#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
from pydantic import SecretStr
from dotenv import load_dotenv
from config.settings import (
    anthropic_rejects_sampling,
    resolve_anthropic_model,
    resolve_deepseek_model,
    resolve_gemini_model,
    resolve_openai_model,
    settings,
)
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from utils.utils_core.logger import get_logger
from utils.utils_core.api_error_handler import get_api_key_with_fallback
from utils.utils_performance_monitoring.token_monitor import get_token_monitor

logger = get_logger(__name__)

load_dotenv()

# 全局缓存字典，避免重复初始化LLM
_llm_cache = {}


def get_llm(company: str, use_cache: bool = True, use_case: str = 'chat'):
    """
    根据 COMPANY 选择不同的 LLM 来源:
    - ollama  → 本地 Ollama
    - deepseek → DeepSeek 云端
    - openai → OpenAI 官方 API
    - gemini → 谷歌 官方 API
    - qwen → 阿里云 Qwen（通义千问）
    - anthropic → Anthropic Claude（Messages API）

    Args:
        company: LLM提供商
        use_cache: 是否使用缓存，默认为True
        use_case: 使用场景，'chat'为AI聊天，'case_generation'为用例生成，'requirement_analysis'为需求分析
    """
    # 验证company参数（统一转换为大写）
    company = company.upper() if company else 'OPENAI'
    valid_companies = ["OLLAMA", "DEEPSEEK", "OPENAI", "GEMINI", "QWEN", "ANTHROPIC"]
    if company not in valid_companies:
        raise ValueError(f"Invalid company: {company}. Supported: {valid_companies}")

    # 获取Token配置
    def get_max_tokens(provider, scenario):
        """根据提供商和使用场景获取Token配置"""
        if scenario == 'chat':
            # AI聊天使用通用Token配置
            return getattr(settings, 'MAX_TOKENS', 4000)
        elif scenario in ['case_generation', 'requirement_analysis']:
            if provider == 'OLLAMA':
                return getattr(settings, 'MAX_TOKENS', 4000)
            unified = getattr(settings, 'TR_MAX_TOKENS', None)
            if unified not in (None, ''):
                try:
                    return int(unified)
                except (TypeError, ValueError):
                    pass
            legacy_map = {
                'OPENAI': 'TR_OPENAI_MAX_TOKENS',
                'DEEPSEEK': 'TR_DEEPSEEK_MAX_TOKENS',
                'GEMINI': 'TR_GEMINI_MAX_TOKENS',
                'QWEN': 'TR_QWEN_MAX_TOKENS',
                'ANTHROPIC': 'TR_ANTHROPIC_MAX_TOKENS',
            }
            legacy_key = legacy_map.get(provider)
            if legacy_key:
                return getattr(settings, legacy_key, 8000)
            return getattr(settings, 'MAX_TOKENS', 4000)
        else:
            # 默认使用通用Token配置
            return getattr(settings, 'MAX_TOKENS', 4000)

    # 如果使用缓存且已存在，直接返回
    cache_key = f"{company}_{use_case}"
    if use_cache and cache_key in _llm_cache:
        return _llm_cache[cache_key]

    # 获取当前场景的Token配置
    max_tokens = get_max_tokens(company, use_case)
    
    if company == "OPENAI":
        # 使用新的API Key获取机制
        api_key, source, validation_result = get_api_key_with_fallback("openai")
        if api_key is None:
            raise ValueError(f"OpenAI API Key 配置失败: {validation_result}")
        
        logger.info(f"OpenAI API Key 来源: {source}")
        model_name = resolve_openai_model(getattr(settings, 'OPENAI_MODEL', None))
        # 统一超时配置（所有模型）
        if use_case == 'case_generation':
            timeout = getattr(settings, 'LLM_TIMEOUT_CASE_GENERATION', 300)
        elif use_case == 'requirement_analysis':
            timeout = getattr(settings, 'LLM_TIMEOUT_REQUIREMENT_ANALYSIS', 300)
        else:
            timeout = getattr(settings, 'LLM_TIMEOUT_DEFAULT', 120)
        
        # 根据模型类型设置不同的参数
        if "gpt-5" in model_name:
            # verbosity 只支持 'low', 'medium', 'high'，不支持 'minimal'
            verbosity = getattr(settings, 'GPT5_VERBOSITY', None) or "low"
            reasoning_effort = getattr(settings, 'GPT5_REASONING_EFFORT', None) or "low"
            # GPT-5 使用 max_completion_tokens 而不是 max_tokens
            llm = ChatOpenAI(
                api_key=SecretStr(api_key),
                base_url=getattr(settings, 'OPENAI_BASE_URL', 'https://api.openai.com/v1'),
                model=model_name,
                max_completion_tokens=max_tokens,  # GPT-5 专用参数
                timeout=timeout,
                extra_body={
                    "verbosity": verbosity,
                    "reasoning_effort": reasoning_effort
                }
            )
        else:
            llm = ChatOpenAI(
                api_key=SecretStr(api_key),
                base_url=getattr(settings, 'OPENAI_BASE_URL', 'https://api.openai.com/v1'),
                model=model_name,
                temperature=0.7,
                max_tokens=max_tokens,
                timeout=timeout
            )

    elif company == "OLLAMA":
        model = getattr(settings, 'OLLAMA_MODEL', None)
        if not model:
            raise ValueError("请在配置中心设置 OLLAMA_MODEL，例如 gemma:2b")
        
        # 注意：ChatOllama 不支持 timeout 参数，超时由 base_url 的 HTTP 客户端控制
        llm = ChatOllama(
            base_url=getattr(settings, 'OLLAMA_BASE_URL', 'http://127.0.0.1:11434'),
            model=model,
            temperature=0.6
        )

    elif company == "DEEPSEEK":
        # 使用新的API Key获取机制
        api_key, source, validation_result = get_api_key_with_fallback("deepseek")
        if api_key is None:
            raise ValueError(f"DeepSeek API Key 配置失败: {validation_result}")
        
        logger.info(f"DeepSeek API Key 来源: {source}")
        
        # 统一超时配置
        if use_case == 'case_generation':
            timeout = getattr(settings, 'LLM_TIMEOUT_CASE_GENERATION', 300)
        elif use_case == 'requirement_analysis':
            timeout = getattr(settings, 'LLM_TIMEOUT_REQUIREMENT_ANALYSIS', 300)
        else:
            timeout = getattr(settings, 'LLM_TIMEOUT_DEFAULT', 120)
        
        model_name = resolve_deepseek_model(getattr(settings, 'DEEPSEEK_MODEL', None))
        llm = ChatDeepSeek(
            api_key=SecretStr(api_key),
            base_url=getattr(settings, 'DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1'),
            model=model_name,
            temperature=1,
            max_tokens=max_tokens,
            timeout=timeout
        )

    elif company == "GEMINI":
        # 使用新的API Key获取机制
        api_key, source, validation_result = get_api_key_with_fallback("gemini")
        if api_key is None:
            raise ValueError(f"Gemini API Key 配置失败: {validation_result}")
        
        logger.info(f"Gemini API Key 来源: {source}")
        
        # 统一超时配置
        if use_case == 'case_generation':
            timeout = getattr(settings, 'LLM_TIMEOUT_CASE_GENERATION', 300)
        elif use_case == 'requirement_analysis':
            timeout = getattr(settings, 'LLM_TIMEOUT_REQUIREMENT_ANALYSIS', 300)
        else:
            timeout = getattr(settings, 'LLM_TIMEOUT_DEFAULT', 120)
        
        # Gemini 不支持在初始化时设置 max_tokens，需要通过 generation_config 在调用时传递
        # max_tokens 会在 chat_service 中通过 generation_config.max_output_tokens 传递
        llm = ChatGoogleGenerativeAI(
            api_key=SecretStr(api_key),
            model=resolve_gemini_model(getattr(settings, 'GEMINI_MODEL', None)),
            temperature=0.7,
            timeout=timeout
        )

    elif company == "QWEN":
        # 使用新的API Key获取机制
        api_key, source, validation_result = get_api_key_with_fallback("qwen")
        if api_key is None:
            raise ValueError(f"Qwen API Key 配置失败: {validation_result}")
        
        logger.info(f"Qwen API Key 来源: {source}")
        # Qwen 使用 OpenAI-compatible API，通过 ChatOpenAI 接入
        base_url = getattr(settings, 'QWEN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        model = getattr(settings, 'QWEN_MODEL', None) or os.getenv("QWEN_MODEL", "qwen-flash")
        temperature = getattr(settings, 'QWEN_TEMPERATURE', 0.7)
        # 根据用例类型设置不同的超时时间：用例生成和需求分析需要更长时间
        if use_case == 'case_generation':
            default_timeout = 180
        elif use_case == 'requirement_analysis':
            default_timeout = 180  # 需求分析、测试点提取、业务规则提取都需要较长时间
        else:
            default_timeout = 120
        timeout = getattr(settings, 'QWEN_TIMEOUT', default_timeout)
        logger.info(f"Qwen 超时设置: {timeout}秒 (use_case: {use_case})")
        llm = ChatOpenAI(
            api_key=SecretStr(api_key),
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )

    elif company == "ANTHROPIC":
        api_key, source, validation_result = get_api_key_with_fallback("anthropic")
        if api_key is None:
            raise ValueError(f"Anthropic API Key 配置失败: {validation_result}")

        logger.info(f"Anthropic API Key 来源: {source}")
        if use_case == 'case_generation':
            timeout = getattr(settings, 'LLM_TIMEOUT_CASE_GENERATION', 300)
        elif use_case == 'requirement_analysis':
            timeout = getattr(settings, 'LLM_TIMEOUT_REQUIREMENT_ANALYSIS', 300)
        else:
            timeout = getattr(settings, 'LLM_TIMEOUT_DEFAULT', 120)

        model_name = resolve_anthropic_model(getattr(settings, 'ANTHROPIC_MODEL', None))
        # 当前 Claude 拒绝 temperature / top_p / top_k。旧型号仍按其他厂商的 0.7。
        anthropic_kwargs = {
            'api_key': SecretStr(api_key),
            'base_url': getattr(settings, 'ANTHROPIC_BASE_URL', 'https://api.anthropic.com'),
            'model': model_name,
            'max_tokens': max_tokens,
            'timeout': timeout,
        }
        if not anthropic_rejects_sampling(model_name):
            anthropic_kwargs['temperature'] = 0.7
        llm = ChatAnthropic(**anthropic_kwargs)

    else:
        raise ValueError(f"Invalid company name: {company}. Supported: OPENAI, OLLAMA, DEEPSEEK, GEMINI, QWEN, ANTHROPIC")

    # 只在首次创建时打印日志
    if use_cache:
        # 根据不同的company获取对应的模型名称
        if company == "OPENAI":
            model_name = resolve_openai_model(getattr(settings, 'OPENAI_MODEL', None))
        elif company == "OLLAMA":
            model_name = getattr(settings, 'OLLAMA_MODEL', None) or os.getenv('OLLAMA_MODEL', 'gemma:2b')
        elif company == "DEEPSEEK":
            model_name = resolve_deepseek_model(getattr(settings, 'DEEPSEEK_MODEL', None))
        elif company == "GEMINI":
            model_name = resolve_gemini_model(getattr(settings, 'GEMINI_MODEL', None))
        elif company == "QWEN":
            model_name = getattr(settings, 'QWEN_MODEL', None) or os.getenv('QWEN_MODEL', 'qwen-flash')
        elif company == "ANTHROPIC":
            model_name = resolve_anthropic_model(getattr(settings, 'ANTHROPIC_MODEL', None))
        else:
            model_name = settings.MODEL

        logger.info(f"已加载 LLM 配置 → COMPANY={company}, MODEL={model_name}, USE_CASE={use_case}, MAX_TOKENS={max_tokens}")

        # 添加 Token 消耗监控日志
        token_monitor = get_token_monitor(model_name)
        logger.info(f"Token监控器已初始化，当前限制: {token_monitor.max_tokens_per_session:,} tokens")
        _llm_cache[cache_key] = llm

    return llm


def get_llm_instance(company: str = None, use_cache: bool = True, use_case: str = 'chat'):
    """
    获取LLM实例的便捷函数
    
    Args:
        company: LLM提供商，如果为None则使用默认配置
        use_cache: 是否使用缓存
        use_case: 使用场景
    
    Returns:
        LLM实例
    """
    if company is None:
        # 使用默认的LLM提供商
        company = getattr(settings, 'DEFAULT_COMPANY', 'OPENAI')
    
    return get_llm(company, use_cache, use_case)


def clear_llm_cache():
    """清除LLM缓存，用于重新初始化"""
    global _llm_cache
    _llm_cache.clear()
    logger.info("LLM缓存已清除")