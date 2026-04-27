#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
清理向量库中的乱码文档并重新处理

使用方法:
    # 1. 仅检查乱码（不执行清理）
    python scripts/clean_garbled_knowledge.py --check-only
    
    # 2. 清理所有乱码文档（删除乱码块）
    python scripts/clean_garbled_knowledge.py --clean
    
    # 3. 清理并重新处理源文件（推荐）
    python scripts/clean_garbled_knowledge.py --clean --reprocess
    
    # 4. 仅删除指定文件的块
    python scripts/clean_garbled_knowledge.py --clean --file "path/to/file.docx"

功能:
    1. 扫描向量库中的所有文档块
    2. 检测包含乱码的文档块
    3. 删除乱码文档块
    4. （可选）重新处理源文件并上传到向量库
    
注意:
    - 此操作不可逆，建议先备份数据库
    - 重新处理需要源文件仍然存在于 uploads/knowledge 目录
"""
import sys
import argparse
from pathlib import Path
from collections import defaultdict
from typing import List, Dict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.utils_core.logger import get_logger
from utils.utils_ai_models.embeddings import create_vector_db
from services.knowledge_service import KnowledgeService

logger = get_logger(__name__)


def detect_garbled_text(text: str, threshold: float = 0.3) -> bool:
    """
    检测文本是否包含乱码
    
    Args:
        text: 需要检测的文本
        threshold: 乱码字符比例阈值（默认30%）
        
    Returns:
        是否包含乱码
    """
    if not text or not isinstance(text, str):
        return False
    
    import re
    
    # 计算有意义字符的比例（字母、数字、中文、常见标点）
    meaningful_chars = sum(1 for c in text if c.isalnum() or '\u4e00' <= c <= '\u9fa5' 
                          or c in '.,!?;:()[]{}""\'\'、，。！？；：（）【】《》')
    
    if len(text) == 0:
        return True  # 空文本认为是无效的
    
    meaningful_ratio = meaningful_chars / len(text)
    
    # 如果有意义字符比例低于阈值，认为是乱码
    if meaningful_ratio < threshold:
        return True
    
    # 检测连续的特殊字符序列（乱码模式）
    garbled_patterns = [
        r'[^\w\s\u4e00-\u9fa5.,!?;:()]{5,}',  # 连续5个以上的特殊字符
        r'[A-Za-z0-9+/=]{30,}',  # 看起来像base64编码
    ]
    
    for pattern in garbled_patterns:
        if re.search(pattern, text):
            return True
    
    return False


def get_garbled_documents(vector_db) -> Dict[str, List[str]]:
    """
    获取包含乱码的文档列表
    
    Returns:
        字典：{文件路径: [乱码块ID列表]}
    """
    print("正在扫描向量库中的乱码文档...")
    
    # 获取向量数据库对象
    actual_db = getattr(vector_db, '_vector_db', vector_db)
    
    # 获取所有文档
    if hasattr(actual_db, 'get_all'):
        # SQLiteVectorStore
        all_docs = actual_db.get_all(include=['documents', 'metadatas'])
    else:
        # ChromaDB
        collection = getattr(actual_db, '_collection', None) or getattr(actual_db, 'collection', None)
        if not collection:
            raise RuntimeError("无法访问向量数据库集合")
        all_docs = collection.get(include=['documents', 'metadatas'])
    
    if not all_docs or 'ids' not in all_docs or len(all_docs['ids']) == 0:
        print("⚠️  向量库为空，没有文档")
        return {}
    
    total_docs = len(all_docs['ids'])
    print(f"找到 {total_docs} 个文档块，开始检测...")
    
    garbled_by_file = defaultdict(list)
    garbled_count = 0
    
    for idx, doc_id in enumerate(all_docs['ids']):
        if idx % 100 == 0 and idx > 0:
            print(f"已检查 {idx}/{total_docs} 个文档块...")
        
        doc_content = all_docs.get('documents', [None])[idx]
        metadata = all_docs.get('metadatas', [{}])[idx] if 'metadatas' in all_docs else {}
        
        if not doc_content:
            continue
        
        file_path = metadata.get('source', '未知文件')
        
        # 检测乱码
        if detect_garbled_text(doc_content):
            garbled_by_file[file_path].append(doc_id)
            garbled_count += 1
    
    print(f"\n✅ 扫描完成:")
    print(f"   总文档块: {total_docs}")
    print(f"   乱码块: {garbled_count} ({garbled_count/total_docs*100:.1f}%)")
    print(f"   受影响文件: {len(garbled_by_file)}")
    print()
    
    return dict(garbled_by_file)


def delete_document_chunks(vector_db, chunk_ids: List[str]) -> bool:
    """
    删除指定的文档块
    
    Args:
        vector_db: 向量数据库实例
        chunk_ids: 要删除的块ID列表
        
    Returns:
        是否成功
    """
    if not chunk_ids:
        return True
    
    try:
        actual_db = getattr(vector_db, '_vector_db', vector_db)
        
        if hasattr(actual_db, 'delete'):
            # SQLiteVectorStore 或 ChromaDB 都支持 delete 方法
            actual_db.delete(ids=chunk_ids)
            return True
        else:
            print(f"❌ 不支持的向量数据库类型")
            return False
    except Exception as e:
        print(f"❌ 删除文档块失败: {e}")
        logger.exception("删除文档块时发生异常")
        return False


def reprocess_file(file_path: str, knowledge_service: KnowledgeService, vector_db) -> bool:
    """
    重新处理单个文件
    
    Args:
        file_path: 文件路径
        knowledge_service: 知识库服务实例
        vector_db: 向量数据库实例
        
    Returns:
        是否成功
    """
    try:
        if not Path(file_path).exists():
            print(f"   ⚠️  源文件不存在: {file_path}")
            return False
        
        print(f"   正在重新处理: {Path(file_path).name}")
        
        result = knowledge_service.process_knowledge_file(
            file_path=file_path,
            vector_db=vector_db
        )
        
        if result['success']:
            print(f"   ✅ 重新处理成功")
            return True
        else:
            print(f"   ❌ 重新处理失败: {result.get('message', '未知错误')}")
            return False
    except Exception as e:
        print(f"   ❌ 重新处理异常: {e}")
        logger.exception(f"重新处理文件 {file_path} 时发生异常")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='清理向量库中的乱码文档')
    parser.add_argument('--check-only', action='store_true', help='仅检查乱码，不执行清理')
    parser.add_argument('--clean', action='store_true', help='清理乱码文档块')
    parser.add_argument('--reprocess', action='store_true', help='重新处理源文件（需要配合--clean使用）')
    parser.add_argument('--file', type=str, help='仅处理指定文件')
    parser.add_argument('--threshold', type=float, default=0.3, help='乱码检测阈值（默认0.3）')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("向量库乱码清理工具")
    print("=" * 80)
    print()
    
    try:
        # 创建向量数据库连接
        print("正在连接向量数据库...")
        vector_db = create_vector_db()
        if not vector_db:
            print("❌ 向量库未启用（ENABLE_VECTOR_STORE=false 或初始化失败），本脚本无法运行")
            return
        print("✅ 成功连接到向量数据库")
        print()
        
        # 获取乱码文档
        garbled_by_file = get_garbled_documents(vector_db)
        
        if not garbled_by_file:
            print("✅ 没有发现乱码文档，向量库是干净的！")
            return
        
        # 如果指定了文件，只处理该文件
        if args.file:
            garbled_by_file = {k: v for k, v in garbled_by_file.items() if args.file in k}
            if not garbled_by_file:
                print(f"⚠️  指定的文件未发现乱码: {args.file}")
                return
        
        # 显示详细信息
        print("=" * 80)
        print("发现以下包含乱码的文件:")
        print("=" * 80)
        print()
        
        for idx, (file_path, chunk_ids) in enumerate(garbled_by_file.items(), 1):
            print(f"{idx}. {Path(file_path).name}")
            print(f"   路径: {file_path}")
            print(f"   乱码块数: {len(chunk_ids)}")
            print()
        
        # 如果只是检查模式，到此结束
        if args.check_only:
            print("=" * 80)
            print("检查完成（--check-only 模式，未执行清理）")
            print("=" * 80)
            return
        
        # 确认清理操作
        if not args.clean:
            print("=" * 80)
            print("⚠️  请使用 --clean 参数来执行清理操作")
            print("   示例: python scripts/clean_garbled_knowledge.py --clean")
            print("=" * 80)
            return
        
        print("=" * 80)
        print("⚠️  警告：即将删除乱码文档块")
        print("=" * 80)
        print()
        
        # 再次确认
        response = input("确认删除以上乱码文档块吗? (yes/no): ")
        if response.lower() != 'yes':
            print("操作已取消")
            return
        
        print()
        print("开始清理...")
        print("-" * 80)
        
        # 清理每个文件的乱码块
        success_count = 0
        fail_count = 0
        
        knowledge_service = KnowledgeService() if args.reprocess else None
        
        for file_path, chunk_ids in garbled_by_file.items():
            print(f"\n处理文件: {Path(file_path).name}")
            print(f"  删除 {len(chunk_ids)} 个乱码块...")
            
            # 删除乱码块
            if delete_document_chunks(vector_db, chunk_ids):
                print(f"  ✅ 删除成功")
                
                # 如果需要重新处理
                if args.reprocess and knowledge_service:
                    if reprocess_file(file_path, knowledge_service, vector_db):
                        success_count += 1
                    else:
                        fail_count += 1
                else:
                    success_count += 1
            else:
                print(f"  ❌ 删除失败")
                fail_count += 1
        
        print()
        print("=" * 80)
        print("清理完成")
        print("=" * 80)
        print()
        print(f"📊 统计:")
        print(f"   成功处理: {success_count} 个文件")
        print(f"   失败: {fail_count} 个文件")
        print()
        
        if args.reprocess:
            print("✅ 已重新处理源文件并更新向量库")
        else:
            print("💡 提示: 使用 --reprocess 参数可自动重新处理源文件")
        
        print()
        
    except Exception as e:
        print(f"❌ 清理过程中发生错误: {e}")
        logger.exception("清理乱码文档时发生异常")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


