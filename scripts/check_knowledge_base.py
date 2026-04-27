#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# 执行所有检查（默认）
python scripts/check_knowledge_base.py --all

# 只检查文件哈希值
python scripts/check_knowledge_base.py --hash

# 只检查哈希值详细状态
python scripts/check_knowledge_base.py --hash-status

# 只检查向量数据库
python scripts/check_knowledge_base.py --vector-db

# 检查最近30天的记录
python scripts/check_knowledge_base.py --all --days 30

# 显示所有哈希值记录（不限数量）
python scripts/check_knowledge_base.py --hash --all-records

# 显示最近50条哈希值记录
python scripts/check_knowledge_base.py --hash --limit 50

# 更新缺失哈希值的文件记录
python scripts/check_knowledge_base.py --update-hashes

# 预览将要更新的记录（不实际更新）
python scripts/check_knowledge_base.py --update-hashes --dry-run

# 更新哈希值后执行所有检查
python scripts/check_knowledge_base.py --update-hashes --all

# 更新缺失哈希值的文件记录
python scripts/check_knowledge_base.py --update-hashes

# 预览将要更新的记录（不实际更新）
python scripts/check_knowledge_base.py --update-hashes --dry-run

# 更新哈希值后执行所有检查
python scripts/check_knowledge_base.py --update-hashes --all

# 只更新哈希值，不执行检查
python scripts/check_knowledge_base.py --update-hashes

知识库完整检查和诊断工具
整合了文件哈希检查、哈希状态统计和向量数据库检查功能
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import ast

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from models.models import RagFileRecord, db
from services.knowledge_service import KnowledgeService
from config.settings import settings
from utils.utils_core.path_helper import get_uploads_path


