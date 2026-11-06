#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
配置中心数据库初始化脚本（支持重置模式）

用法：
# 初始化配置中心（保留原有配置）
python scripts/init_config_center.py

# 重置模式（会清空配置中心旧数据但保留表结构）
python scripts/init_config_center.py --force
"""
import sys
import os
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.models import db
from models.config_models import ConfigItem, ConfigValidationRule
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)

AI_PROVIDER_NAMES = ('OPENAI', 'DEEPSEEK', 'OLLAMA', 'GEMINI', 'QWEN', 'ANTHROPIC')
AI_PROVIDER_KEY_ROWS = (
    ('OPENAI_API_KEY', 'OpenAI API密钥'),
    ('DEEPSEEK_API_KEY', 'DeepSeek API密钥'),
    ('GEMINI_API_KEY', 'Gemini API密钥'),
    ('QWEN_API_KEY', 'Qwen API密钥'),
    ('ANTHROPIC_API_KEY', 'Anthropic API密钥'),
)


def clear_old_data():
    """清空旧的配置中心数据"""
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            deleted_items = ConfigItem.query.delete()
            deleted_rules = ConfigValidationRule.query.delete()
            db.session.commit()
            logger.warning(f"⚠️ 已清空旧配置：{deleted_items} 条配置项，{deleted_rules} 条验证规则。")
            print(f"⚠️ 已清空旧配置：{deleted_items} 条配置项，{deleted_rules} 条验证规则。")
            return True
    except Exception as e:
        logger.error(f"清空旧配置失败: {e}")
        return False


def init_config_center_tables():
    """初始化配置中心数据表"""
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            # 创建配置中心相关表
            db.create_all()
            logger.info("配置中心数据表创建成功")
            return True
    except Exception as e:
        logger.error(f"创建配置中心数据表失败: {e}")
        return False


def _env_flag(name: str, default: str = 'true') -> str:
    return 'true' if os.getenv(name, default).strip().lower() in ('true', '1', 'yes', 'on') else 'false'


def _feature_flag_rows():
    """功能开关按 .env 的当前取值写入，避免配置中心覆盖已生效的设置。"""
    return [
        {'key': 'ENABLE_VECTOR_STORE', 'value': _env_flag('ENABLE_VECTOR_STORE'), 'value_type': 'bool',
         'category': 'knowledge', 'description': '启用知识库向量存储', 'is_sensitive': False},
        {'key': 'ENABLE_EXPERIMENTAL_ACTIONS', 'value': _env_flag('ENABLE_EXPERIMENTAL_ACTIONS'), 'value_type': 'bool',
         'category': 'performance', 'description': '启用实验工具', 'is_sensitive': False},
    ]


def seed_default_configs():
    """补齐缺失的配置项。调用方必须已处于 Flask app context，且不覆盖已有值。"""
    try:
        if True:
            # 默认配置项
            default_configs = [
                # AI模型配置
                {'key': 'DEFAULT_COMPANY', 'value': 'OPENAI', 'value_type': 'string',
                 'category': 'ai_model', 'description': '默认AI模型提供商（统一使用大写：OPENAI/DEEPSEEK/GEMINI/QWEN/ANTHROPIC/OLLAMA）', 'is_sensitive': False},
                {'key': 'OPENAI_API_KEY', 'value': '', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'OpenAI API密钥', 'is_sensitive': True},
                {'key': 'OPENAI_BASE_URL', 'value': 'https://api.openai.com/v1', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'OpenAI服务地址', 'is_sensitive': False},
                {'key': 'OPENAI_MODEL', 'value': 'gpt-5', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'OpenAI模型名称', 'is_sensitive': False},
                {'key': 'TR_MAX_TOKENS', 'value': '8000', 'value_type': 'int',
                 'category': 'ai_model', 'description': '用例生成与需求分析单次最大词元数（各厂商共用）', 'is_sensitive': False},
                {'key': 'TR_OPENAI_MAX_TOKENS', 'value': '8000', 'value_type': 'int',
                 'category': 'ai_model', 'description': 'OpenAI 用例生成单次最大词元数', 'is_sensitive': False},
                {'key': 'GPT5_VERBOSITY', 'value': 'low', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'GPT-5详细程度', 'is_sensitive': False},
                {'key': 'GPT5_REASONING_EFFORT', 'value': 'minimal', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'GPT-5推理努力', 'is_sensitive': False},
                {'key': 'DEEPSEEK_API_KEY', 'value': '', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'DeepSeek API密钥', 'is_sensitive': True},
                {'key': 'DEEPSEEK_BASE_URL', 'value': 'https://api.deepseek.com/v1', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'DeepSeek服务地址', 'is_sensitive': False},
                {'key': 'DEEPSEEK_MODEL', 'value': 'deepseek-flash', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'DeepSeek模型名称', 'is_sensitive': False},
                {'key': 'TR_DEEPSEEK_MAX_TOKENS', 'value': '8000', 'value_type': 'int',
                 'category': 'ai_model', 'description': 'DeepSeek 用例生成单次最大词元数', 'is_sensitive': False},
                {'key': 'OLLAMA_BASE_URL', 'value': 'http://127.0.0.1:11434', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Ollama服务地址', 'is_sensitive': False},
                {'key': 'OLLAMA_MODEL', 'value': 'phi:2.7b', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Ollama模型名称', 'is_sensitive': False},
                {'key': 'GEMINI_API_KEY', 'value': '', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Gemini API密钥', 'is_sensitive': True},
                {'key': 'GEMINI_BASE_URL', 'value': 'https://generativelanguage.googleapis.com/v1beta', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Gemini服务地址', 'is_sensitive': False},
                {'key': 'GEMINI_MODEL', 'value': 'gemini-3.8-flash', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Gemini模型名称', 'is_sensitive': False},
                {'key': 'TR_GEMINI_MAX_TOKENS', 'value': '8000', 'value_type': 'int',
                 'category': 'ai_model', 'description': 'Gemini 用例生成单次最大词元数', 'is_sensitive': False},
                {'key': 'QWEN_API_KEY', 'value': '', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Qwen API密钥', 'is_sensitive': True},
                {'key': 'QWEN_BASE_URL', 'value': 'https://dashscope.aliyuncs.com/compatible-mode/v1', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Qwen服务地址', 'is_sensitive': False},
                {'key': 'QWEN_MODEL', 'value': 'qwen-flash', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Qwen模型名称', 'is_sensitive': False},
                {'key': 'QWEN_TEMPERATURE', 'value': '0.7', 'value_type': 'float',
                 'category': 'ai_model', 'description': 'Qwen温度参数（0.0-2.0）', 'is_sensitive': False},
                {'key': 'TR_QWEN_MAX_TOKENS', 'value': '8000', 'value_type': 'int',
                 'category': 'ai_model', 'description': 'Qwen 用例生成单次最大词元数', 'is_sensitive': False},
                {'key': 'QWEN_TIMEOUT', 'value': '180', 'value_type': 'int',
                 'category': 'ai_model', 'description': 'Qwen请求超时时间（秒），建议180秒（3分钟），用例生成可能需要更长时间', 'is_sensitive': False},
                {'key': 'ANTHROPIC_API_KEY', 'value': '', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Anthropic API密钥', 'is_sensitive': True},
                {'key': 'ANTHROPIC_BASE_URL', 'value': 'https://api.anthropic.com', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Anthropic服务地址', 'is_sensitive': False},
                {'key': 'ANTHROPIC_MODEL', 'value': 'claude-sonnet-5-5', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Anthropic模型名称', 'is_sensitive': False},
                {'key': 'TR_ANTHROPIC_MAX_TOKENS', 'value': '8000', 'value_type': 'int',
                 'category': 'ai_model', 'description': 'Anthropic 用例生成单次最大词元数', 'is_sensitive': False},
                {'key': 'MAX_TOKENS', 'value': '4000', 'value_type': 'int',
                 'category': 'ai_model', 'description': '聊天、快捷回复与 Ollama 单次最大词元数', 'is_sensitive': False},

                # 用例生成配置
                {'key': 'MAX_CASE_NUM', 'value': '50', 'value_type': 'int',
                 'category': 'case_generation', 'description': '最大生成数量', 'is_sensitive': False},
                {'key': 'CONTENT_SIMILARITY_THRESHOLD', 'value': '0.8', 'value_type': 'float',
                 'category': 'case_generation', 'description': '内容相似度阈值', 'is_sensitive': False},
                {'key': 'ENABLE_CONTENT_DEDUP', 'value': 'true', 'value_type': 'bool',
                 'category': 'case_generation', 'description': '启用内容去重', 'is_sensitive': False},
                {'key': 'ENABLE_HALLUCINATION_DETECTION', 'value': 'true', 'value_type': 'bool',
                 'category': 'case_generation', 'description': '启用幻觉检测', 'is_sensitive': False},
                {'key': 'ENABLE_CASE_GENERATION_RAG', 'value': 'false', 'value_type': 'bool',
                 'category': 'case_generation', 'description': '启用用例生成知识库增强', 'is_sensitive': False},
                {'key': 'CONTENT_DEDUP_BATCH_SIZE', 'value': '100', 'value_type': 'int',
                 'category': 'case_generation', 'description': '去重批次大小', 'is_sensitive': False},
                {'key': 'CONTENT_DEDUP_WEIGHTS',
                 'value': '{"title": 0.4, "steps": 0.3, "expected": 0.2, "preconditions": 0.1}',
                 'value_type': 'json', 'category': 'case_generation',
                 'description': '内容去重权重配置', 'is_sensitive': False},

                # 性能优化配置
                {'key': 'CHUNK_SIZE', 'value': '1000', 'value_type': 'int',
                 'category': 'performance', 'description': '处理块大小', 'is_sensitive': False},
                {'key': 'MAX_WORKERS', 'value': '3', 'value_type': 'int',
                 'category': 'performance', 'description': '最大工作线程', 'is_sensitive': False},
                {'key': 'ENABLE_PARALLEL_PROCESSING', 'value': 'true', 'value_type': 'bool',
                 'category': 'performance', 'description': '启用并行处理', 'is_sensitive': False},
                {'key': 'ENABLE_STREAMING', 'value': 'true', 'value_type': 'bool',
                 'category': 'performance', 'description': '启用流式处理', 'is_sensitive': False},
                *_feature_flag_rows(),

                # 知识库检索配置
                {'key': 'RAG_TOP_K', 'value': '5', 'value_type': 'int',
                 'category': 'knowledge', 'description': 'RAG检索结果数量', 'is_sensitive': False},
                {'key': 'RAG_SCORE_THRESHOLD', 'value': '0.7', 'value_type': 'float',
                 'category': 'knowledge', 'description': 'RAG相似度阈值（统一与settings.py保持一致）', 'is_sensitive': False},

                # 文件处理配置
                {'key': 'MAX_MEMORY_MB', 'value': '500', 'value_type': 'int',
                 'category': 'file_processing', 'description': '最大内存使用量(MB)', 'is_sensitive': False},

                # Token 会话熔断（与 TokenMonitor 对齐，UI 与请求上限同区）
                {'key': 'TOKEN_MAX_PER_SESSION', 'value': '50000', 'value_type': 'int',
                 'category': 'ai_model', 'description': '单会话累计词元上限（超过则拒绝继续调用）', 'is_sensitive': False},
                {'key': 'TOKEN_MAX_CALLS_PER_SESSION', 'value': '100', 'value_type': 'int',
                 'category': 'ai_model', 'description': '单会话模型最大调用次数', 'is_sensitive': False},
            ]

            env_company = os.getenv('DEFAULT_COMPANY', '').strip().upper()
            if env_company:
                for item in default_configs:
                    if item['key'] == 'DEFAULT_COMPANY':
                        item['value'] = env_company

            existing_default = ConfigItem.query.filter_by(key='DEFAULT_COMPANY').first()
            chosen_company = str(existing_default.value or '').strip().upper() if existing_default else ''
            if chosen_company not in AI_PROVIDER_NAMES:
                chosen_company = next(
                    (str(item['value'] or '').strip().upper() for item in default_configs if item['key'] == 'DEFAULT_COMPANY'),
                    'OPENAI',
                )
            for provider_name in AI_PROVIDER_NAMES:
                default_configs.append({
                    'key': f'ENABLE_{provider_name}',
                    'value': 'true' if provider_name == chosen_company else 'false',
                    'value_type': 'bool',
                    'category': 'ai_model',
                    'description': f'是否启用 {provider_name}',
                    'is_sensitive': False,
                })

            # 插入默认配置
            retired_models = {
                'DEEPSEEK_MODEL': ({'deepseek-chat', 'deepseek-reasoner', 'deepseek-coder'}, 'deepseek-flash'),
                'GEMINI_MODEL': ({
                    'gemini-2.0-flash', 'gemini-2.0-flash-001', 'gemini-1.5-pro',
                    'gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-pro',
                }, 'gemini-3.8-flash'),
                'OPENAI_MODEL': ({
                    'gpt-4-turbo', 'gpt-4-turbo-2024-04-09', 'gpt-3.5-turbo',
                    'gpt-3.5-turbo-0125', 'gpt-4', 'gpt-4-0613',
                }, 'gpt-5'),
            }
            for config_data in default_configs:
                existing_config = ConfigItem.query.filter_by(key=config_data['key']).first()
                if not existing_config:
                    config_item = ConfigItem(**config_data)
                    db.session.add(config_item)
                    logger.info(f"添加默认配置: {config_data['key']}")
                    continue
                retired = retired_models.get(config_data['key'])
                if retired and str(existing_config.value or '').strip() in retired[0]:
                    existing_config.value = retired[1]
                    logger.info(f"{config_data['key']} 已从停用名称更新为 {retired[1]}")

            for migrate_key in ('TOKEN_MAX_PER_SESSION', 'TOKEN_MAX_CALLS_PER_SESSION'):
                migrated = ConfigItem.query.filter_by(key=migrate_key).first()
                if migrated and migrated.category != 'ai_model':
                    migrated.category = 'ai_model'
                    logger.info('迁移配置分类: %s -> ai_model', migrate_key)

            unified_generation = ConfigItem.query.filter_by(key='TR_MAX_TOKENS').first()
            if not unified_generation:
                seed = ConfigItem.query.filter_by(key='TR_OPENAI_MAX_TOKENS').first()
                seed_value = seed.value if seed and str(seed.value).strip() else '8000'
                db.session.add(ConfigItem(
                    key='TR_MAX_TOKENS',
                    value=seed_value,
                    value_type='int',
                    category='ai_model',
                    description='用例生成与需求分析单次最大词元数（各厂商共用）',
                    is_sensitive=False,
                ))
                logger.info('添加统一词元配置 TR_MAX_TOKENS=%s', seed_value)
            else:
                sync_value = str(unified_generation.value or '').strip()
                if sync_value:
                    for legacy_key in (
                        'TR_OPENAI_MAX_TOKENS', 'TR_DEEPSEEK_MAX_TOKENS',
                        'TR_GEMINI_MAX_TOKENS', 'TR_QWEN_MAX_TOKENS', 'TR_ANTHROPIC_MAX_TOKENS',
                    ):
                        legacy = ConfigItem.query.filter_by(key=legacy_key).first()
                        if legacy and str(legacy.value or '').strip() != sync_value:
                            legacy.value = sync_value

            db.session.commit()
            logger.info("默认配置初始化成功")
            return True

    except Exception as e:
        logger.error(f"初始化默认配置失败: {e}")
        return False


def ensure_ai_provider_rows():
    """只补缺失的服务商密钥、启用开关和功能开关。不恢复用户删除的其他配置，也不覆盖已有值。"""
    try:
        default_row = ConfigItem.query.filter_by(key='DEFAULT_COMPANY').first()
        chosen = str(default_row.value or '').strip().upper() if default_row else ''
        if chosen not in AI_PROVIDER_NAMES:
            chosen = os.getenv('DEFAULT_COMPANY', 'OPENAI').strip().upper()
        if chosen not in AI_PROVIDER_NAMES:
            chosen = 'OPENAI'
        for row in _feature_flag_rows():
            if ConfigItem.query.filter_by(key=row['key']).first():
                continue
            db.session.add(ConfigItem(**row))
            logger.info('补齐缺失配置: %s', row['key'])
        for key, description in AI_PROVIDER_KEY_ROWS:
            if ConfigItem.query.filter_by(key=key).first():
                continue
            db.session.add(ConfigItem(
                key=key,
                value='',
                value_type='string',
                category='ai_model',
                description=description,
                is_sensitive=True,
            ))
            logger.info('补齐缺失配置: %s', key)
        for provider_name in AI_PROVIDER_NAMES:
            key = f'ENABLE_{provider_name}'
            if ConfigItem.query.filter_by(key=key).first():
                continue
            db.session.add(ConfigItem(
                key=key,
                value='true' if provider_name == chosen else 'false',
                value_type='bool',
                category='ai_model',
                description=f'是否启用 {provider_name}',
                is_sensitive=False,
            ))
            logger.info('补齐缺失配置: %s', key)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        logger.warning('补齐 AI 服务商配置失败: %s', e)
        return False


def init_default_configs():
    """脚本入口：新建应用上下文后补齐配置。"""
    from app import create_app
    app = create_app()
    with app.app_context():
        return seed_default_configs()


def seed_validation_rules():
    """补齐缺失的验证规则。调用方必须已处于 Flask app context。"""
    try:
        if True:
            validation_rules = [
                # Token数量验证
                {'config_key': 'TR_OPENAI_MAX_TOKENS', 'validation_type': 'enum',
                 'validation_config': {'values': [1000, 2000, 4000, 8000, 10000, 12000]},
                 'error_message': 'OpenAI 词元数必须在允许的范围内', 'is_required': True},
                {'config_key': 'TR_DEEPSEEK_MAX_TOKENS', 'validation_type': 'enum',
                 'validation_config': {'values': [1000, 2000, 3000, 4000, 6000, 8000]},
                 'error_message': 'DeepSeek 词元数必须在允许的范围内', 'is_required': True},
                {'config_key': 'MAX_TOKENS', 'validation_type': 'enum',
                 'validation_config': {'values': [1000, 2000, 3000, 4000, 6000, 8000]},
                 'error_message': '聊天词元数必须在允许的范围内', 'is_required': True},
                {'config_key': 'TR_MAX_TOKENS', 'validation_type': 'enum',
                 'validation_config': {'values': [1000, 2000, 4000, 8000, 10000, 12000]},
                 'error_message': '用例与需求分析词元数必须在允许的范围内', 'is_required': True},
                # 数值范围验证
                {'config_key': 'MAX_CASE_NUM', 'validation_type': 'range',
                 'validation_config': {'min': 1, 'max': 100},
                 'error_message': '最大生成数量必须在1-100之间', 'is_required': True},
                {'config_key': 'CONTENT_SIMILARITY_THRESHOLD', 'validation_type': 'range',
                 'validation_config': {'min': 0.1, 'max': 1.0},
                 'error_message': '相似度阈值必须在0.1-1.0之间', 'is_required': True},
                {'config_key': 'CHUNK_SIZE', 'validation_type': 'range',
                 'validation_config': {'min': 100, 'max': 10000},
                 'error_message': '处理块大小必须在100-10000之间', 'is_required': True},
                {'config_key': 'MAX_WORKERS', 'validation_type': 'range',
                 'validation_config': {'min': 1, 'max': 10},
                 'error_message': '最大工作线程必须在1-10之间', 'is_required': True},
                {'config_key': 'RAG_TOP_K', 'validation_type': 'range',
                 'validation_config': {'min': 1, 'max': 20},
                 'error_message': 'RAG检索结果数量必须在1-20之间', 'is_required': True},
                {'config_key': 'RAG_SCORE_THRESHOLD', 'validation_type': 'range',
                 'validation_config': {'min': 0.1, 'max': 1.0},
                 'error_message': 'RAG相似度阈值必须在0.1-1.0之间', 'is_required': True},
                {'config_key': 'MAX_MEMORY_MB', 'validation_type': 'range',
                 'validation_config': {'min': 100, 'max': 2000},
                 'error_message': '最大内存使用量必须在100-2000MB之间', 'is_required': True},
                {'config_key': 'TOKEN_MAX_PER_SESSION', 'validation_type': 'range',
                 'validation_config': {'min': 1000, 'max': 500000},
                 'error_message': '单会话词元上限必须在 1000-500000 之间', 'is_required': True},
                {'config_key': 'TOKEN_MAX_CALLS_PER_SESSION', 'validation_type': 'range',
                 'validation_config': {'min': 1, 'max': 1000},
                 'error_message': '单会话调用次数必须在 1-1000 之间', 'is_required': True},
                # URL格式验证
                {'config_key': 'OPENAI_BASE_URL', 'validation_type': 'regex',
                 'validation_config': {'pattern': r'^https?://.*'},
                 'error_message': 'OpenAI服务地址必须是有效的URL', 'is_required': True},
                {'config_key': 'DEEPSEEK_BASE_URL', 'validation_type': 'regex',
                 'validation_config': {'pattern': r'^https?://.*'},
                 'error_message': 'DeepSeek服务地址必须是有效的URL', 'is_required': True},
                {'config_key': 'OLLAMA_BASE_URL', 'validation_type': 'regex',
                 'validation_config': {'pattern': r'^https?://.*'},
                 'error_message': 'Ollama服务地址必须是有效的URL', 'is_required': True},
                {'config_key': 'GEMINI_BASE_URL', 'validation_type': 'regex',
                 'validation_config': {'pattern': r'^https?://.*'},
                 'error_message': 'Gemini服务地址必须是有效的URL', 'is_required': True},
                {'config_key': 'QWEN_BASE_URL', 'validation_type': 'regex',
                 'validation_config': {'pattern': r'^https?://.*'},
                 'error_message': 'Qwen服务地址必须是有效的URL', 'is_required': True},
                {'config_key': 'ANTHROPIC_BASE_URL', 'validation_type': 'regex',
                 'validation_config': {'pattern': r'^https?://.*'},
                 'error_message': 'Anthropic服务地址必须是有效的URL', 'is_required': True},
                # DEFAULT_COMPANY 枚举验证（统一使用大写）
                {'config_key': 'DEFAULT_COMPANY', 'validation_type': 'enum',
                 'validation_config': {'values': ['OPENAI', 'DEEPSEEK', 'GEMINI', 'QWEN', 'ANTHROPIC', 'OLLAMA']},
                 'error_message': 'DEFAULT_COMPANY 必须是以下值之一：OPENAI, DEEPSEEK, GEMINI, QWEN, ANTHROPIC, OLLAMA（统一使用大写）', 'is_required': True},
                # Token数量验证 - Gemini
                {'config_key': 'TR_GEMINI_MAX_TOKENS', 'validation_type': 'enum',
                 'validation_config': {'values': [1000, 2000, 4000, 8000, 10000, 12000]},
                 'error_message': 'Gemini 词元数必须在允许的范围内', 'is_required': True},
                # Token数量验证 - Qwen
                {'config_key': 'TR_QWEN_MAX_TOKENS', 'validation_type': 'enum',
                 'validation_config': {'values': [1000, 2000, 4000, 8000, 10000, 12000]},
                 'error_message': 'Qwen 词元数必须在允许的范围内', 'is_required': True},
                {'config_key': 'TR_ANTHROPIC_MAX_TOKENS', 'validation_type': 'enum',
                 'validation_config': {'values': [1000, 2000, 4000, 8000, 10000, 12000]},
                 'error_message': 'Anthropic 词元数必须在允许的范围内', 'is_required': True},
                # Temperature验证 - Qwen
                {'config_key': 'QWEN_TEMPERATURE', 'validation_type': 'range',
                 'validation_config': {'min': 0.0, 'max': 2.0},
                 'error_message': 'Qwen温度参数必须在0.0-2.0之间', 'is_required': True},
                # Timeout验证 - Qwen
                {'config_key': 'QWEN_TIMEOUT', 'validation_type': 'range',
                 'validation_config': {'min': 10, 'max': 300},
                 'error_message': 'Qwen超时时间必须在10-300秒之间', 'is_required': True},
                # 布尔值验证
                {'config_key': 'ENABLE_PARALLEL_PROCESSING', 'validation_type': 'enum',
                 'validation_config': {'values': [True, False, 'true', 'false', '1', '0']},
                 'error_message': '并行处理开关必须是布尔值', 'is_required': True},
                {'config_key': 'ENABLE_STREAMING', 'validation_type': 'enum',
                 'validation_config': {'values': [True, False, 'true', 'false', '1', '0']},
                 'error_message': '流式处理开关必须是布尔值', 'is_required': True},
                {'config_key': 'ENABLE_CONTENT_DEDUP', 'validation_type': 'enum',
                 'validation_config': {'values': [True, False, 'true', 'false', '1', '0']},
                 'error_message': '内容去重开关必须是布尔值', 'is_required': True},
                {'config_key': 'ENABLE_HALLUCINATION_DETECTION', 'validation_type': 'enum',
                 'validation_config': {'values': [True, False, 'true', 'false', '1', '0']},
                 'error_message': '幻觉检测开关必须是布尔值', 'is_required': True},
                {'config_key': 'ENABLE_CASE_GENERATION_RAG', 'validation_type': 'enum',
                 'validation_config': {'values': [True, False, 'true', 'false', '1', '0']},
                 'error_message': '用例生成知识库增强开关必须是布尔值', 'is_required': True}
            ]

            # 插入验证规则
            for rule_data in validation_rules:
                existing_rule = ConfigValidationRule.query.filter_by(
                    config_key=rule_data['config_key']
                ).first()
                if not existing_rule:
                    validation_rule = ConfigValidationRule(**rule_data)
                    db.session.add(validation_rule)
                    logger.info(f"添加验证规则: {rule_data['config_key']}")
                    continue
                if rule_data['config_key'] == 'DEFAULT_COMPANY':
                    current_values = list((existing_rule.validation_config or {}).get('values') or [])
                    if 'ANTHROPIC' not in current_values:
                        existing_rule.validation_config = rule_data['validation_config']
                        existing_rule.error_message = rule_data['error_message']
                        logger.info('DEFAULT_COMPANY 枚举已加入 ANTHROPIC')

            db.session.commit()
            logger.info("验证规则初始化成功")
            return True

    except Exception as e:
        logger.error(f"初始化验证规则失败: {e}")
        return False


def main(force_reset=False):
    """主函数"""
    print("🚀 配置中心初始化脚本")
    print("=" * 50)

    if force_reset:
        print("⚠️ 警告：你正在使用【重置模式】，旧数据将被删除！")
        confirm = input("确定要继续吗？(y/N，大小写均可): ")
        if confirm.lower() != 'y':
            print("❌ 操作已取消。")
            return False
        if not clear_old_data():
            print("❌ 清空旧配置失败，终止执行。")
            return False

    # 初始化数据表
    print("📋 创建配置中心数据表...")
    if not init_config_center_tables():
        print("❌ 数据表创建失败")
        return False
    print("✅ 数据表创建成功")

    # 初始化默认配置
    print("⚙️ 初始化默认配置...")
    if not init_default_configs():
        print("❌ 默认配置初始化失败")
        return False
    print("✅ 默认配置初始化成功")

    # 初始化验证规则
    print("🔍 初始化验证规则...")
    if not init_validation_rules():
        print("❌ 验证规则初始化失败")
        return False
    print("✅ 验证规则初始化成功")

    print("\n🎉 配置中心初始化完成！")
    print("现在可以通过前端界面管理配置了。")
    return True


def init_validation_rules():
    """脚本入口：新建应用上下文后补齐验证规则。"""
    from app import create_app
    app = create_app()
    with app.app_context():
        return seed_validation_rules()


if __name__ == '__main__':
    os.environ['SKIP_LLM_INIT'] = 'true'
    parser = argparse.ArgumentParser(description="配置中心初始化工具")
    parser.add_argument('--force', action='store_true', help="启用重置模式（会清空旧数据）")
    args = parser.parse_args()

    success = main(force_reset=args.force)
    sys.exit(0 if success else 1)
