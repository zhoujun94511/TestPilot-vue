# -*- coding: utf-8 -*-
"""
配置中心数据查询脚本
查询配置中心中的数据在数据库中的存储情况

用法:
# 查询所有配置
python scripts/query_config_center.py

# 查询特定分类的配置
python scripts/query_config_center.py --category ai_model

# 查询敏感配置
python scripts/query_config_center.py --sensitive

# 查询审计日志
python scripts/query_config_center.py --audit

# 显示敏感配置的实际值
python scripts/query_config_center.py --sensitive --show-sensitive

# 使用SQLite查看
sqlite3 testpilot.db "SELECT key, value FROM config_items WHERE key LIKE '%API_KEY%';"

# 导出配置数据
python scripts/query_config_center.py --export config_export.json
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.models import db
from models.config_models import ConfigItem, ConfigAuditLog, ConfigValidationRule
from utils.utils_core.logger import get_logger
# 设置控制台编码为UTF-8
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from app import create_app  # 导入Flask应用创建函数

logger = get_logger(__name__)


class ConfigCenterQuery:
    """配置中心查询类"""
    
    def __init__(self):
        self.session = db.session
    
    def get_all_configs(self) -> List[Dict]:
        """获取所有配置项"""
        try:
            configs = self.session.query(ConfigItem).order_by(ConfigItem.category, ConfigItem.key).all()
            return [config.to_dict() for config in configs]
        except Exception as e:
            logger.error(f"获取所有配置失败: {e}")
            return []
    
    def get_configs_by_category(self, category: str) -> List[Dict]:
        """根据分类获取配置项"""
        try:
            configs = self.session.query(ConfigItem).filter_by(category=category).order_by(ConfigItem.key).all()
            return [config.to_dict() for config in configs]
        except Exception as e:
            logger.error(f"获取分类配置失败: {category}, 错误: {e}")
            return []
    
    def get_sensitive_configs(self) -> List[Dict]:
        """获取敏感配置项"""
        try:
            configs = self.session.query(ConfigItem).filter_by(is_sensitive=True).order_by(ConfigItem.category, ConfigItem.key).all()
            return [config.to_dict() for config in configs]
        except Exception as e:
            logger.error(f"获取敏感配置失败: {e}")
            return []
    
    def get_audit_logs(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取审计日志"""
        try:
            logs = self.session.query(ConfigAuditLog).order_by(
                ConfigAuditLog.created_at.desc()
            ).offset(offset).limit(limit).all()
            return [log.to_dict() for log in logs]
        except Exception as e:
            logger.error(f"获取审计日志失败: {e}")
            return []
    
    def get_validation_rules(self) -> List[Dict]:
        """获取验证规则"""
        try:
            rules = self.session.query(ConfigValidationRule).order_by(ConfigValidationRule.config_key).all()
            return [rule.to_dict() for rule in rules]
        except Exception as e:
            logger.error(f"获取验证规则失败: {e}")
            return []
    
    def get_config_statistics(self) -> Dict[str, Any]:
        """获取配置统计信息"""
        try:
            # 总配置数
            total_configs = self.session.query(ConfigItem).count()
            
            # 按分类统计
            category_stats = {}
            categories = self.session.query(ConfigItem.category).distinct().all()
            for (category,) in categories:
                count = self.session.query(ConfigItem).filter_by(category=category).count()
                category_stats[category] = count
            
            # 按类型统计
            type_stats = {}
            types = self.session.query(ConfigItem.value_type).distinct().all()
            for (value_type,) in types:
                count = self.session.query(ConfigItem).filter_by(value_type=value_type).count()
                type_stats[value_type] = count
            
            # 敏感配置统计
            sensitive_count = self.session.query(ConfigItem).filter_by(is_sensitive=True).count()
            
            # 最近更新统计
            recent_updates = self.session.query(ConfigItem).filter(
                ConfigItem.updated_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            ).count()
            
            # 审计日志统计
            total_audit_logs = self.session.query(ConfigAuditLog).count()
            
            return {
                "total_configs": total_configs,
                "category_stats": category_stats,
                "type_stats": type_stats,
                "sensitive_count": sensitive_count,
                "recent_updates": recent_updates,
                "total_audit_logs": total_audit_logs,
                "query_time": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"获取配置统计失败: {e}")
            return {}
    
    def search_configs(self, keyword: str) -> List[Dict]:
        """搜索配置项"""
        try:
            configs = self.session.query(ConfigItem).filter(
                ConfigItem.key.contains(keyword) | 
                ConfigItem.description.contains(keyword) |
                ConfigItem.value.contains(keyword)
            ).order_by(ConfigItem.category, ConfigItem.key).all()
            return [config.to_dict() for config in configs]
        except Exception as e:
            logger.error(f"搜索配置失败: {e}")
            return []
    
    def export_configs(self, filename: str) -> bool:
        """导出配置数据"""
        try:
            export_data = {
                "export_time": datetime.now(timezone.utc).isoformat(),
                "statistics": self.get_config_statistics(),
                "configs": self.get_all_configs(),
                "audit_logs": self.get_audit_logs(limit=1000),  # 导出最近1000条审计日志
                "validation_rules": self.get_validation_rules()
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置数据已导出到: {filename}")
            return True
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return False


def print_configs(configs: List[Dict], show_sensitive: bool = False):
    """打印配置项"""
    if not configs:
        print("📭 没有找到配置项")
        return
    
    print(f"📋 找到 {len(configs)} 个配置项:")
    print("=" * 80)
    
    current_category = None
    for config in configs:
        # 显示分类标题
        if config['category'] != current_category:
            current_category = config['category']
            print(f"\n📁 分类: {current_category}")
            print("-" * 40)
        
        # 显示配置项
        print(f"🔧 {config['key']}")
        print(f"   类型: {config['value_type']}")
        print(f"   描述: {config['description'] or '无'}")
        
        # 显示值（敏感信息需要特殊处理）
        if config['is_sensitive'] and not show_sensitive:
            print(f"   值: {'*' * 8} (敏感信息)")
        else:
            value = config['value']
            if len(str(value)) > 100:
                value = str(value)[:100] + "..."
            print(f"   值: {value}")
        
        print(f"   创建时间: {config['created_at']}")
        print(f"   更新时间: {config['updated_at']}")
        print()


def print_audit_logs(logs: List[Dict]):
    """打印审计日志"""
    if not logs:
        print("📭 没有找到审计日志")
        return
    
    print(f"📋 找到 {len(logs)} 条审计日志:")
    print("=" * 100)
    
    for log in logs:
        print(f"🕐 {log['created_at']}")
        print(f"   操作: {log['operation_type']} - {log['config_key']}")
        print(f"   操作者: {log['operator']} ({log['operator_ip']})")
        
        if log['old_value']:
            old_value = log['old_value']
            if len(old_value) > 50:
                old_value = old_value[:50] + "..."
            print(f"   旧值: {old_value}")
        
        if log['new_value']:
            new_value = log['new_value']
            if len(new_value) > 50:
                new_value = new_value[:50] + "..."
            print(f"   新值: {new_value}")
        
        if log['change_reason']:
            print(f"   原因: {log['change_reason']}")
        
        print()


def print_statistics(stats: Dict[str, Any]):
    """打印统计信息"""
    print("📊 配置中心统计信息:")
    print("=" * 50)
    print(f"总配置数: {stats.get('total_configs', 0)}")
    print(f"敏感配置数: {stats.get('sensitive_count', 0)}")
    print(f"今日更新数: {stats.get('recent_updates', 0)}")
    print(f"审计日志数: {stats.get('total_audit_logs', 0)}")
    
    print("\n📁 按分类统计:")
    for category, count in stats.get('category_stats', {}).items():
        print(f"  {category}: {count}")
    
    print("\n🏷️ 按类型统计:")
    for value_type, count in stats.get('type_stats', {}).items():
        print(f"  {value_type}: {count}")


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='配置中心数据查询脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python scripts/query_config_center.py                    # 查询所有配置
  python scripts/query_config_center.py --category ai_model # 查询AI模型配置
  python scripts/query_config_center.py --sensitive         # 查询敏感配置
  python scripts/query_config_center.py --audit             # 查询审计日志
  python scripts/query_config_center.py --search "api"      # 搜索包含"api"的配置
  python scripts/query_config_center.py --export data.json  # 导出配置数据
  python scripts/query_config_center.py --stats             # 显示统计信息
        """
    )
    
    parser.add_argument(
        '--category', 
        help='指定配置分类'
    )
    
    parser.add_argument(
        '--sensitive', 
        action='store_true',
        help='查询敏感配置'
    )
    
    parser.add_argument(
        '--audit', 
        action='store_true',
        help='查询审计日志'
    )
    
    parser.add_argument(
        '--search', 
        help='搜索关键词'
    )
    
    parser.add_argument(
        '--export', 
        help='导出配置数据到文件'
    )
    
    parser.add_argument(
        '--stats', 
        action='store_true',
        help='显示统计信息'
    )
    
    parser.add_argument(
        '--show-sensitive', 
        action='store_true',
        help='显示敏感配置的值（谨慎使用）'
    )
    
    parser.add_argument(
        '--limit', 
        type=int, 
        default=100,
        help='限制返回结果数量（默认: 100）'
    )
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()
    
    print("🔍 配置中心数据查询工具")
    print("=" * 50)
    
    # 创建Flask应用实例
    app = create_app()
    
    # 在应用上下文中运行
    with app.app_context():
        # 创建查询器
        query = ConfigCenterQuery()
        
        try:
            if args.export:
                # 导出配置数据
                print(f"📤 正在导出配置数据到: {args.export}")
                if query.export_configs(args.export):
                    print("✅ 导出成功")
                else:
                    print("❌ 导出失败")
                    sys.exit(1)
            
            elif args.stats:
                # 显示统计信息
                stats = query.get_config_statistics()
                print_statistics(stats)
            
            elif args.audit:
                # 查询审计日志
                logs = query.get_audit_logs(limit=args.limit)
                print_audit_logs(logs)
            
            elif args.search:
                # 搜索配置
                print(f"🔍 搜索关键词: {args.search}")
                configs = query.search_configs(args.search)
                print_configs(configs, args.show_sensitive)
            
            elif args.sensitive:
                # 查询敏感配置
                print("🔒 敏感配置:")
                configs = query.get_sensitive_configs()
                print_configs(configs, args.show_sensitive)
            
            elif args.category:
                # 查询特定分类
                print(f"📁 分类: {args.category}")
                configs = query.get_configs_by_category(args.category)
                print_configs(configs, args.show_sensitive)
            
            else:
                # 查询所有配置
                print("📋 所有配置:")
                configs = query.get_all_configs()
                print_configs(configs, args.show_sensitive)
                
                # 显示统计信息
                print("\n" + "=" * 50)
                stats = query.get_config_statistics()
                print_statistics(stats)
        
        except Exception as e:
            logger.error(f"查询失败: {e}")
            print(f"❌ 查询失败: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
