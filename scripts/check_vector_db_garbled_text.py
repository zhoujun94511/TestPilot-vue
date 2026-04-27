#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
检查向量库中的乱码文本
用于评估是否有重新处理数据的必要

使用方法:
    python scripts/check_vector_db_garbled_text.py

功能:
    1. 连接向量数据库（ChromaDB）
    2. 获取所有文档块
    3. 检测每个文档块是否包含乱码
    4. 按文件统计乱码情况
    5. 输出详细的检查报告和建议

输出信息:
    - 总体统计：总文档块数、乱码块数、总文件数、包含乱码的文件数
    - 详细报告：列出所有包含乱码的文件及其乱码比例
    - 处理建议：根据乱码比例给出处理建议
"""
import sys
from pathlib import Path
from collections import defaultdict
from typing import Tuple

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.utils_core.logger import get_logger
from utils.utils_core.common_utils import clean_text
from utils.utils_ai_models.embeddings import create_vector_db

logger = get_logger(__name__)


def detect_garbled_text(text: str) -> Tuple[bool, str, int]:
    """
    检测文本是否包含乱码
    
    Args:
        text: 需要检测的文本
        
    Returns:
        Tuple[是否包含乱码, 乱码示例, 乱码字符数]
    """
    if not text or not isinstance(text, str):
        return False, '', 0
    
    original_text = text
    cleaned_text = clean_text(text)
    
    # 如果清理后的文本长度明显减少，说明有乱码
    removed_length = len(original_text) - len(cleaned_text)
    
    # 检测明显的乱码模式
    import re
    garbled_chars = []
    
    # 控制字符（除了换行、制表、回车）
    control_chars = re.findall(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', original_text)
    if control_chars:
        garbled_chars.extend(control_chars)
    
    # 替换字符 (U+FFFD 是Unicode替换字符，用于表示编码错误)
    # noqa: SC100 - FFFD 是Unicode字符代码点名称
    if '\uFFFD' in original_text:  # noqa: SC100
        garbled_chars.append('\uFFFD')  # noqa: SC100
    
    # 零宽字符
    zero_width = re.findall(r'[\u200B-\u200D\uFEFF]', original_text)
    if zero_width:
        garbled_chars.extend(zero_width)
    
    # 私用区字符
    private_use = re.findall(r'[\uE000-\uF8FF]', original_text)
    if private_use:
        garbled_chars.extend(private_use)
    
    # 连续的特殊字符序列（可能是乱码）
    common_punctuation = r'.,!?;:\\-_()\[\]{}"\'\'/=\+\*&%$#@'
    allowed_pattern = rf'[\w\s\u4e00-\u9fa5{re.escape(common_punctuation)}]'
    special_seqs = re.findall(rf'[^{allowed_pattern}]{{5,}}', original_text)
    if special_seqs:
        garbled_chars.extend(special_seqs)
    
    # 非打印字符序列
    non_printable = re.findall(r'[^\x20-\x7E\u4e00-\u9fa5\n\r\t]{3,}', original_text)
    if non_printable:
        garbled_chars.extend(non_printable)
    
    # 提取乱码示例（前100个字符）
    garbled_example = ''
    if garbled_chars:
        garbled_example = ''.join(garbled_chars[:50])[:100]
    
    # 如果清理前后长度差异超过5%，或者有乱码字符，认为包含乱码
    has_garbled = removed_length > len(original_text) * 0.05 or len(garbled_chars) > 0
    
    return has_garbled, garbled_example, removed_length


def check_vector_db_garbled_text():
    """
    检查向量库中的所有文档，找出包含乱码的文件
    """
    print("=" * 80)
    print("向量库乱码检查工具")
    print("=" * 80)
    print()
    
    try:
        # 创建向量数据库连接
        print("正在连接向量数据库...")
        vector_db = create_vector_db()
        if not vector_db:
            print("❌ 向量库未启用（ENABLE_VECTOR_STORE=false 或初始化失败），本脚本无法运行")
            return
        # 获取向量数据库对象
        actual_db = getattr(vector_db, '_vector_db', vector_db)
        
        # 检查是否是 SQLiteVectorStore
        if hasattr(actual_db, 'get_all'):
            # SQLiteVectorStore 路径
            print("✅ 成功连接到向量数据库（SQLite）")
            print()
            
            # 获取所有文档
            print("正在获取所有文档...")
            all_docs = actual_db.get_all(include=['documents', 'metadatas'])
        else:
            # ChromaDB 路径：获取集合对象
            collection = getattr(actual_db, '_collection', None) or getattr(actual_db, 'collection', None)
            
            if not collection:
                print("❌ 错误：无法访问向量数据库集合")
                return
            
            print("✅ 成功连接到向量数据库（ChromaDB）")
            print()
            
            # 获取所有文档
            print("正在获取所有文档...")
            # 获取所有文档（使用get方法，不传参数会返回所有）
            # noqa: SC200 - metadatas 是 ChromaDB API 的正确参数名（复数形式）
            all_docs = collection.get(include=['documents', 'metadatas'])  # noqa: SC200
        
        try:
            if not all_docs or 'ids' not in all_docs:
                print("⚠️  向量库为空，没有文档")
                return

            total_docs = len(all_docs['ids'])
            print(f"✅ 找到 {total_docs} 个文档块")
            print()

            # ===============================
            # ✅ 空向量库：直接结束（合法状态）
            # ===============================
            if total_docs == 0:
                print("=" * 80)
                print("ℹ️ 向量数据库为空（0 文档块）")
                print("   当前为新初始化或尚未入库状态")
                print("   无需进行乱码检查")
                print("=" * 80)
                return



        except Exception as e:
            print(f"❌ 获取文档失败: {e}")
            return
        
        # 统计信息
        file_stats = defaultdict(lambda: {
            'total_chunks': 0,
            'garbled_chunks': 0,
            'garbled_examples': [],
            'file_path': '',
            'file_name': ''
        })
        
        garbled_chunks_count = 0
        garbled_files = set()
        
        print("正在检查文档内容...")
        print("-" * 80)
        
        # 检查每个文档块
        for idx, doc_id in enumerate(all_docs['ids']):
            if idx % 100 == 0 and idx > 0:
                print(f"已检查 {idx}/{total_docs} 个文档块...")
            
            # 获取文档内容
            doc_content = all_docs.get('documents', [None])[idx] if 'documents' in all_docs else None
            # noqa: SC200 - metadatas 是 ChromaDB API 的正确参数名（复数形式）
            metadata = all_docs.get('metadatas', [{}])[idx] if 'metadatas' in all_docs else {}  # noqa: SC200
            
            if not doc_content:
                continue
            
            # 获取文件信息
            file_path = metadata.get('source', '未知文件')
            file_name = metadata.get('file_name', Path(file_path).name if file_path != '未知文件' else '未知文件')
            
            # 检测乱码
            has_garbled, garbled_example, removed_length = detect_garbled_text(doc_content)
            
            # 更新统计
            file_stats[file_path]['total_chunks'] += 1
            file_stats[file_path]['file_path'] = file_path
            file_stats[file_path]['file_name'] = file_name
            
            if has_garbled:
                file_stats[file_path]['garbled_chunks'] += 1
                garbled_chunks_count += 1
                garbled_files.add(file_path)
                
                # 保存乱码示例（最多保存3个）
                if len(file_stats[file_path]['garbled_examples']) < 3:
                    file_stats[file_path]['garbled_examples'].append({
                        'chunk_id': doc_id,
                        'example': garbled_example[:100],
                        'removed_length': removed_length
                    })
        
        print()
        print("=" * 80)
        print("检查结果统计")
        print("=" * 80)
        print()
        
        # 总体统计
        total_files = len(file_stats)
        files_with_garbled = len(garbled_files)
        files_clean = total_files - files_with_garbled
        
        print(f"📊 总体统计:")
        print(f"   总文档块数: {total_docs}")
        print(f"   包含乱码的文档块: {garbled_chunks_count} ({garbled_chunks_count/total_docs*100:.1f}%)")
        print(f"   总文件数: {total_files}")
        print(f"   包含乱码的文件: {files_with_garbled} ({files_with_garbled/total_files*100:.1f}%)")
        print(f"   干净的文件: {files_clean} ({files_clean/total_files*100:.1f}%)")
        print()
        
        # 详细报告：包含乱码的文件
        if files_with_garbled > 0:
            print("=" * 80)
            print("⚠️  包含乱码的文件详情")
            print("=" * 80)
            print()
            
            # 按乱码比例排序
            garbled_file_list = []
            for file_path, stats in file_stats.items():
                if stats['garbled_chunks'] > 0:
                    garbled_ratio = stats['garbled_chunks'] / stats['total_chunks'] * 100
                    garbled_file_list.append((file_path, stats, garbled_ratio))
            
            garbled_file_list.sort(key=lambda x: x[2], reverse=True)
            
            for idx, (file_path, stats, garbled_ratio) in enumerate(garbled_file_list, 1):
                print(f"{idx}. {stats['file_name']}")
                print(f"   文件路径: {stats['file_path']}")
                print(f"   总块数: {stats['total_chunks']}")
                print(f"   乱码块数: {stats['garbled_chunks']} ({garbled_ratio:.1f}%)")
                print(f"   乱码示例:")
                for example_info in stats['garbled_examples']:
                    print(f"     - 块ID: {example_info['chunk_id'][:50]}...")
                    print(f"       示例: {repr(example_info['example'][:50])}")
                    print(f"       移除字符数: {example_info['removed_length']}")
                print()
        else:
            print("✅ 所有文件都是干净的，没有发现乱码！")
            print()
        
        # 建议
        print("=" * 80)
        print("💡 建议")
        print("=" * 80)
        print()
        
        if files_with_garbled == 0:
            print("✅ 向量库中的文件都是干净的，无需重新处理。")
        elif files_with_garbled <= total_files * 0.1:  # 少于10%的文件有乱码
            print(f"⚠️  有 {files_with_garbled} 个文件包含乱码，建议重新上传这些文件。")
            print("   影响较小，可以逐步处理。")
        elif files_with_garbled <= total_files * 0.5:  # 10%-50%的文件有乱码
            print(f"⚠️  有 {files_with_garbled} 个文件包含乱码，强烈建议重新处理这些文件。")
            print("   建议批量重新上传包含乱码的文件。")
        else:  # 超过50%的文件有乱码
            print(f"❌  有 {files_with_garbled} 个文件包含乱码，占比超过50%。")
            print("   强烈建议重新处理所有文件，或考虑重建向量库。")
        
        print()
        print("=" * 80)
        print("检查完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 检查过程中发生错误: {e}")
        logger.exception("检查向量库乱码时发生异常")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_vector_db_garbled_text()

