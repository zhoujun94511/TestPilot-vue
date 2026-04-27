#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
向量数据库管理工具

功能：
1. 初始化和清空向量数据库
2. 检查向量数据库中的文档
3. 检查文件系统中的文件
4. 找出重复的内容（基于文件路径、文件名、哈希值）
5. 提供清理选项

主要功能：

# 初始化向量数据库（清空所有数据，保留数据库结构，类似 init_db.py 的 clear）
python scripts/init_vectordb.py --init-vector-db

# 清空向量数据库（危险操作，会删除所有向量数据）
python scripts/init_vectordb.py --clear-vector-db

# 预览初始化向量数据库（模拟运行）
python scripts/init_vectordb.py --init-vector-db --dry-run

# 预览清空向量数据库（模拟运行）
python scripts/init_vectordb.py --clear-vector-db --dry-run

清理功能：

# 1. 仅预览，不执行实际清理
python scripts/init_vectordb.py --dry-run

# 2. 预览清理向量数据库中的孤立文档
python scripts/init_vectordb.py --dry-run --clean-vector-db

# 3. 预览清理文件系统中的孤立文件
python scripts/init_vectordb.py --dry-run --clean-files

# 4. 实际执行清理（清理数据库重复记录 + 向量数据库孤立文档）
python scripts/init_vectordb.py --clean-vector-db --clean-files

# 5. 实际执行清理（清理数据库重复记录 + 文件系统孤立文件）
python scripts/init_vectordb.py --clean-files

使用方法:
    python scripts/init_vectordb.py [--dry-run] [--clean-vector-db] [--clean-files] [--clear-vector-db] [--init-vector-db]
    
参数:
    --dry-run: 仅预览，不执行实际清理
    --clean-vector-db: 清理向量数据库中的孤立文档
    --clean-files: 清理文件系统中的孤立文件
    --clear-vector-db: 清空向量数据库（危险操作，会删除所有向量数据）
    --init-vector-db: 初始化向量数据库（清空所有数据，保留数据库结构，类似 init_db.py 的 clear）
