#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清空并重建知识库脚本

功能：
1. 完全删除ChromaDB向量数据库
2. 重新创建干净的向量数据库
3. 重建所有知识库文件

使用方法：
    python scripts/clear_and_rebuild_knowledge.py
"""

import sys
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from services.knowledge_service import KnowledgeService
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


def main():
    """主函数"""
    try:
        logger.info("=" * 60)
        logger.info("开始清空并重建知识库")
        logger.info("=" * 60)
        
        # 创建Flask应用
        app = create_app()
        
        with app.app_context():
            # 步骤1: 删除向量数据库目录
            vector_store_path = Path(app.config.get('CHROMADB_PERSIST_DIRECTORY', 'vector_store'))
            
            if vector_store_path.exists():
                logger.info(f"步骤1: 删除向量数据库目录: {vector_store_path}")
                try:
                    # 删除所有子目录和文件
                    for item in vector_store_path.iterdir():
                        if item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                            logger.info(f"  已删除目录: {item.name}")
                        else:
                            item.unlink()
                            logger.info(f"  已删除文件: {item.name}")
                    logger.info("✅ 向量数据库已完全清空")
                except Exception as e:
                    logger.error(f"❌ 删除向量数据库失败: {e}")
                    return False
            else:
                logger.info(f"向量数据库目录不存在: {vector_store_path}")
            
            # 步骤2: 重新创建向量数据库
            logger.info("\n步骤2: 重新创建向量数据库...")
            try:
                from utils.utils_ai_models.embeddings import create_vector_db
                vector_db = create_vector_db()
                app.vector_db = vector_db
                logger.info("✅ 向量数据库已重新创建")
            except Exception as e:
                logger.error(f"❌ 创建向量数据库失败: {e}")
                return False
            
            # 步骤3: 重建知识库
            logger.info("\n步骤3: 重建所有知识库文件...")
            knowledge_service = KnowledgeService()
            result = knowledge_service.rebuild_knowledge_base(
                vector_db=vector_db,
                clear_all=True
            )
            
            if result['success']:
                info = result.get('info', {})
                logger.info("=" * 60)
                logger.info("✅ 知识库重建完成！")
                logger.info(f"  总文件数: {info.get('total_files', 0)}")
                logger.info(f"  成功处理: {info.get('processed', 0)}")
                logger.info(f"  失败: {info.get('failed', 0)}")
                logger.info(f"  耗时: {info.get('rebuild_time', 0):.2f}秒")
                
                if info.get('failed_files'):
                    logger.warning("\n失败的文件:")
                    for failed in info['failed_files']:
                        logger.warning(f"  - {failed['name']}: {failed['reason']}")
                
                logger.info("=" * 60)
                return True
            else:
                logger.error(f"❌ 重建失败: {result.get('message')}")
                return False
                
    except Exception as e:
        logger.error(f"❌ 脚本执行失败: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)




