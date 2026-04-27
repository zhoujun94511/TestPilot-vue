#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
数据迁移脚本：将数据库中的 DEFAULT_COMPANY 值统一转换为大写

使用方法：
    python scripts/migrate_default_company_to_uppercase.py

说明：
    - 此脚本会将数据库中所有 DEFAULT_COMPANY 配置项的值转换为大写
    - 支持的提供商：openai -> OPENAI, deepseek -> DEEPSEEK, gemini -> GEMINI, qwen -> QWEN, ollama -> OLLAMA
    - 如果值已经是大写，则不会修改
    - 如果值不在支持的列表中，会记录警告但不会修改
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from models.models import db
from models.config_models import ConfigItem
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)

# 支持的提供商映射（小写 -> 大写）
PROVIDER_MAPPING = {
    'openai': 'OPENAI',
    'deepseek': 'DEEPSEEK',
    'gemini': 'GEMINI',
    'qwen': 'QWEN',
    'ollama': 'OLLAMA',
}


def migrate_default_company_to_uppercase():
    """将 DEFAULT_COMPANY 值转换为大写"""
    try:
        app = create_app()
        with app.app_context():
            # 查找 DEFAULT_COMPANY 配置项
            config_item = db.session.query(ConfigItem).filter_by(key='DEFAULT_COMPANY').first()
            
            if not config_item:
                logger.info("未找到 DEFAULT_COMPANY 配置项，无需迁移")
                return True, "未找到 DEFAULT_COMPANY 配置项，无需迁移"
            
            old_value = config_item.value
            old_value_lower = old_value.lower() if isinstance(old_value, str) else str(old_value).lower()
            
            # 检查是否需要转换
            if old_value_lower in PROVIDER_MAPPING:
                new_value = PROVIDER_MAPPING[old_value_lower]
                
                # 如果值已经是大写，无需修改
                if old_value == new_value:
                    logger.info(f"DEFAULT_COMPANY 值已经是大写: {old_value}，无需迁移")
                    return True, f"DEFAULT_COMPANY 值已经是大写: {old_value}，无需迁移"
                
                # 更新值
                config_item.value = new_value
                db.session.commit()
                
                logger.info(f"✅ 成功将 DEFAULT_COMPANY 从 '{old_value}' 迁移为 '{new_value}'")
                return True, f"成功将 DEFAULT_COMPANY 从 '{old_value}' 迁移为 '{new_value}'"
            else:
                # 值不在支持的列表中
                if old_value.isupper() and old_value in PROVIDER_MAPPING.values():
                    logger.info(f"DEFAULT_COMPANY 值已经是有效的大写值: {old_value}，无需迁移")
                    return True, f"DEFAULT_COMPANY 值已经是有效的大写值: {old_value}，无需迁移"
                else:
                    logger.warning(f"⚠️ DEFAULT_COMPANY 值 '{old_value}' 不在支持的提供商列表中，跳过迁移")
                    logger.warning(f"支持的提供商: {', '.join(PROVIDER_MAPPING.values())}")
                    return False, f"DEFAULT_COMPANY 值 '{old_value}' 不在支持的提供商列表中"
                    
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        if 'db' in locals() and db.session:
            db.session.rollback()
        return False, f"迁移失败: {str(e)}"


def main():
    """主函数"""
    print("=" * 60)
    print("🔄 DEFAULT_COMPANY 数据迁移脚本")
    print("=" * 60)
    print()
    print("此脚本将把数据库中的 DEFAULT_COMPANY 值统一转换为大写")
    print("支持的提供商：OPENAI, DEEPSEEK, GEMINI, QWEN, OLLAMA")
    print()
    
    confirm = input("确定要继续吗？(y/N，大小写均可): ")
    if confirm.lower() != 'y':
        print("❌ 用户取消操作")
        return
    
    print()
    print("开始迁移...")
    print("-" * 60)
    
    success, message = migrate_default_company_to_uppercase()
    
    print("-" * 60)
    if success:
        print(f"✅ {message}")
        print()
        print("迁移完成！")
    else:
        print(f"❌ {message}")
        print()
        print("迁移失败，请检查日志获取详细信息")
    
    print("=" * 60)


if __name__ == '__main__':
    main()



