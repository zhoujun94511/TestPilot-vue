#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
快速检查向量数据库中的实际数据
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.utils_ai_models.embeddings import create_vector_db
import sqlite3
from config.settings import settings

def check_vector_count():
    """检查向量数据库中的实际数据"""
    print("=" * 60)
    print("向量数据库数据检查")
    print("=" * 60)
    
    # 方法1: 使用 count() 方法
    print("\n1. 使用 count() 方法:")
    try:
        vector_db = create_vector_db()
        if vector_db:
            count = vector_db.count()
            print(f"   count() 返回: {count}")
        else:
            print("   ❌ 无法创建向量数据库连接")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    # 方法2: 直接查询数据库
    print("\n2. 直接查询数据库:")
    try:
        db_path = Path(settings.VECTOR_STORE_DIR) / "vector_store.db"
        if not db_path.exists():
            print(f"   ❌ 数据库文件不存在: {db_path}")
            return
        
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        
        # 检查各个表的记录数
        chunks_count = conn.execute("SELECT COUNT(*) as cnt FROM chunks").fetchone()['cnt']
        embeddings_count = conn.execute("SELECT COUNT(*) as cnt FROM chunk_embeddings").fetchone()['cnt']
        documents_count = conn.execute("SELECT COUNT(*) as cnt FROM documents").fetchone()['cnt']
        
        print(f"   chunks 表: {chunks_count} 条记录")
        print(f"   chunk_embeddings 表: {embeddings_count} 条记录")
        print(f"   documents 表: {documents_count} 条记录")
        
        # 检查是否有不匹配的情况
        if chunks_count > 0 and embeddings_count == 0:
            print(f"\n   ⚠️  警告: chunks 表有 {chunks_count} 条记录，但 chunk_embeddings 表为空！")
            print(f"   这意味着文档已添加，但向量数据未写入。")
        
        conn.close()
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_vector_count()