"""
import sys
import ast
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from models.models import RagFileRecord, db
from utils.utils_core.logger import get_logger
from utils.utils_core.path_helper import get_knowledge_uploads_path
from utils.utils_ai_models.embeddings import create_vector_db, clear_vector_db
from services.knowledge_service import KnowledgeService

logger = get_logger(__name__)


class KnowledgeCleaner:
    """知识库清理器"""
    
    def __init__(self, app):
        self.app = app
        self.knowledge_service = KnowledgeService()
        self.knowledge_dir = get_knowledge_uploads_path()
    
    def analyze_duplicates(self) -> Dict[str, Any]:
        """分析重复内容"""
        print("=" * 80)
        print("知识库重复内容分析")
        print("=" * 80)
        print()
        
        with self.app.app_context():
            # 1. 分析数据库记录
            print("📊 分析数据库记录...")
            db_records = RagFileRecord.query.filter(RagFileRecord.status == 'active').all()
            print(f"   找到 {len(db_records)} 条活跃记录")
            
            # 按哈希值分组
            records_by_hash = defaultdict(list)
            records_by_path = {}
            records_by_name = defaultdict(list)
            
            for record in db_records:
                if record.file_hash:
                    records_by_hash[record.file_hash].append(record)
                if record.file_path:
                    records_by_path[record.file_path] = record
                if record.file_name:
                    records_by_name[record.file_name].append(record)
            
            # 找出重复的哈希值
            duplicate_hashes = {h: records for h, records in records_by_hash.items() if len(records) > 1}
            duplicate_names = {n: records for n, records in records_by_name.items() if len(records) > 1}
            
            print(f"   按哈希值分组: {len(records_by_hash)} 个唯一哈希值")
            print(f"   重复哈希值: {len(duplicate_hashes)} 个")
            print(f"   重复文件名: {len(duplicate_names)} 个")
            print()
            
            # 2. 分析向量数据库
            print("📊 分析向量数据库...")
            vector_db = getattr(self.app, 'vector_db', None)
            if not vector_db:
                vector_db = create_vector_db()
            
            vector_docs_by_source = defaultdict(list)
            total_vector_chunks = 0
            
            try:
                actual_db = getattr(vector_db, '_vector_db', vector_db)
                
                # 检查是否是 SQLiteVectorStore
                if hasattr(actual_db, 'get_all'):
                    # SQLiteVectorStore 路径
                    all_docs = actual_db.get_all(include=['documents', 'metadatas'])
                    if all_docs and 'ids' in all_docs:
                        total_vector_chunks = len(all_docs['ids'])
                        metadatas = all_docs.get('metadatas', [])
                        
                        for metadata in metadatas:
                            if metadata and 'source' in metadata:
                                source = metadata['source']
                                vector_docs_by_source[source].append(metadata)
                        
                        print(f"   向量数据库总文档块数: {total_vector_chunks}")
                        print(f"   唯一文件来源数: {len(vector_docs_by_source)}")
                    else:
                        print("   ⚠️  向量数据库为空")
                else:
                    # ChromaDB 路径：获取集合对象
                    collection = getattr(actual_db, '_collection', None) or getattr(actual_db, 'collection', None)
                    
                    if collection:
                        # noqa: SC200 - metadatas 是 ChromaDB API 的正确参数名（复数形式）
                        all_docs = collection.get(include=['documents', 'metadatas'])  # noqa: SC200
                        if all_docs and 'ids' in all_docs:
                            total_vector_chunks = len(all_docs['ids'])
                            # noqa: SC200 - metadatas 是 ChromaDB API 的正确参数名（复数形式）
                            metadatas = all_docs.get('metadatas', [])  # noqa: SC200
                            
                            for metadata in metadatas:
                                if metadata and 'source' in metadata:
                                    source = metadata['source']
                                    vector_docs_by_source[source].append(metadata)
                            
                            print(f"   向量数据库总文档块数: {total_vector_chunks}")
                            print(f"   唯一文件来源数: {len(vector_docs_by_source)}")
                        else:
                            print("   ⚠️  向量数据库为空")
                    else:
                        print("   ⚠️  无法访问向量数据库集合")
            except Exception as e:
                print(f"   ❌ 分析向量数据库失败: {e}")
                logger.error(f"分析向量数据库失败: {e}", exc_info=True)
            
            print()
            
            # 3. 分析文件系统
            print("📊 分析文件系统...")
            file_system_files = {}
            if self.knowledge_dir.exists():
                for file_path in self.knowledge_dir.rglob('*'):
                    if file_path.is_file():
                        try:
                            file_hash = self.knowledge_service.calculate_file_hash(str(file_path))
                            file_system_files[str(file_path)] = {
                                'path': str(file_path),
                                'name': file_path.name,
                                'hash': file_hash,
                                'size': file_path.stat().st_size
                            }
                        except Exception as e:
                            logger.warning(f"计算文件哈希失败 {file_path}: {e}")
                
                print(f"   文件系统文件数: {len(file_system_files)}")
            else:
                print(f"   ⚠️  知识库目录不存在: {self.knowledge_dir}")
            
            print()
            
            # 4. 找出问题
            print("🔍 查找重复和孤立内容...")
            print("-" * 80)
            
            # 4.1 数据库中的重复记录（相同哈希值）
            db_duplicates = []
            for hash_val, records in duplicate_hashes.items():
                if len(records) > 1:
                    # 保留最新的记录，标记其他的为重复
                    records_sorted = sorted(records, key=lambda r: r.created_time or datetime.min, reverse=True)
                    db_duplicates.append({
                        'hash': hash_val,
                        'keep': records_sorted[0],
                        'duplicates': records_sorted[1:]
                    })
            
            # 4.2 向量数据库中的孤立文档（没有对应的数据库记录）
            orphaned_vector_docs = []
            for source, metadata_list in vector_docs_by_source.items():
                # 检查是否有对应的数据库记录
                has_record = False
                for record in db_records:
                    if record.file_path == source or (record.file_name and source.endswith(record.file_name)):
                        has_record = True
                        break
                
                if not has_record:
                    orphaned_vector_docs.append({
                        'source': source,
                        'chunk_count': len(metadata_list)
                    })
            
            # 4.3 数据库记录对应的文件不存在
            missing_files = []
            knowledge_base_path = self.knowledge_dir
            for record in db_records:
                if record.file_path:
                    # 尝试多种路径格式
                    file_path = Path(record.file_path)
                    # 如果路径是相对路径，尝试拼接知识库根目录
                    if not file_path.is_absolute():
                        # 尝试直接拼接
                        full_path1 = knowledge_base_path / file_path
                        # 尝试去掉开头的"knowledge"前缀（如果存在）
                        path_str = str(file_path)
                        if path_str.startswith('knowledge'):
                            path_str = path_str.replace('knowledge', '', 1).lstrip('\\/')
                            full_path2 = knowledge_base_path / path_str
                        else:
                            full_path2 = knowledge_base_path / file_path
                        
                        # 检查多个可能的路径
                        if not (full_path1.exists() or full_path2.exists()):
                            missing_files.append(record)
                    else:
                        # 绝对路径直接检查
                        if not file_path.exists():
                            missing_files.append(record)
            
            # 4.4 文件系统中的文件没有对应的数据库记录
            orphaned_files = []
            for file_path, file_info in file_system_files.items():
                has_record = False
                file_path_obj = Path(file_path)
                # 尝试相对路径和绝对路径匹配
                relative_path = file_path_obj.relative_to(knowledge_base_path) if knowledge_base_path in file_path_obj.parents else file_path_obj
                
                for record in db_records:
                    # 检查多种匹配方式
                    record_path = Path(record.file_path) if record.file_path else None
                    if record_path:
                        # 标准化路径进行比较
                        record_path_normalized = str(record_path).replace('\\', '/')
                        file_path_normalized = str(file_path).replace('\\', '/')
                        relative_path_normalized = str(relative_path).replace('\\', '/')
                        
                        # 检查是否匹配（绝对路径、相对路径、文件名）
                        if (record_path_normalized == file_path_normalized or
                            record_path_normalized.endswith(relative_path_normalized) or
                            relative_path_normalized.endswith(record_path_normalized) or
                            record_path.name == file_path_obj.name):
                            has_record = True
                            break
                    
                    # 检查哈希值匹配
                    if record.file_hash and record.file_hash == file_info['hash']:
                        has_record = True
                        break
                    
                    # 检查文件名匹配（作为最后手段）
                    if record.file_name and record.file_name == file_info['name']:
                        # 文件名匹配需要更谨慎，因为可能有同名但不同内容的文件
                        # 这里只作为提示，不直接标记为已匹配
                        pass
                
                if not has_record:
                    orphaned_files.append(file_info)
            
            # 输出统计
            print(f"📋 重复内容统计:")
            print(f"   数据库重复记录（相同哈希值）: {len(db_duplicates)} 组")
            print(f"   向量数据库孤立文档: {len(orphaned_vector_docs)} 个文件来源")
            print(f"   数据库记录对应的文件缺失: {len(missing_files)} 个")
            print(f"   文件系统中的孤立文件: {len(orphaned_files)} 个")
            print()
            
            return {
                'db_duplicates': db_duplicates,
                'orphaned_vector_docs': orphaned_vector_docs,
                'missing_files': missing_files,
                'orphaned_files': orphaned_files,
                'total_db_records': len(db_records),
                'total_vector_chunks': total_vector_chunks,
                'total_file_system_files': len(file_system_files)
            }
    
    def clean_duplicates(self, analysis: Dict[str, Any], clean_vector_db: bool = False, clean_files: bool = False, dry_run: bool = False):
        """清理重复内容"""
        print("=" * 80)
        if dry_run:
            print("预览：清理重复内容（模拟运行）")
        else:
            print("清理重复内容")
        print("=" * 80)
        print()
        
        with self.app.app_context():
            cleaned_count = 0
            
            # 1. 清理数据库重复记录
            if analysis['db_duplicates']:
                print(f"🗑️  清理数据库重复记录（{len(analysis['db_duplicates'])} 组）...")
                for dup_info in analysis['db_duplicates']:
                    keep_record = dup_info['keep']
                    duplicates = dup_info['duplicates']
                    
                    print(f"   哈希值: {dup_info['hash'][:16]}...")
                    print(f"   保留: {keep_record.file_name} (ID: {keep_record.id})")
                    
                    for dup_record in duplicates:
                        print(f"   删除: {dup_record.file_name} (ID: {dup_record.id})")
                        
                        if not dry_run:
                            try:
                                # 删除向量数据库中的文档
                                if dup_record.ids:
                                    try:
                                        doc_ids = ast.literal_eval(dup_record.ids)
                                        if doc_ids and clean_vector_db:
                                            vector_db = getattr(self.app, 'vector_db', None)
                                            if vector_db:
                                                vector_db.delete(ids=doc_ids)
                                                print(f"      已删除向量数据: {len(doc_ids)} 个文档块")
                                    except Exception as e:
                                        logger.warning(f"删除向量数据失败: {e}")
                                
                                # 删除数据库记录
                                db.session.delete(dup_record)
                                cleaned_count += 1
                            except Exception as e:
                                logger.error(f"删除记录失败: {e}")
                                db.session.rollback()
                
                if not dry_run:
                    try:
                        db.session.commit()
                        print(f"   ✅ 已清理 {cleaned_count} 条重复记录")
                    except Exception as e:
                        logger.error(f"提交数据库更改失败: {e}")
                        db.session.rollback()
                print()
            
            # 2. 清理向量数据库中的孤立文档
            if clean_vector_db and analysis['orphaned_vector_docs']:
                print(f"🗑️  清理向量数据库孤立文档（{len(analysis['orphaned_vector_docs'])} 个文件来源）...")
                vector_db = getattr(self.app, 'vector_db', None)
                if not vector_db:
                    vector_db = create_vector_db()
                
                total_deleted_chunks = 0
                for orphan_info in analysis['orphaned_vector_docs']:
                    source = orphan_info['source']
                    chunk_count = orphan_info['chunk_count']
                    
                    print(f"   文件来源: {source}")
                    print(f"   文档块数: {chunk_count}")
                    
                    if not dry_run:
                        try:
                            actual_db = getattr(vector_db, '_vector_db', vector_db)
                            
                            # 检查是否是 SQLiteVectorStore
                            if hasattr(actual_db, 'get_all'):
                                # SQLiteVectorStore 路径
                                all_docs = actual_db.get_all(include=['metadatas'])
                                if all_docs and 'ids' in all_docs:
                                    ids_to_delete = []
                                    metadatas = all_docs.get('metadatas', [])
                                    
                                    for i, metadata in enumerate(metadatas):
                                        if metadata and metadata.get('source') == source:
                                            ids_to_delete.append(all_docs['ids'][i])
                                    
                                    if ids_to_delete:
                                        actual_db.delete(ids=ids_to_delete)
                                        total_deleted_chunks += len(ids_to_delete)
                                        print(f"      已删除 {len(ids_to_delete)} 个文档块")
                            else:
                                # ChromaDB 路径：获取集合对象
                                collection = getattr(actual_db, '_collection', None) or getattr(actual_db, 'collection', None)
                                
                                if collection:
                                    # 获取该来源的所有文档ID
                                    # noqa: SC200 - metadatas 是 ChromaDB API 的正确参数名（复数形式）
                                    all_docs = collection.get(include=['metadatas'])  # noqa: SC200
                                    if all_docs and 'ids' in all_docs:
                                        ids_to_delete = []
                                        # noqa: SC200 - metadatas 是 ChromaDB API 的正确参数名（复数形式）
                                        metadatas = all_docs.get('metadatas', [])  # noqa: SC200
                                        
                                        for i, metadata in enumerate(metadatas):
                                            if metadata and metadata.get('source') == source:
                                                ids_to_delete.append(all_docs['ids'][i])
                                        
                                        if ids_to_delete:
                                            collection.delete(ids=ids_to_delete)
                                            total_deleted_chunks += len(ids_to_delete)
                                            print(f"      已删除 {len(ids_to_delete)} 个文档块")
                        except Exception as e:
                            logger.error(f"删除孤立文档失败: {e}")
                
                if not dry_run:
                    print(f"   ✅ 已清理 {total_deleted_chunks} 个孤立文档块")
                print()
            
            # 3. 清理文件系统中的孤立文件
            if clean_files and analysis['orphaned_files']:
                print(f"🗑️  清理文件系统孤立文件（{len(analysis['orphaned_files'])} 个）...")
                deleted_files = 0
                for file_info in analysis['orphaned_files']:
                    file_path = Path(file_info['path'])
                    print(f"   删除: {file_path.name} ({file_info['size'] / 1024 / 1024:.2f} MB)")
                    if not dry_run:
                        print(f"     路径: {file_info['path']}")
                    
                    if not dry_run:
                        try:
                            if file_path.exists():
                                file_path.unlink()
                                deleted_files += 1
                        except Exception as e:
                            logger.error(f"删除文件失败 {file_path}: {e}")
                
                if not dry_run:
                    print(f"   ✅ 已删除 {deleted_files} 个孤立文件")
                print()
            
            # 4. 处理缺失的文件记录
            if analysis['missing_files']:
                print(f"⚠️  发现 {len(analysis['missing_files'])} 个数据库记录对应的文件缺失")
                print("   建议：这些记录可以标记为已删除或手动处理")
                if not dry_run:
                    for record in analysis['missing_files']:
                        print(f"   记录: {record.file_name} (ID: {record.id}), 路径: {record.file_path}")
                        # 可以选择标记为已删除
                        # record.status = 'deleted'
                print()
            
            print("=" * 80)
            if dry_run:
                print("预览完成（未执行实际清理）")
            else:
                print(f"清理完成！共清理 {cleaned_count} 条重复记录")
            print("=" * 80)

    @staticmethod
    def init_vector_database(app, dry_run: bool = False):
        """初始化向量数据库（清空所有数据，保留数据库结构，类似 init_db.py 的 clear 命令）"""
        print("=" * 80)
        if dry_run:
            print("预览：初始化向量数据库（模拟运行）")
        else:
            print("初始化向量数据库（清空所有数据）")
        print("=" * 80)
        print()

        if dry_run:
            print("⚠️  预览模式：将执行以下操作：")
            print("   1. 清空向量数据库中的所有数据（保留数据库结构）")
            print("   2. 向量数据库将变为空，但文件结构保持不变")
            print()
            print("💡 提示：使用不带 --dry-run 参数的命令来实际执行初始化")
            print("=" * 80)
            return

        # 确认操作（因为这是危险操作）
        try:
            confirm = input("⚠️  警告：这将清空所有向量数据（保留数据库结构）！\n确定要继续吗？(y/N，大小写均可): ")
            if confirm.lower() != 'y':
                print("操作已取消")
                return
        except (KeyboardInterrupt, EOFError):
            print("\n操作已取消")
            return

        try:
            # 步骤1: 清空向量数据库中的所有数据
            print("🗑️  步骤1: 清空向量数据库中的所有数据...")
            if clear_vector_db(app):
                print("   ✅ 已清空向量数据库中的所有数据")
            else:
                print("   ⚠️  清空向量数据库时出现问题，但继续执行...")
            print()

            # 步骤2: 确保向量数据库连接正常
            print("🔄 步骤2: 检查向量数据库连接...")
            if app and hasattr(app, 'vector_db') and app.vector_db is not None:
                print("   ✅ 向量数据库连接正常")
            else:
                # 如果应用中没有连接，创建一个新的
                vector_db = create_vector_db()
                if vector_db:
                    print("   ✅ 向量数据库连接已创建")
                    if app:
                        app.vector_db = vector_db
                else:
                    print("   ❌ 向量数据库连接失败")
                    return
            print()

            print()
            print("=" * 80)
            print("✅ 向量数据库初始化完成！")
            print("=" * 80)

        except Exception as e:
            logger.error(f"初始化向量数据库失败: {e}", exc_info=True)
            print(f"   ❌ 初始化向量数据库失败: {e}")
            print("=" * 80)
            print("💡 提示：如果遇到文件被占用错误，请确保：")
            print("   1. 没有其他Flask应用实例正在运行")
            print("   2. 没有其他程序正在访问向量数据库文件")
            print("   3. 尝试关闭所有相关程序后重试")
            print("=" * 80)

    @staticmethod
    def clear_vector_database(app, dry_run: bool = False):
        """清空向量数据库（危险操作）"""
        print("=" * 80)
        if dry_run:
            print("预览：清空向量数据库（模拟运行）")
        else:
            print("清空向量数据库（危险操作）")
        print("=" * 80)
        print()
        
        if dry_run:
            print("⚠️  预览模式：将执行以下操作：")
            print("   1. 关闭现有的向量数据库连接")
            print("   2. 删除整个向量数据库目录")
            print("   3. 所有向量数据将被永久删除")
            print()
            print("💡 提示：使用不带 --dry-run 参数的命令来实际执行清空操作")
            print("=" * 80)
            return
        
        # 再次确认（因为这是危险操作）
        try:
            confirm = input("⚠️  警告：这将永久删除所有向量数据！\n确定要继续吗？(y/N，大小写均可): ")
            if confirm.lower() != 'y':
                print("操作已取消")
                return
        except (KeyboardInterrupt, EOFError):
            print("\n操作已取消")
            return
        
        try:
            print("🔌 关闭现有向量数据库连接...")
            clear_vector_db(app)
            print("   ✅ 已关闭向量数据库连接")
            print()

            print("🗑️  清空向量数据库...")
            clear_vector_db(app)
            print("   ✅ 向量数据库已清空")
            print()
            print("=" * 80)
            print("✅ 向量数据库清空完成！")
            print("=" * 80)
            
        except Exception as e:
            logger.error(f"清空向量数据库失败: {e}", exc_info=True)
            print(f"   ❌ 清空向量数据库失败: {e}")
            print("=" * 80)
            print("💡 提示：如果遇到文件被占用错误，请确保：")
            print("   1. 没有其他Flask应用实例正在运行")
            print("   2. 没有其他程序正在访问向量数据库文件")
            print("   3. 尝试关闭所有相关程序后重试")
            print("=" * 80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='向量数据库管理工具（初始化、清空、清理重复内容）')
    parser.add_argument('--dry-run', action='store_true', help='仅预览，不执行实际清理')
    parser.add_argument('--clean-vector-db', action='store_true', help='清理向量数据库中的孤立文档')
    parser.add_argument('--clean-files', action='store_true', help='清理文件系统中的孤立文件')
    parser.add_argument('--clear-vector-db', action='store_true', help='清空向量数据库（危险操作）')
    parser.add_argument('--init-vector-db', action='store_true', help='初始化向量数据库（重新创建）')

    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        cleaner = KnowledgeCleaner(app)

        # 优先处理初始化和清空操作（这些操作不需要分析）
        if args.clear_vector_db:
            cleaner.clear_vector_database(app, dry_run=args.dry_run)
            return

        if args.init_vector_db:
            cleaner.init_vector_database(app, dry_run=args.dry_run)
            return

        # 分析重复内容
        analysis = cleaner.analyze_duplicates()

        # 如果有重复内容，询问是否清理
        has_duplicates = (len(analysis['db_duplicates']) > 0 or
                         len(analysis['orphaned_vector_docs']) > 0 or
                         len(analysis['orphaned_files']) > 0)

        if has_duplicates:
            print()
            if args.dry_run:
                # 预览模式
                cleaner.clean_duplicates(
                    analysis,
                    clean_vector_db=args.clean_vector_db,
                    clean_files=args.clean_files,
                    dry_run=True
                )
            else:
                # 实际清理
                if args.clean_vector_db or args.clean_files:
                    cleaner.clean_duplicates(
                        analysis,
                        clean_vector_db=args.clean_vector_db,
                        clean_files=args.clean_files,
                        dry_run=False
                    )
                else:
                    print("💡 提示：使用 --clean-vector-db 和 --clean-files 参数来执行实际清理")
                    print("   或使用 --dry-run 参数预览清理操作")
        else:
            print("✅ 未发现重复内容，知识库是干净的！")


if __name__ == '__main__':
    main()

