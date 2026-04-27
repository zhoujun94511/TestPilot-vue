#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
配置中心数据库初始化脚本（支持重置模式）

用法：
# 初始化配置中心（保留原有配置）
python scripts/init_config_center.py

# 重置模式（⚠️ 会清空旧数据）
python scripts/init_config_center.py --force
"""
import sys
import os
import argparse
from pathlib import Path

# 设置环境变量，跳过 LLM 初始化（减少初始化过程中的警告）
os.environ['SKIP_LLM_INIT'] = 'true'

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from models.models import db
from models.config_models import ConfigItem, ConfigValidationRule
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


def clear_old_data():
    """清空旧的配置中心数据"""
    try:
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
        app = create_app()
        with app.app_context():
            # 创建配置中心相关表
            db.create_all()
            logger.info("配置中心数据表创建成功")
            return True
    except Exception as e:
        logger.error(f"创建配置中心数据表失败: {e}")
        return False


def init_default_configs():
    """初始化默认配置"""
    try:
        app = create_app()
        with app.app_context():
            # 默认配置项
            default_configs = [
                # AI模型配置
                {'key': 'DEFAULT_COMPANY', 'value': 'OPENAI', 'value_type': 'string',
                 'category': 'ai_model', 'description': '默认AI模型提供商（统一使用大写：OPENAI/DEEPSEEK/GEMINI/QWEN/OLLAMA）', 'is_sensitive': False},
                {'key': 'OPENAI_API_KEY', 'value': '', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'OpenAI API密钥', 'is_sensitive': True},
                {'key': 'OPENAI_BASE_URL', 'value': 'https://api.openai.com/v1', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'OpenAI服务地址', 'is_sensitive': False},
                {'key': 'OPENAI_MODEL', 'value': 'gpt-5', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'OpenAI模型名称', 'is_sensitive': False},
                {'key': 'TR_OPENAI_MAX_TOKENS', 'value': '8000', 'value_type': 'int',
                 'category': 'ai_model', 'description': 'OpenAI用例生成最大Token数', 'is_sensitive': False},
                {'key': 'GPT5_VERBOSITY', 'value': 'low', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'GPT-5详细程度', 'is_sensitive': False},
                {'key': 'GPT5_REASONING_EFFORT', 'value': 'minimal', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'GPT-5推理努力', 'is_sensitive': False},
                {'key': 'DEEPSEEK_API_KEY', 'value': '', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'DeepSeek API密钥', 'is_sensitive': True},
                {'key': 'DEEPSEEK_BASE_URL', 'value': 'https://api.deepseek.com/v1', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'DeepSeek服务地址', 'is_sensitive': False},
                {'key': 'DEEPSEEK_MODEL', 'value': 'deepseek-chat', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'DeepSeek模型名称', 'is_sensitive': False},
                {'key': 'TR_DEEPSEEK_MAX_TOKENS', 'value': '8000', 'value_type': 'int',
                 'category': 'ai_model', 'description': 'DeepSeek用例生成最大Token数', 'is_sensitive': False},
                {'key': 'OLLAMA_BASE_URL', 'value': 'http://127.0.0.1:11434', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Ollama服务地址', 'is_sensitive': False},
                {'key': 'OLLAMA_MODEL', 'value': 'phi:2.7b', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Ollama模型名称', 'is_sensitive': False},
                {'key': 'GEMINI_API_KEY', 'value': '', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Gemini API密钥', 'is_sensitive': True},
                {'key': 'GEMINI_BASE_URL', 'value': 'https://generativelanguage.googleapis.com/v1beta', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Gemini服务地址', 'is_sensitive': False},
                {'key': 'GEMINI_MODEL', 'value': 'gemini-2.0-flash', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Gemini模型名称', 'is_sensitive': False},
                {'key': 'TR_GEMINI_MAX_TOKENS', 'value': '8000', 'value_type': 'int',
                 'category': 'ai_model', 'description': 'Gemini用例生成最大Token数', 'is_sensitive': False},
                {'key': 'QWEN_API_KEY', 'value': '', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Qwen API密钥', 'is_sensitive': True},
                {'key': 'QWEN_BASE_URL', 'value': 'https://dashscope.aliyuncs.com/compatible-mode/v1', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Qwen服务地址', 'is_sensitive': False},
                {'key': 'QWEN_MODEL', 'value': 'qwen-flash', 'value_type': 'string',
                 'category': 'ai_model', 'description': 'Qwen模型名称', 'is_sensitive': False},
                {'key': 'QWEN_TEMPERATURE', 'value': '0.7', 'value_type': 'float',
                 'category': 'ai_model', 'description': 'Qwen温度参数（0.0-2.0）', 'is_sensitive': False},
                {'key': 'TR_QWEN_MAX_TOKENS', 'value': '8000', 'value_type': 'int',
                 'category': 'ai_model', 'description': 'Qwen用例生成最大Token数', 'is_sensitive': False},
                {'key': 'QWEN_TIMEOUT', 'value': '180', 'value_type': 'int',
                 'category': 'ai_model', 'description': 'Qwen请求超时时间（秒），建议180秒（3分钟），用例生成可能需要更长时间', 'is_sensitive': False},
                {'key': 'MAX_TOKENS', 'value': '4000', 'value_type': 'int',
                 'category': 'ai_model', 'description': '通用最大Token数', 'is_sensitive': False},

                # 用例生成配置
                {'key': 'MAX_CASE_NUM', 'value': '50', 'value_type': 'int',
                 'category': 'case_generation', 'description': '最大生成数量', 'is_sensitive': False},
                {'key': 'CONTENT_SIMILARITY_THRESHOLD', 'value': '0.8', 'value_type': 'float',
                 'category': 'case_generation', 'description': '内容相似度阈值', 'is_sensitive': False},
                {'key': 'ENABLE_CONTENT_DEDUP', 'value': 'true', 'value_type': 'bool',
                 'category': 'case_generation', 'description': '启用内容去重', 'is_sensitive': False},
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
                {'key': 'ENABLE_PARALLEL_PROCESSING', 'value': 'true', 'value_type': 'bool',
                 'category': 'performance', 'description': '启用并行处理', 'is_sensitive': False},

                # 知识库检索配置
                {'key': 'RAG_TOP_K', 'value': '5', 'value_type': 'int',
                 'category': 'knowledge', 'description': 'RAG检索结果数量', 'is_sensitive': False},
                {'key': 'RAG_SCORE_THRESHOLD', 'value': '0.7', 'value_type': 'float',
                 'category': 'knowledge', 'description': 'RAG相似度阈值（统一与settings.py保持一致）', 'is_sensitive': False},

                # 文件处理配置
                {'key': 'MAX_MEMORY_MB', 'value': '500', 'value_type': 'int',
                 'category': 'file_processing', 'description': '最大内存使用量(MB)', 'is_sensitive': False}
            ]

            # 插入默认配置
            for config_data in default_configs:
                existing_config = ConfigItem.query.filter_by(key=config_data['key']).first()
                if not existing_config:
                    config_item = ConfigItem(**config_data)
                    db.session.add(config_item)
                    logger.info(f"添加默认配置: {config_data['key']}")

            db.session.commit()
            logger.info("默认配置初始化成功")
            return True

    except Exception as e:
        logger.error(f"初始化默认配置失败: {e}")
        return False


def init_validation_rules():
    """初始化验证规则"""
    try:
        app = create_app()
        with app.app_context():
            validation_rules = [
                # Token数量验证
                {'config_key': 'TR_OPENAI_MAX_TOKENS', 'validation_type': 'enum',
                 'validation_config': {'values': [1000, 2000, 4000, 8000, 10000, 12000]},
                 'error_message': 'OpenAI Token数必须在允许的范围内', 'is_required': True},
                {'config_key': 'TR_DEEPSEEK_MAX_TOKENS', 'validation_type': 'enum',
                 'validation_config': {'values': [1000, 2000, 3000, 4000, 6000, 8000]},
                 'error_message': 'DeepSeek Token数必须在允许的范围内', 'is_required': True},
                {'config_key': 'MAX_TOKENS', 'validation_type': 'enum',
                 'validation_config': {'values': [1000, 2000, 3000, 4000, 6000, 8000]},
                 'error_message': '通用Token数必须在允许的范围内', 'is_required': True},
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
                # DEFAULT_COMPANY 枚举验证（统一使用大写）
                {'config_key': 'DEFAULT_COMPANY', 'validation_type': 'enum',
                 'validation_config': {'values': ['OPENAI', 'DEEPSEEK', 'GEMINI', 'QWEN', 'OLLAMA']},
                 'error_message': 'DEFAULT_COMPANY 必须是以下值之一：OPENAI, DEEPSEEK, GEMINI, QWEN, OLLAMA（统一使用大写）', 'is_required': True},
                # Token数量验证 - Gemini
                {'config_key': 'TR_GEMINI_MAX_TOKENS', 'validation_type': 'enum',
                 'validation_config': {'values': [1000, 2000, 4000, 8000, 10000, 12000]},
                 'error_message': 'Gemini Token数必须在允许的范围内', 'is_required': True},
                # Token数量验证 - Qwen
                {'config_key': 'TR_QWEN_MAX_TOKENS', 'validation_type': 'enum',
                 'validation_config': {'values': [1000, 2000, 4000, 8000, 10000, 12000]},
                 'error_message': 'Qwen Token数必须在允许的范围内', 'is_required': True},
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="配置中心初始化工具")
    parser.add_argument('--force', action='store_true', help="启用重置模式（会清空旧数据）")
    args = parser.parse_args()

    success = main(force_reset=args.force)
    sys.exit(0 if success else 1)