class KnowledgeBaseChecker:
    """知识库检查器"""
    
    def __init__(self, app):
        self.app = app
        self.knowledge_service = KnowledgeService()
        
    def check_file_hashes(self, limit=20, show_all=False):
        """检查文件哈希值状态"""
        print("\n" + "=" * 80)
        print("文件哈希值检查")
        print("=" * 80)
        
        with self.app.app_context():
            # 查询所有记录
            query = RagFileRecord.query.filter(RagFileRecord.status == 'active')
            all_records = query.all()
            print(f"\n总记录数: {len(all_records)}")
            
            # 统计
            has_hash = 0
            no_hash = 0
            null_hash = 0
            empty_hash = 0
            
            # 显示记录
            sorted_records = sorted(all_records, key=lambda x: x.id, reverse=True)
            if not show_all and limit:
                sorted_records = sorted_records[:limit]
            
            display_count = len(sorted_records)
            total_count = len(all_records)
            status_text = "（显示全部）" if show_all or not limit else f"（显示最近 {display_count} 条，共 {total_count} 条）"
            print(f"\n文件哈希值状态{status_text}:")
            print("-" * 80)
            print(f"{'ID':<6} | {'状态':<12} | {'哈希值':<20} | {'文件名':<40}")
            print("-" * 80)
            
            for record in sorted_records:
                if record.file_hash is None:
                    hash_status = "NULL"
                    hash_display = "None"
                    null_hash += 1
                    no_hash += 1
                elif record.file_hash.strip() == '':
                    hash_status = "空字符串"
                    hash_display = "''"
                    empty_hash += 1
                    no_hash += 1
                else:
                    hash_status = "有效"
                    hash_display = record.file_hash[:16] + "..." if len(record.file_hash) > 16 else record.file_hash
                    has_hash += 1
                
                file_name = record.file_name[:37] + "..." if len(record.file_name) > 40 else record.file_name
                print(f"{record.id:<6} | {hash_status:<12} | {hash_display:<20} | {file_name}")
            
            print("\n" + "=" * 80)
            print("统计汇总:")
            print(f"  有效哈希值: {has_hash}")
            print(f"  无哈希值: {no_hash} (NULL: {null_hash}, 空字符串: {empty_hash})")
            print("=" * 80)
            
            return {
                'total': len(all_records),
                'has_hash': has_hash,
                'no_hash': no_hash,
                'null_hash': null_hash,
                'empty_hash': empty_hash
            }
    
    def check_hash_status(self, days=7):
        """检查文件哈希值详细状态"""
        print("\n" + "=" * 80)
        print("文件哈希值详细状态统计")
        print("=" * 80)
        
        with self.app.app_context():
            # 查询所有记录
            all_records = RagFileRecord.query.all()
            
            # 统计信息
            total_count = len(all_records)
            null_hash_count = sum(1 for r in all_records if r.file_hash is None)
            empty_hash_count = sum(1 for r in all_records if r.file_hash == '')
            valid_hash_count = sum(1 for r in all_records if r.file_hash and r.file_hash.strip())
            
            # 指定天数内的记录
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_records = RagFileRecord.query.filter(
                RagFileRecord.created_time >= cutoff_date
            ).all()
            
            recent_null_count = sum(1 for r in recent_records if r.file_hash is None or r.file_hash == '')
            
            print(f"\n总记录数: {total_count}")
            print(f"  ✓ 有效哈希值: {valid_hash_count} ({valid_hash_count/total_count*100:.1f}%)")
            print(f"  ✗ NULL哈希值: {null_hash_count} ({null_hash_count/total_count*100:.1f}%)")
            print(f"  ✗ 空字符串哈希值: {empty_hash_count} ({empty_hash_count/total_count*100:.1f}%)")
            print(f"\n最近 {days} 天的记录: {len(recent_records)}")
            print(f"  ✗ 无哈希值记录: {recent_null_count}")
            
            # 显示最近无哈希值的记录详情
            if recent_null_count > 0:
                print(f"\n最近 {days} 天无哈希值的文件列表:")
                print("-" * 80)
                for record in recent_records:
                    if not record.file_hash or record.file_hash.strip() == '':
                        print(f"ID: {record.id}")
                        print(f"  文件名: {record.file_name}")
                        print(f"  创建时间: {record.created_time}")
                        print(f"  文件大小: {record.file_size:,} bytes")
                        print(f"  哈希值: {repr(record.file_hash)}")
                        print(f"  状态: {record.status}")
                        print()
            
            # 检查文件是否存在
            upload_folder = Path(settings.UPLOAD_FOLDER)
            missing_files = []
            existing_files = []
            
            for record in recent_records:
                if record.file_path:
                    file_path = upload_folder / record.file_path
                    if not file_path.exists():
                        missing_files.append({
                            'id': record.id,
                            'file_name': record.file_name,
                            'expected_path': str(file_path),
                            'created_time': record.created_time
                        })
                    else:
                        existing_files.append(record.id)
            
            if missing_files:
                print(f"\n⚠️  发现 {len(missing_files)} 个文件路径不存在:")
                print("-" * 80)
                for item in missing_files[:20]:  # 只显示前20个
                    print(f"ID: {item['id']}, 文件: {item['file_name']}")
                    print(f"  路径: {item['expected_path']}")
                    print(f"  创建时间: {item['created_time']}")
                
                if len(missing_files) > 20:
                    print(f"\n  ... 还有 {len(missing_files) - 20} 个缺失文件未显示")
            else:
                print(f"\n✓ 所有文件路径都存在")
            
            print("\n" + "=" * 80)
            
            return {
                'total': total_count,
                'valid_hash': valid_hash_count,
                'null_hash': null_hash_count,
                'empty_hash': empty_hash_count,
                'recent_total': len(recent_records),
                'recent_no_hash': recent_null_count,
                'missing_files': len(missing_files),
                'existing_files': len(existing_files)
            }
    
    def check_vector_db(self, days=7):
        """检查向量数据库中的数据"""
        print("\n" + "=" * 80)
        print("向量数据库数据检查")
        print("=" * 80)
        
        with self.app.app_context():
            vector_db = getattr(self.app, 'vector_db', None)
            
            if not vector_db:
                print("\n❌ 向量数据库未初始化")
                return None
            
            # 查询数据库记录
            all_records = RagFileRecord.query.filter(RagFileRecord.status == 'active').all()
            print(f"\n数据库中的文件记录: {len(all_records)} 个")
            
            # 检查每个记录对应的向量数据
            records_with_vectors = 0
            records_without_vectors = 0
            total_chunks_in_db = 0
            total_chunks_in_vectors = 0
            problematic_records = []
            
            print("\n详细检查:")
            print("-" * 80)
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for record in all_records:
                # 解析文档ID列表
                doc_ids = []
                if record.ids:
                    try:
                        doc_ids = ast.literal_eval(record.ids)
                        if not isinstance(doc_ids, list):
                            doc_ids = []
                    except (ValueError, SyntaxError):
                        doc_ids = []
                
                total_chunks_in_db += len(doc_ids)
                
                # 检查向量数据库中的实际数据
                chunks_found = 0
                if doc_ids and vector_db:
                    try:
                        # 尝试从向量数据库获取数据
                        # 使用 getattr 安全访问 protected 成员（ThreadSafeVectorDB 包装器）
                        actual_db = getattr(vector_db, '_vector_db', vector_db)
                        
                        # 检查是否是 SQLiteVectorStore
                        if hasattr(actual_db, 'get'):
                            # SQLiteVectorStore 路径
                            sample_ids = doc_ids[:5]
                            try:
                                query_results = actual_db.get(ids=sample_ids)
                                if query_results and 'ids' in query_results:
                                    chunks_found = len([doc_id for doc_id in sample_ids if doc_id in query_results['ids']])
                            except (AttributeError, KeyError, TypeError, ValueError):
                                pass
                        elif hasattr(actual_db, '_collection') or hasattr(actual_db, 'collection'):
                            # ChromaDB 路径
                            collection = getattr(actual_db, '_collection', None) or getattr(actual_db, 'collection', None)
                            if collection and hasattr(collection, 'get'):
                                # 只检查前5个ID作为样本
                                sample_ids = doc_ids[:5]
                                try:
                                    # metadatas 是 ChromaDB API 的合法参数名（复数形式）
                                    # noqa: SC200 - metadatas 是 ChromaDB API 的正确参数名
                                    query_results = collection.get(ids=sample_ids, include=['metadatas'])
                                    if query_results and 'ids' in query_results:
                                        chunks_found = len([doc_id for doc_id in sample_ids if doc_id in query_results['ids']])
                                except (AttributeError, KeyError, TypeError, ValueError):
                                    pass
                        
                        # 或者尝试使用 similarity_search 查询
                        if chunks_found == 0 and record.file_path and record.file_name:
                            try:
                                if hasattr(vector_db, 'similarity_search'):
                                    results = vector_db.similarity_search(
                                        query=record.file_name[:50] if record.file_name else "",
                                        k=5
                                    )
                                    if results and record.file_name:
                                        filtered_results = [
                                            doc for doc in results
                                            if hasattr(doc, 'metadata') and doc.metadata
                                            and record.file_name in str(doc.metadata.get('source', ''))
                                        ]
                                        if filtered_results:
                                            chunks_found = len(filtered_results)
                            except (AttributeError, TypeError, ValueError):
                                pass
                    except (AttributeError, TypeError, ValueError):
                        pass
                
                if chunks_found > 0 or len(doc_ids) > 0:
                    records_with_vectors += 1
                    total_chunks_in_vectors += len(doc_ids)
                else:
                    records_without_vectors += 1
                    if record.created_time >= cutoff_date:
                        problematic_records.append({
                            'id': record.id,
                            'file_name': record.file_name,
                            'doc_ids_count': len(doc_ids),
                            'created_time': record.created_time
                        })
                
                # 显示详细信息（只显示最近指定天数的无哈希值或问题记录）
                if record.created_time >= cutoff_date:
                    if not record.file_hash or record.file_hash.strip() == '' or len(doc_ids) == 0:
                        print(f"\n文件ID: {record.id}")
                        print(f"  文件名: {record.file_name}")
                        print(f"  数据库中的chunk数量: {len(doc_ids)}")
                        print(f"  向量数据库中的chunk数量: {chunks_found} (样本检查)")
                        print(f"  文件路径: {record.file_path}")
                        print(f"  哈希值: {repr(record.file_hash)}")
                        print(f"  创建时间: {record.created_time}")
            
            # 尝试获取向量数据库的总文档数
            vector_total = None
            try:
                # 使用 getattr 安全访问 protected 成员（ThreadSafeVectorDB 包装器）
                actual_db = getattr(vector_db, '_vector_db', vector_db)
                
                # 检查是否是 SQLiteVectorStore
                if hasattr(actual_db, 'count'):
                    vector_total = actual_db.count()
                elif hasattr(actual_db, '_collection') or hasattr(actual_db, 'collection'):
                    # ChromaDB 路径
                    collection = getattr(actual_db, '_collection', None) or getattr(actual_db, 'collection', None)
                    if collection and hasattr(collection, 'count'):
                        vector_total = collection.count()
            except (AttributeError, TypeError, ValueError):
                pass
            
            print("\n" + "=" * 80)
            print("统计汇总:")
            print("=" * 80)
            print(f"总文件记录: {len(all_records)}")
            print(f"  ✓ 有向量数据: {records_with_vectors}")
            print(f"  ✗ 无向量数据: {records_without_vectors}")
            print(f"数据库记录的chunk总数: {total_chunks_in_db}")
            if vector_total is not None:
                print(f"向量数据库总文档数: {vector_total}")
                if total_chunks_in_db != vector_total:
                    diff = abs(total_chunks_in_db - vector_total)
                    print(f"  ⚠️  差异: {diff} (数据库: {total_chunks_in_db}, 向量库: {vector_total})")
            
            if problematic_records:
                print(f"\n⚠️  发现 {len(problematic_records)} 个问题记录（最近 {days} 天）:")
                for item in problematic_records[:10]:
                    print(f"  ID {item['id']}: {item['file_name']} (chunks: {item['doc_ids_count']})")
                if len(problematic_records) > 10:
                    print(f"  ... 还有 {len(problematic_records) - 10} 个问题记录")
            
            print("=" * 80)
            
            return {
                'total_records': len(all_records),
                'with_vectors': records_with_vectors,
                'without_vectors': records_without_vectors,
                'total_chunks_db': total_chunks_in_db,
                'total_chunks_vector': vector_total,
                'problematic_records': len(problematic_records)
            }
    
    def check_all(self, hash_limit=20, days=7):
        """执行所有检查"""
        print("=" * 80)
        print("知识库完整检查和诊断")
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # 1. 检查文件哈希值
        hash_check_result = self.check_file_hashes(limit=hash_limit)
        
        # 2. 检查哈希值详细状态
        hash_status_result = self.check_hash_status(days=days)
        
        # 3. 检查向量数据库
        vector_db_result = self.check_vector_db(days=days)
        
        # 总结
        print("\n" + "=" * 80)
        print("检查总结")
        print("=" * 80)
        
        if hash_check_result:
            print(f"文件记录总数: {hash_check_result['total']}")
            total = hash_check_result['total']
            has_hash = hash_check_result['has_hash']
            no_hash = hash_check_result['no_hash']
            print(f"  有效哈希值: {has_hash} ({has_hash/max(total, 1)*100:.1f}%)")
            print(f"  缺失哈希值: {no_hash} ({no_hash/max(total, 1)*100:.1f}%)")
        
        if vector_db_result:
            print(f"\n向量数据库状态:")
            print(f"  有向量数据: {vector_db_result['with_vectors']}")
            print(f"  无向量数据: {vector_db_result['without_vectors']}")
            print(f"  问题记录: {vector_db_result['problematic_records']}")
        
        if hash_status_result and hash_status_result.get('missing_files', 0) > 0:
            print(f"\n⚠️  缺失文件: {hash_status_result['missing_files']} 个")
        
        print("=" * 80)
        
        # 构建返回结果
        results = {
            'hash_check': hash_check_result,
            'hash_status': hash_status_result,
            'vector_db': vector_db_result
        }
        
        return results
    
    def update_missing_hashes(self, dry_run=False):
        """为缺失哈希值的文件记录补充哈希值
        
        Args:
            dry_run: 如果为 True，只显示将要更新的记录，不实际更新
        """
        print("\n" + "=" * 80)
        if dry_run:
            print("预览：为缺失哈希值的文件记录补充哈希值（模拟运行）")
        else:
            print("为缺失哈希值的文件记录补充哈希值")
        print("=" * 80)
        
        with self.app.app_context():
            # 查询所有缺少哈希值的记录
            records_without_hash = RagFileRecord.query.filter(
                RagFileRecord.status == 'active',
                db.or_(
                    RagFileRecord.file_hash == None,  # noqa: E711
                    RagFileRecord.file_hash == ''
                )
            ).all()
            
            print(f"\n找到 {len(records_without_hash)} 条缺少哈希值的记录\n")
            
            if not records_without_hash:
                print("✅ 所有记录都有哈希值，无需更新！")
                return {
                    'total': 0,
                    'updated': 0,
                    'failed': 0,
                    'skipped': 0
                }
            
            uploads_dir = get_uploads_path()
            updated_count = 0
            failed_count = 0
            skipped_count = 0
            
            print(f"{'ID':<6} | {'哈希值':<20} | {'文件名':<50}")
            print("-" * 80)
            
            for record in records_without_hash:
                try:
                    # 构建完整的文件路径
                    if record.file_path:
                        file_path = uploads_dir / record.file_path
                    else:
                        if not dry_run:
                            print(f"⚠️  记录 ID {record.id} 缺少文件路径，跳过")
                        skipped_count += 1
                        failed_count += 1
                        continue
                    
                    # 检查文件是否存在
                    if not file_path.exists():
                        if not dry_run:
                            print(f"⚠️  记录 ID {record.id} 的文件不存在: {file_path}")
                        skipped_count += 1
                        failed_count += 1
                        continue
                    
                    # 计算文件哈希值
                    file_hash = self.knowledge_service.calculate_file_hash(str(file_path))
                    
                    if not file_hash:
                        if not dry_run:
                            print(f"⚠️  记录 ID {record.id} 无法计算哈希值: {record.file_name}")
                        skipped_count += 1
                        failed_count += 1
                        continue
                    
                    # 显示将要更新的记录
                    file_name_display = record.file_name[:47] + "..." if len(record.file_name) > 50 else record.file_name
                    
                    if dry_run:
                        print(f"{record.id:<6} | {file_hash[:16]}... | {file_name_display}")
                    else:
                        # 更新哈希值
                        record.file_hash = file_hash
                        db.session.commit()
                        
                        print(f"{record.id:<6} | {file_hash[:16]}... | {file_name_display}")
                        updated_count += 1
                    
                except Exception as e:
                    if not dry_run:
                        print(f"❌ 更新记录 ID {record.id} 失败: {e}")
                        db.session.rollback()
                    failed_count += 1
            
            print("\n" + "=" * 80)
            if dry_run:
                print("预览完成（未实际更新）:")
            else:
                print("更新完成:")
            print(f"  成功更新: {updated_count}")
            print(f"  失败/跳过: {failed_count + skipped_count}")
            if skipped_count > 0:
                print(f"    - 跳过: {skipped_count}（文件不存在或路径缺失）")
            print("=" * 80)
            
            return {
                'total': len(records_without_hash),
                'updated': updated_count,
                'failed': failed_count,
                'skipped': skipped_count
            }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='知识库完整检查和诊断工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 执行所有检查
  python check_knowledge_base.py --all
  
  # 只检查文件哈希值
  python check_knowledge_base.py --hash
  
  # 检查最近30天的记录
  python check_knowledge_base.py --all --days 30
  
  # 显示所有哈希值记录（不限数量）
  python check_knowledge_base.py --hash --all-records
  
  # 更新缺失哈希值的文件记录
  python check_knowledge_base.py --update-hashes
  
  # 预览将要更新的记录（不实际更新）
  python check_knowledge_base.py --update-hashes --dry-run
  
  # 更新哈希值后执行所有检查
  python check_knowledge_base.py --update-hashes --all
        """
    )
    
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='执行所有检查（默认）'
    )
    parser.add_argument(
        '--hash', '-H',
        action='store_true',
        help='只检查文件哈希值'
    )
    parser.add_argument(
        '--hash-status', '-s',
        action='store_true',
        help='检查哈希值详细状态'
    )
    parser.add_argument(
        '--vector-db', '-v',
        action='store_true',
        help='检查向量数据库'
    )
    parser.add_argument(
        '--days', '-d',
        type=int,
        default=7,
        help='检查最近N天的记录（默认: 7）'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=20,
        help='哈希值检查显示记录数（默认: 20）'
    )
    parser.add_argument(
        '--all-records',
        action='store_true',
        help='显示所有哈希值记录（不限数量）'
    )
    parser.add_argument(
        '--update-hashes', '-u',
        action='store_true',
        help='更新缺失哈希值的文件记录'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览模式：只显示将要更新的记录，不实际更新（需配合 --update-hashes 使用）'
    )
    
    args = parser.parse_args()
    
    # 如果没有指定任何选项，默认执行所有检查（除非是更新哈希值）
    if not (args.hash or args.hash_status or args.vector_db or args.update_hashes):
        args.all = True
    
    app = create_app()
    checker = KnowledgeBaseChecker(app)
    
    try:
        # 更新哈希值功能
        if args.update_hashes:
            checker.update_missing_hashes(dry_run=args.dry_run)
            # 如果同时指定了其他检查，也执行
            if args.all or args.hash or args.hash_status or args.vector_db:
                print("\n" + "=" * 80 + "\n")
        
        # 执行检查功能
        if args.all:
            checker.check_all(hash_limit=args.limit if not args.all_records else None, days=args.days)
        else:
            if args.hash:
                checker.check_file_hashes(
                    limit=args.limit if not args.all_records else None,
                    show_all=args.all_records
                )
            
            if args.hash_status:
                checker.check_hash_status(days=args.days)
            
            if args.vector_db:
                checker.check_vector_db(days=args.days)
    
    except KeyboardInterrupt:
        print("\n\n检查已中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 检查失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

