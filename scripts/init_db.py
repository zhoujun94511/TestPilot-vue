#!/usr/bin/env python3
"""
TestPilot 数据库初始化脚本
用于创建数据库表和初始化数据

RBAC / 认证：本脚本通过 create_app() 间接执行 models.init_database() →
run_auth_migrations()（部门表、users 表、业务表 dept_id 列、引导 super_admin）。
业务表 legacy 结构迁移见 migrate / full-migrate，与 auth_migrations 互补。
详见 docs/AUTH-RBAC.md

# 用法
# 初始化数据库（只创建表，不清空数据；含 RBAC 迁移）
python scripts/init_db.py init
# 清空数据库中的所有数据（保留表结构）
python scripts/init_db.py clear
# 重置数据库（删除所有表并重新创建）
python scripts/init_db.py reset
# 检查数据库状态
python scripts/init_db.py status
# 执行完整迁移（推荐）
python scripts/init_db.py full-migrate
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from models.models import db
from utils.utils_core.logger import get_logger
from sqlalchemy import text

logger = get_logger(__name__)


def migrate_database():
    """迁移数据库，添加新字段"""
    try:
        app = create_app()

        with app.app_context():
            logger.info("开始数据库迁移...")

            # 检查并添加缺失的字段
            # test_cases.module (检查是否已存在)
            try:
                with db.engine.connect() as conn:
                    # 检查字段是否存在
                    result = conn.execute(text("PRAGMA table_info(test_cases)"))
                    columns = [col[1] for col in result.fetchall()]
                    
                    if 'module' not in columns:
                        conn.execute(text("ALTER TABLE test_cases ADD COLUMN module VARCHAR(100)"))
                        conn.commit()
                        logger.info("成功添加 module 字段")
                    else:
                        logger.info("module 字段已存在，跳过")
            except Exception as e:
                logger.error(f"处理 module 字段失败: {e}")

            # test_cases.test_method (检查是否已存在)
            try:
                with db.engine.connect() as conn:
                    result = conn.execute(text("PRAGMA table_info(test_cases)"))
                    columns = [col[1] for col in result.fetchall()]
                    
                    if 'test_method' not in columns:
                        conn.execute(text("ALTER TABLE test_cases ADD COLUMN test_method VARCHAR(100)"))
                        conn.commit()
                        logger.info("成功添加 test_method 字段")
                    else:
                        logger.info("test_method 字段已存在，跳过")
            except Exception as e:
                logger.error(f"处理 test_method 字段失败: {e}")

            # test_cases.display_id (检查是否已存在)
            try:
                with db.engine.connect() as conn:
                    result = conn.execute(text("PRAGMA table_info(test_cases)"))
                    columns = [col[1] for col in result.fetchall()]
                    
                    if 'display_id' not in columns:
                        conn.execute(text("ALTER TABLE test_cases ADD COLUMN display_id VARCHAR(100)"))
                        conn.commit()
                        logger.info("成功添加 display_id 字段")
                    else:
                        logger.info("display_id 字段已存在，跳过")
            except Exception as e:
                logger.error(f"处理 display_id 字段失败: {e}")

            # test_cases.case_id 字段长度优化 (支持新的ID格式)
            try:
                with db.engine.connect() as conn:
                    # 检查当前case_id字段长度
                    result = conn.execute(text("PRAGMA table_info(test_cases)"))
                    columns = result.fetchall()
                    case_id_column = next((col for col in columns if col[1] == 'case_id'), None)
                    
                    if case_id_column and case_id_column[2] == 'VARCHAR(200)':
                        logger.info("case_id 字段长度已足够")
                    else:
                        # 如果长度不够，需要重新创建字段
                        logger.info("case_id 字段长度需要优化，但SQLite不支持直接修改列类型")
                        logger.info("建议使用数据迁移脚本处理现有数据")
            except Exception as e:
                logger.warning(f"检查 case_id 字段长度失败: {e}")

            # chat_history.user_id
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE chat_history ADD COLUMN user_id VARCHAR(100)"))
                    conn.commit()
                    logger.info("成功添加 user_id 字段到 chat_history")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    logger.info("chat_history.user_id 字段已存在")
                else:
                    logger.error(f"添加 chat_history.user_id 字段失败: {e}")

            # chat_history.role
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE chat_history ADD COLUMN role VARCHAR(50)"))
                    conn.commit()
                    logger.info("成功添加 role 字段到 chat_history")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    logger.info("chat_history.role 字段已存在")
                else:
                    logger.error(f"添加 chat_history.role 字段失败: {e}")

            # chat_history.content
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE chat_history ADD COLUMN content TEXT"))
                    conn.commit()
                    logger.info("成功添加 content 字段到 chat_history")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    logger.info("chat_history.content 字段已存在")
                else:
                    logger.error(f"添加 chat_history.content 字段失败: {e}")

            # chat_history.created_time
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE chat_history ADD COLUMN created_time DATETIME"))
                    conn.commit()
                    logger.info("成功添加 created_time 字段到 chat_history")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    logger.info("chat_history.created_time 字段已存在")
                else:
                    logger.error(f"添加 chat_history.created_time 字段失败: {e}")

            # performance_metrics.status_code
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE performance_metrics ADD COLUMN status_code INTEGER"))
                    conn.commit()
                    logger.info("成功添加 status_code 字段到 performance_metrics")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    logger.info("performance_metrics.status_code 字段已存在")
                else:
                    logger.error(f"添加 performance_metrics.status_code 字段失败: {e}")

            # performance_metrics.response_time
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE performance_metrics ADD COLUMN response_time FLOAT"))
                    conn.commit()
                    logger.info("成功添加 response_time 字段到 performance_metrics")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    logger.info("performance_metrics.response_time 字段已存在")
                else:
                    logger.error(f"添加 performance_metrics.response_time 字段失败: {e}")

            # performance_metrics.memory_usage
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE performance_metrics ADD COLUMN memory_usage FLOAT"))
                    conn.commit()
                    logger.info("成功添加 memory_usage 字段到 performance_metrics")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    logger.info("performance_metrics.memory_usage 字段已存在")
                else:
                    logger.error(f"添加 performance_metrics.memory_usage 字段失败: {e}")

            # performance_metrics.cpu_usage
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE performance_metrics ADD COLUMN cpu_usage FLOAT"))
                    conn.commit()
                    logger.info("成功添加 cpu_usage 字段到 performance_metrics")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    logger.info("performance_metrics.cpu_usage 字段已存在")
                else:
                    logger.error(f"添加 performance_metrics.cpu_usage 字段失败: {e}")

            # chat_sessions 表相关字段
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN title VARCHAR(200)"))
                    conn.commit()
                    logger.info("成功添加 title 字段到 chat_sessions")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    logger.info("chat_sessions.title 字段已存在")
                else:
                    logger.error(f"添加 chat_sessions.title 字段失败: {e}")

            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN user_id VARCHAR(100)"))
                    conn.commit()
                    logger.info("成功添加 user_id 字段到 chat_sessions")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    logger.info("chat_sessions.user_id 字段已存在")
                else:
                    logger.error(f"添加 chat_sessions.user_id 字段失败: {e}")

            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN created_time DATETIME"))
                    conn.commit()
                    logger.info("成功添加 created_time 字段到 chat_sessions")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    logger.info("chat_sessions.created_time 字段已存在")
                else:
                    logger.error(f"添加 chat_sessions.created_time 字段失败: {e}")

            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN updated_time DATETIME"))
                    conn.commit()
                    logger.info("成功添加 updated_time 字段到 chat_sessions")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    logger.info("chat_sessions.updated_time 字段已存在")
                else:
                    logger.error(f"添加 chat_sessions.updated_time 字段失败: {e}")

            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE"))
                    conn.commit()
                    logger.info("成功添加 is_deleted 字段到 chat_sessions")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    logger.info("chat_sessions.is_deleted 字段已存在")
                else:
                    logger.error(f"添加 chat_sessions.is_deleted 字段失败: {e}")

            # 确保配置中心相关表存在
            try:
                from models.config_models import ConfigItem, ConfigAuditLog, ConfigValidationRule
                logger.info("配置中心表已确保存在")
            except Exception as e:
                logger.warning(f"配置中心表检查失败: {e}")

            # rag_file_records.file_hash (用于文件去重)
            try:
                with db.engine.connect() as conn:
                    result = conn.execute(text("PRAGMA table_info(rag_file_records)"))
                    columns = [col[1] for col in result.fetchall()]
                    
                    if 'file_hash' not in columns:
                        conn.execute(text("ALTER TABLE rag_file_records ADD COLUMN file_hash VARCHAR(64)"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rag_file_records_file_hash ON rag_file_records(file_hash)"))
                        conn.commit()
                        logger.info("成功添加 file_hash 字段到 rag_file_records")
                    else:
                        logger.info("rag_file_records.file_hash 字段已存在")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    logger.info("rag_file_records.file_hash 字段已存在")
                else:
                    logger.error(f"添加 rag_file_records.file_hash 字段失败: {e}")

            logger.info("数据库迁移完成")

    except Exception as e:
        logger.error(f"数据库迁移失败: {str(e)}")
        sys.exit(1)


def migrate_case_ids():
    """迁移测试用例ID到新格式"""
    try:
        from utils.utils_business_logic.case_id_generator import generate_case_id_from_data, case_id_generator
        from models.models import TestCase
        
        app = create_app()
        
        with app.app_context():
            logger.info("开始迁移测试用例ID...")
            
            # 获取所有现有的测试用例
            existing_cases = TestCase.query.all()
            logger.info(f"找到 {len(existing_cases)} 个现有测试用例")
            
            migrated_count = 0
            skipped_count = 0
            
            for case in existing_cases:
                try:
                    # 检查是否已经是新格式
                    if case_id_generator.is_valid_case_id(case.case_id):
                        logger.debug(f"跳过已经是新格式的ID: {case.case_id}")
                        skipped_count += 1
                        continue
                    
                    # 生成新的ID
                    case_data = {
                        'title': case.title,
                        'category': case.category,
                        'module': case.module
                    }
                    new_case_id = generate_case_id_from_data(case_data)
                    
                    # 检查新ID是否已存在
                    if TestCase.query.filter_by(case_id=new_case_id).first():
                        logger.warning(f"新ID已存在，跳过: {new_case_id}")
                        skipped_count += 1
                        continue
                    
                    # 更新ID
                    old_case_id = case.case_id
                    case.case_id = new_case_id
                    
                    logger.info(f"迁移ID: {old_case_id} -> {new_case_id}")
                    migrated_count += 1
                    
                except Exception as e:
                    logger.error(f"迁移用例 {case.id} 失败: {e}")
                    continue
            
            # 提交更改
            db.session.commit()
            
            logger.info(f"ID迁移完成！")
            logger.info(f"成功迁移: {migrated_count} 个")
            logger.info(f"跳过: {skipped_count} 个")
            
            return True
            
    except Exception as e:
        logger.error(f"ID迁移过程中发生错误: {e}")
        db.session.rollback()
        return False


def backup_database():
    """备份数据库"""
    try:
        import shutil
        from datetime import datetime
        
        app = create_app()
        
        with app.app_context():
            # 获取数据库文件路径
            db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
            if not db_path:
                logger.error("无法获取数据库文件路径")
                return False
            
            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{db_path}.backup_{timestamp}"
            
            # 复制数据库文件
            shutil.copy2(db_path, backup_path)
            logger.info(f"数据库备份完成: {backup_path}")
            
            return backup_path
            
    except Exception as e:
        logger.error(f"数据库备份失败: {e}")
        return None


def optimize_database():
    """优化数据库性能"""
    try:
        app = create_app()
        
        with app.app_context():
            logger.info("开始数据库优化...")
            
            with db.engine.connect() as conn:
                # 创建索引优化查询性能
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_test_cases_case_id ON test_cases(case_id)",
                    "CREATE INDEX IF NOT EXISTS idx_test_cases_category ON test_cases(category)",
                    "CREATE INDEX IF NOT EXISTS idx_test_cases_status ON test_cases(status)",
                    "CREATE INDEX IF NOT EXISTS idx_test_cases_priority ON test_cases(priority)",
                    "CREATE INDEX IF NOT EXISTS idx_test_cases_created_time ON test_cases(created_time)",
                    "CREATE INDEX IF NOT EXISTS idx_chat_history_created_time ON chat_history(created_time)",
                    "CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_time ON chat_sessions(created_time)"
                ]
                
                for index_sql in indexes:
                    try:
                        conn.execute(text(index_sql))
                        logger.info(f"创建索引: {index_sql}")
                    except Exception as e:
                        logger.warning(f"创建索引失败: {e}")
                
                # 分析数据库统计信息
                conn.execute(text("ANALYZE"))
                logger.info("数据库统计信息已更新")
                
                conn.commit()
            
            logger.info("数据库优化完成")
            return True
            
    except Exception as e:
        logger.error(f"数据库优化失败: {e}")
        return False


def show_database_status():
    """显示数据库状态"""
    try:
        from models.models import TestCase, Requirement, ChatHistory, RagFileRecord, SystemLog, PerformanceMetric, ChatSession
        from models.config_models import ConfigItem, ConfigAuditLog, ConfigValidationRule
        from utils.utils_business_logic.case_id_generator import case_id_generator
        
        app = create_app()
        
        with app.app_context():
            print("=" * 60)
            print("数据库状态报告")
            print("=" * 60)
            
            # 基本统计
            test_cases_count = TestCase.query.count()
            requirements_count = Requirement.query.count()
            chat_history_count = ChatHistory.query.count()
            rag_files_count = RagFileRecord.query.count()
            system_logs_count = SystemLog.query.count()
            performance_metrics_count = PerformanceMetric.query.count()
            chat_sessions_count = ChatSession.query.count()
            config_items_count = ConfigItem.query.count()
            config_audit_logs_count = ConfigAuditLog.query.count()
            config_validation_rules_count = ConfigValidationRule.query.count()
            
            print(f"测试用例总数: {test_cases_count}")
            print(f"需求文档总数: {requirements_count}")
            print(f"聊天记录总数: {chat_history_count}")
            print(f"聊天会话总数: {chat_sessions_count}")
            print(f"RAG文件记录总数: {rag_files_count}")
            print(f"系统日志总数: {system_logs_count}")
            print(f"性能指标总数: {performance_metrics_count}")
            print(f"配置项总数: {config_items_count}")
            print(f"配置审计日志总数: {config_audit_logs_count}")
            print(f"配置验证规则总数: {config_validation_rules_count}")
            print()
            
            # 测试用例ID格式分析
            if test_cases_count > 0:
                print("测试用例ID格式分析:")
                test_cases = TestCase.query.all()
                new_format_count = 0
                old_format_count = 0
                
                for case in test_cases:
                    if case_id_generator.is_valid_case_id(case.case_id):
                        new_format_count += 1
                    else:
                        old_format_count += 1
                
                print(f"  新格式ID: {new_format_count} ({new_format_count/test_cases_count*100:.1f}%)")
                print(f"  旧格式ID: {old_format_count} ({old_format_count/test_cases_count*100:.1f}%)")
                print()
                
                # 显示一些示例ID
                print("示例ID:")
                for i, case in enumerate(test_cases[:5]):
                    format_type = "新格式" if case_id_generator.is_valid_case_id(case.case_id) else "旧格式"
                    print(f"  {i+1}. {case.case_id} ({format_type})")
                if test_cases_count > 5:
                    print(f"  ... 还有 {test_cases_count - 5} 个测试用例")
                print()
            
            # 数据库文件信息
            import os
            db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
            if os.path.exists(db_path):
                file_size = os.path.getsize(db_path)
                print(f"数据库文件: {db_path}")
                print(f"文件大小: {file_size / 1024 / 1024:.2f} MB")
            print()
            
            # 向量数据库信息
            print("=" * 60)
            print("向量数据库状态报告")
            print("=" * 60)
            
            try:
                from utils.utils_ai_models.embeddings import create_vector_db
                from config.settings import settings
                
                vector_db = getattr(app, 'vector_db', None)
                if not vector_db:
                    vector_db = create_vector_db()
                
                if vector_db:
                    # 获取底层对象
                    actual_db = getattr(vector_db, '_vector_db', vector_db)
                    
                    # 检查是否是 SQLiteVectorStore
                    if hasattr(actual_db, 'get_all'):
                        # SQLiteVectorStore 路径
                        try:
                            all_data = actual_db.get_all(include=['metadatas'])
                            
                            if all_data and 'ids' in all_data:
                                total_chunks = len(all_data['ids'])
                                print(f"向量文档块总数: {total_chunks}")
                                
                                if total_chunks > 0:
                                    # 统计按来源分组的文档数
                                    metadatas = all_data.get('metadatas', [])
                                    sources = {}
                                    for metadata in metadatas:
                                        if metadata and 'source' in metadata:
                                            source = metadata['source']
                                            sources[source] = sources.get(source, 0) + 1
                                    
                                    print(f"唯一文件来源数: {len(sources)}")
                                    if len(sources) > 0:
                                        print("\n文件来源统计（前10个）:")
                                        sorted_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)
                                        for i, (source, count) in enumerate(sorted_sources[:10], 1):
                                            source_name = source.split('/')[-1] if '/' in source else source
                                            print(f"  {i}. {source_name}: {count} 个文档块")
                                        if len(sources) > 10:
                                            print(f"  ... 还有 {len(sources) - 10} 个文件来源")
                                else:
                                    print("向量数据库为空")
                            else:
                                print("向量数据库为空")
                        except Exception as e:
                            print(f"获取向量数据库信息失败: {e}")
                    else:
                        # ChromaDB 路径：获取集合对象
                        collection = getattr(actual_db, '_collection', None) or getattr(actual_db, 'collection', None)
                        
                        if collection:
                            try:
                                # 获取所有文档
                                # noqa: SC200,SPELLING - metadatas 是 ChromaDB API 的正确参数名（复数形式）
                                all_data = collection.get(include=['metadatas'])  # noqa: SC200,SPELLING
                                
                                if all_data and 'ids' in all_data:
                                    total_chunks = len(all_data['ids'])
                                    print(f"向量文档块总数: {total_chunks}")
                                    
                                    if total_chunks > 0:
                                        # 统计按来源分组的文档数
                                        # noqa: SC200,SPELLING - metadatas 是 ChromaDB API 的正确参数名（复数形式）
                                        metadatas = all_data.get('metadatas', [])  # noqa: SC200,SPELLING
                                        sources = {}
                                        for metadata in metadatas:
                                            if metadata and 'source' in metadata:
                                                source = metadata['source']
                                                sources[source] = sources.get(source, 0) + 1
                                        
                                        print(f"唯一文件来源数: {len(sources)}")
                                        if len(sources) > 0:
                                            print("\n文件来源统计（前10个）:")
                                            sorted_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)
                                            for i, (source, count) in enumerate(sorted_sources[:10], 1):
                                                source_name = source.split('/')[-1] if '/' in source else source
                                                print(f"  {i}. {source_name}: {count} 个文档块")
                                            if len(sources) > 10:
                                                print(f"  ... 还有 {len(sources) - 10} 个文件来源")
                                    else:
                                        print("向量数据库为空")
                                else:
                                    print("向量数据库为空")
                            except Exception as e:
                                print(f"获取向量数据库信息失败: {e}")
                        else:
                            print("⚠️  无法访问向量数据库集合")
                    
                    # 向量数据库文件信息
                    vector_store_dir = settings.VECTOR_STORE_DIR
                    if os.path.exists(vector_store_dir):
                        total_size = 0
                        file_count = 0
                        for root, dirs, files in os.walk(vector_store_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                try:
                                    total_size += os.path.getsize(file_path)
                                    file_count += 1
                                except (OSError, IOError, PermissionError):
                                    # 忽略无法访问的文件
                                    pass
                        
                        print(f"\n向量数据库目录: {vector_store_dir}")
                        print(f"文件数量: {file_count}")
                        print(f"总大小: {total_size / 1024 / 1024:.2f} MB")
                        
                        # 显示主要文件
                        if os.path.exists(vector_store_dir):
                            print("\n主要文件:")
                            for item in os.listdir(vector_store_dir):
                                item_path = os.path.join(vector_store_dir, item)
                                if os.path.isfile(item_path):
                                    size = os.path.getsize(item_path)
                                    print(f"  - {item}: {size / 1024:.2f} KB")
                else:
                    print("⚠️  向量数据库未初始化")
            except Exception as e:
                print(f"获取向量数据库信息失败: {e}")
                logger.error(f"获取向量数据库信息失败: {e}")
            
            print()
            print("=" * 60)
            
    except Exception as e:
        logger.error(f"获取数据库状态失败: {e}")
        print(f"获取数据库状态失败: {e}")


def init_database():
    """初始化数据库"""
    try:
        app = create_app()

        with app.app_context():
            logger.info("开始初始化数据库...")

            # 创建所有表
            db.create_all()

            logger.info("数据库表创建完成")

            # 执行迁移
            migrate_database()

            # 这里可以添加初始数据
            # create_initial_data()

            logger.info("数据库初始化完成")

    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        sys.exit(1)


def create_initial_data():
    """创建初始数据"""
    try:
        # 这里可以添加创建初始数据的逻辑
        pass

    except Exception as e:
        logger.error(f"创建初始数据失败: {str(e)}")
        raise


def clear_database():
    """清空数据库中的所有数据（保留表结构）"""
    try:
        from models.models import (
            TestCase, Requirement, ChatHistory, RagFileRecord, SystemLog, PerformanceMetric,
            ChatSession, ToolExecutionLog, LlmUsageLog,
        )
        from models.config_models import ConfigItem, ConfigAuditLog, ConfigValidationRule
        from models.auth_models import AuthAuditLog, Department, User, UserSession

        app = create_app()

        with app.app_context():
            logger.warning("开始清空数据库数据...")

            # 按外键依赖顺序：子表先于父表；users 在 departments 之前
            deleted_counts = {
                'chat_history': ChatHistory.query.delete(),
                'chat_sessions': ChatSession.query.delete(),
                'tool_execution_logs': ToolExecutionLog.query.delete(),
                'llm_usage_logs': LlmUsageLog.query.delete(),
                'performance_metrics': PerformanceMetric.query.delete(),
                'system_logs': SystemLog.query.delete(),
                'test_cases': TestCase.query.delete(),
                'requirements': Requirement.query.delete(),
                'rag_file_records': RagFileRecord.query.delete(),
                'config_audit_logs': ConfigAuditLog.query.delete(),
                'config_validation_rules': ConfigValidationRule.query.delete(),
                'config_items': ConfigItem.query.delete(),
                # 下次启动 run_auth_migrations() 会重建默认部门和引导超管
                'user_sessions': UserSession.query.delete(),
                'auth_audit_logs': AuthAuditLog.query.delete(),
                'users': User.query.delete(),
                'departments': Department.query.delete(),
            }
            
            # 提交更改
            db.session.commit()

            # 删除记录不会缩小 SQLite 文件；VACUUM 不能在事务内执行
            with db.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(text("VACUUM"))

            logger.info("已清空所有数据库表的数据")
            logger.info(f"清空统计: {deleted_counts}")
            
            print("=" * 60)
            print("数据库数据清空完成")
            print("=" * 60)
            for table, count in deleted_counts.items():
                print(f"  {table}: {count} 条记录")
            print("=" * 60)

    except Exception as e:
        logger.error(f"清空数据库失败: {str(e)}")
        db.session.rollback()
        sys.exit(1)


def reset_database():
    """重置数据库（危险操作）"""
    try:
        app = create_app()

        with app.app_context():
            logger.warning("开始重置数据库...")

            # 删除所有表
            db.drop_all()
            logger.info("已删除所有数据库表")

            # 重新创建表
            db.create_all()
            logger.info("已重新创建数据库表")

            # 创建初始数据
            create_initial_data()

            logger.info("数据库重置完成")

    except Exception as e:
        logger.error(f"数据库重置失败: {str(e)}")
        sys.exit(1)


def main():
    """主函数"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "reset":
            confirm = input("确定要重置数据库吗？这将删除所有数据！(y/N，大小写均可): ")
            if confirm.lower() == 'y':
                reset_database()
            else:
                print("操作已取消")
        elif command == "clear":
            confirm = input("确定要清空数据库中的所有数据吗？这将删除所有记录但保留表结构！(y/N，大小写均可): ")
            if confirm.lower() == 'y':
                clear_database()
            else:
                print("操作已取消")
        elif command == "init":
            init_database()
        elif command == "migrate":
            migrate_database()
        elif command == "migrate-ids":
            # 备份数据库
            backup_path = backup_database()
            if backup_path:
                print(f"数据库已备份到: {backup_path}")
                # 执行ID迁移
                if migrate_case_ids():
                    print("测试用例ID迁移完成！")
                else:
                    print("测试用例ID迁移失败！")
            else:
                print("数据库备份失败，取消ID迁移操作")
        elif command == "backup":
            backup_path = backup_database()
            if backup_path:
                print(f"数据库备份完成: {backup_path}")
            else:
                print("数据库备份失败")
        elif command == "optimize":
            if optimize_database():
                print("数据库优化完成！")
            else:
                print("数据库优化失败！")
        elif command == "full-migrate":
            # 完整迁移流程
            print("开始完整数据库迁移流程...")
            
            # 1. 备份数据库
            backup_path = backup_database()
            if not backup_path:
                print("数据库备份失败，取消迁移操作")
                return
            print(f"数据库已备份到: {backup_path}")
            
            # 2. 执行数据库迁移
            migrate_database()
            
            # 3. 迁移测试用例ID
            if migrate_case_ids():
                print("测试用例ID迁移完成！")
            else:
                print("测试用例ID迁移失败！")
            
            # 4. 优化数据库
            if optimize_database():
                print("数据库优化完成！")
            else:
                print("数据库优化失败！")
            
            print("完整迁移流程完成！")
        elif command == "status":
            show_database_status()
        else:
            print("可用命令:")
            print("  init         - 初始化数据库（只创建表，不清空数据）")
            print("  clear        - 清空数据库中的所有数据（保留表结构）")
            print("  migrate      - 迁移数据库结构")
            print("  migrate-ids  - 迁移测试用例ID到新格式")
            print("  backup       - 备份数据库")
            print("  optimize     - 优化数据库性能")
            print("  status       - 显示数据库状态")
            print("  full-migrate - 完整迁移流程（备份+结构迁移+ID迁移+优化）")
            print("  reset        - 重置数据库（删除所有表并重新创建，危险操作）")
    else:
        init_database()


if __name__ == "__main__":
    main()