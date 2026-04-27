#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量导入知识库文档到向量数据库脚本（增强版）
整合了文件哈希去重、文件夹结构保留、进度显示等功能

用法示例:
  # 一键导入所有文档
  python scripts/batch_import_knowledge.py

  # 强制更新已存在的文件
  python scripts/batch_import_knowledge.py --force

  # 仅导入包含特定关键词的文件
  python scripts/batch_import_knowledge.py --pattern "测试"

  # 仅列出文件，不执行导入
  python scripts/batch_import_knowledge.py --list

  # 预览模式：只显示将要导入的文件，不实际导入
  python scripts/batch_import_knowledge.py --dry-run

  # 导入后自动更新缺失的哈希值
  python scripts/batch_import_knowledge.py --update-hashes

  # 导入后执行完整检查
  python scripts/batch_import_knowledge.py --check

  # 组合使用：强制更新并检查
  python scripts/batch_import_knowledge.py --force --check
"""
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from models.models import db, RagFileRecord
from services.knowledge_service import KnowledgeService
from utils.utils_core.logger import get_logger
from utils.utils_core.path_helper import get_knowledge_uploads_path, get_uploads_path

logger = get_logger(__name__)

# 支持的文件格式
SUPPORTED_EXTENSIONS = {'.txt', '.md', '.docx', '.pdf', '.csv'}


class BatchKnowledgeImporter:
    """批量导入知识库文档的增强类"""
    
    def __init__(self, app):
        self.app = app
        self.knowledge_service = KnowledgeService()
        self.knowledge_dir = get_knowledge_uploads_path()
        self.uploads_dir = get_uploads_path()
        
        # 文件夹名称到分类的映射（根据知识库目录结构）
        self.category_mapping = {
            '测试用例': 'test_cases',
            'test_cases': 'test_cases',
            '需求文档': 'requirements',
            'requirements': 'requirements',
            '业务规则': 'business_rules',
            'business_rules': 'business_rules',
            '最佳实践': 'best_practices',
            'best_practices': 'best_practices',
            '模板文档': 'templates',
            'templates': 'templates',
            '其他': 'other',
            'other': 'other'
        }
    
    def infer_category_from_path(self, file_path: Path) -> str:
        """根据文件路径推断分类
        
        Args:
            file_path: 文件路径
            
        Returns:
            分类名称，默认为 'other'
        """
        # 获取相对于知识库根目录的路径
        try:
            relative_path = file_path.relative_to(self.knowledge_dir)
            # 获取路径的各个部分
            path_parts = relative_path.parts
            
            # 遍历路径部分，查找匹配的分类
            for part in path_parts:
                # 检查是否在映射中
                if part in self.category_mapping:
                    return self.category_mapping[part]
                # 检查是否包含关键词（部分匹配）
                for key, category in self.category_mapping.items():
                    if key in part or part in key:
                        return category
            
            # 根据路径中的关键词推断（模糊匹配）
            path_str = str(relative_path).lower()
            # 检查各种可能的路径模式
            if any(keyword in path_str for keyword in ['测试用例', 'test_case', 'testcase']):
                return 'test_cases'
            elif any(keyword in path_str for keyword in ['需求', 'requirement']):
                return 'requirements'
            elif any(keyword in path_str for keyword in ['业务规则', 'business_rule', 'businessrule']):
                return 'business_rules'
            elif any(keyword in path_str for keyword in ['最佳实践', 'best_practice', 'bestpractice']):
                return 'best_practices'
            elif any(keyword in path_str for keyword in ['模板', 'template']):
                return 'templates'
            # 根据实际目录结构推断（基于常见目录名）
            elif any(keyword in path_str for keyword in ['ai测试', 'ai_test', '测试知识', '测试知识库']):
                return 'test_cases'  # AI测试相关归类为测试用例
            elif any(keyword in path_str for keyword in ['安全测试', 'security', '性能测试', 'performance', '游戏测试', 'game']):
                return 'test_cases'  # 各种测试相关归类为测试用例
            elif any(keyword in path_str for keyword in ['自动化测试', 'automation', '移动端测试', 'mobile']):
                return 'test_cases'  # 自动化测试相关归类为测试用例
        except ValueError:
            # 如果文件不在知识库目录内，无法获取相对路径
            pass
        
        # 默认返回 'other'
        return 'other'
    
    def get_knowledge_files(self, pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取知识库目录下的所有支持的文件（递归扫描子文件夹，自动去重）
        
        Returns:
            文件信息列表，每个元素包含：
            - path: 文件完整路径
            - name: 文件名
            - relative_path: 相对于 knowledge 目录的相对路径
            - size: 文件大小
        """
        if not self.knowledge_dir.exists():
            logger.warning(f"知识库目录不存在: {self.knowledge_dir}")
            return []
        
        files = []
        seen_hashes = {}  # 用于去重：{hash: file_info}
        seen_paths = set()  # 用于去重：文件完整路径
        
        # 使用 rglob 递归扫描所有子目录
        for file_path in self.knowledge_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                # 检查文件路径是否已存在（防止重复扫描）
                file_path_str = str(file_path)
                if file_path_str in seen_paths:
                    logger.debug(f"跳过重复路径: {file_path_str}")
                    continue
                seen_paths.add(file_path_str)
                
                # 计算相对于 knowledge 目录的相对路径
                try:
                    relative_path = file_path.relative_to(self.knowledge_dir)
                except ValueError:
                    # 如果无法计算相对路径，使用文件名
                    relative_path = Path(file_path.name)
                
                # 计算文件哈希值用于去重
                try:
                    file_hash = self.knowledge_service.calculate_file_hash(str(file_path))
                except Exception as e:
                    logger.warning(f"计算文件哈希失败 {file_path}: {e}")
                    file_hash = None
                
                file_info = {
                    'path': file_path,
                    'name': file_path.name,
                    'relative_path': relative_path,
                    'size': file_path.stat().st_size,
                    'size_mb': file_path.stat().st_size / (1024 * 1024),
                    'hash': file_hash
                }
                
                # 基于哈希值去重（相同内容的文件只保留一个）
                if file_hash:
                    if file_hash in seen_hashes:
                        existing_file = seen_hashes[file_hash]
                        logger.debug(f"发现重复文件（相同哈希值）: {file_path.name} (已存在: {existing_file['name']})")
                        # 保留路径较短的（通常是更合理的路径）
                        if len(str(file_info['relative_path'])) < len(str(existing_file['relative_path'])):
                            files.remove(existing_file)
                            files.append(file_info)
                            seen_hashes[file_hash] = file_info
                        continue
                    seen_hashes[file_hash] = file_info
                
                # 文件过滤
                if pattern:
                    if pattern.lower() in file_path.name.lower():
                        files.append(file_info)
                else:
                    files.append(file_info)
        
        return files
    
    @staticmethod
    def check_existing_files_by_hash() -> Dict[str, RagFileRecord]:
        """检查已存在的文件记录（基于哈希值）"""
        existing_files = {}
        records = RagFileRecord.query.filter(RagFileRecord.status == 'active').all()
        
        for record in records:
            if record.file_hash and record.file_hash.strip():
                existing_files[record.file_hash] = record
        
        return existing_files
    
    def import_single_file(
        self,
        file_info: Dict[str, Any],
        vector_db,
        existing_files_by_hash: Dict[str, RagFileRecord],
        existing_files_by_name: Dict[str, RagFileRecord],
        existing_files_by_path: Dict[str, RagFileRecord],
        force_update: bool = False,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """导入单个文件到向量数据库（使用增强的去重逻辑）
        
        Args:
            file_info: 文件信息字典
            vector_db: 向量数据库实例
            existing_files_by_hash: 基于哈希值的已存在文件记录
            existing_files_by_name: 基于文件名的已存在文件记录（向后兼容）
            existing_files_by_path: 基于文件路径的已存在文件记录
            force_update: 是否强制更新
            dry_run: 预览模式
            
        Returns:
            导入结果字典
        """
        file_path = file_info['path']
        filename = file_info['name']
        file_path_str = str(file_path)
        
        try:
            # 使用文件信息中已计算的哈希值（如果存在），否则重新计算
            file_hash = file_info.get('hash') or self.knowledge_service.calculate_file_hash(str(file_path))
            
            # 如果强制更新，先删除旧记录（基于哈希值）
            if force_update and file_hash and file_hash in existing_files_by_hash:
                existing_record = existing_files_by_hash[file_hash]
                from models.models import db  # 在函数开始处导入，确保在except中可用
                try:
                    # 删除向量库中的旧文档
                    if existing_record.ids:
                        import ast
                        doc_ids = ast.literal_eval(existing_record.ids)
                        if doc_ids and vector_db:
                            try:
                                vector_db.delete(ids=doc_ids)
                                logger.info(f"已删除旧文档的向量数据: {len(doc_ids)} 个文档块")
                            except Exception as e:
                                logger.warning(f"删除向量数据失败: {e}")
                    
                    # 删除数据库记录
                    db.session.delete(existing_record)
                    db.session.commit()
                    logger.info(f"已删除旧记录: {filename} (ID: {existing_record.id})")
                    
                    # 更新去重字典，移除已删除的记录
                    existing_files_by_hash.pop(file_hash, None)
                    if existing_record.file_path:
                        existing_files_by_path.pop(existing_record.file_path, None)
                        filename_from_record = Path(existing_record.file_path).name
                        existing_files_by_name.pop(filename_from_record, None)
                except Exception as e:
                    logger.warning(f"删除旧记录失败: {e}")
                    try:
                        db.session.rollback()
                    except (AttributeError, RuntimeError, ValueError) as rollback_error:
                        # 如果rollback也失败，记录警告但继续执行
                        logger.warning(f"数据库回滚失败: {rollback_error}")
                    except Exception as rollback_error:
                        # 其他未知异常，记录但不中断流程
                        logger.error(f"数据库回滚时发生未知错误: {rollback_error}")
            
            # 检查是否已存在（基于哈希值）
            if file_hash and file_hash in existing_files_by_hash and not force_update:
                existing_record = existing_files_by_hash[file_hash]
                return {
                    'success': True,
                    'message': f'文件已存在（相同哈希值）: {filename} (ID: {existing_record.id})',
                    'skipped': True,
                    'is_duplicate': True,
                    'existing_id': existing_record.id,
                    'file_hash': file_hash
                }
            
            # 检查文件路径是否已存在
            if file_path_str in existing_files_by_path and not force_update:
                existing_record = existing_files_by_path[file_path_str]
                return {
                    'success': True,
                    'message': f'文件已存在（相同路径）: {filename} (ID: {existing_record.id})',
                    'skipped': True,
                    'is_duplicate': True,
                    'existing_id': existing_record.id
                }
            
            # 向后兼容：检查文件名是否已存在（如果哈希值匹配失败）
            if filename in existing_files_by_name and not force_update and not file_hash:
                return {
                    'success': False,
                    'message': f'文件已存在（相同文件名）: {filename}',
                    'skipped': True,
                    'is_duplicate': True
                }
            
            if dry_run:
                return {
                    'success': True,
                    'message': f'将导入: {filename}',
                    'dry_run': True,
                    'file_hash': file_hash,
                    'file_size': file_info['size']
                }
            
            # 根据文件路径自动推断分类
            inferred_category = self.infer_category_from_path(file_path)
            
            # 使用增强的上传方法（包含哈希去重和自动乱码清理）
            # 注意：文件处理时会自动清理PDF等文件解析产生的乱码字符
            result = self.knowledge_service.upload_knowledge_file_with_deduplication(
                file_path=str(file_path),
                original_filename=filename,
                description=f'批量导入 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                category=inferred_category,  # 使用推断的分类
                upload_folder=self.uploads_dir,
                vector_db=vector_db
            )
            
            if result['success']:
                file_info_result = result.get('file_info', {})
                return {
                    'success': True,
                    'message': result['message'],
                    'document_ids': file_info_result.get('document_ids', []),
                    'file_id': file_info_result.get('id'),
                    'is_duplicate': file_info_result.get('is_duplicate', False),
                    'file_hash': file_hash
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', '导入失败'),
                    'error': result.get('error', 'unknown_error')
                }
        
        except Exception as e:
            logger.error(f"导入文件失败 {filename}: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'导入失败: {filename} - {str(e)}',
                'error': str(e)
            }
    
    def batch_import(
        self,
        force_update: bool = False,
        file_pattern: Optional[str] = None,
        dry_run: bool = False,
        update_hashes: bool = False,
        check_after: bool = False
    ) -> Dict[str, Any]:
        """批量导入知识库文档
        
        Args:
            force_update: 是否强制更新已存在的文件
            file_pattern: 文件名称过滤模式
            dry_run: 预览模式，不实际导入
            update_hashes: 导入后自动更新缺失的哈希值
            check_after: 导入后执行完整检查
            
        Returns:
            导入结果统计
        """
        print("=" * 80)
        if dry_run:
            print("预览：批量导入知识库文档到向量数据库（模拟运行）")
        else:
            print("批量导入知识库文档到向量数据库")
        print("=" * 80)
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"强制更新: {'是' if force_update else '否'}")
        print(f"预览模式: {'是' if dry_run else '否'}")
        if file_pattern:
            print(f"文件过滤: {file_pattern}")
        print(f"📁 文件读取目录: {self.knowledge_dir}")
        print()
        if not dry_run:
            print("ℹ️  提示：导入的文件会自动清理乱码字符（PDF等文件解析时产生的无效字符）")
            print()
        
        with self.app.app_context():
            # 获取向量数据库
            vector_db = getattr(self.app, 'vector_db', None)
            if not vector_db:
                from utils.utils_ai_models.embeddings import create_vector_db
                print("正在初始化向量数据库...")
                vector_db = create_vector_db()
                if not vector_db:
                    print("❌ 向量数据库初始化失败")
                    return {'success': False, 'error': 'vector_db_not_initialized'}
                self.app.vector_db = vector_db
                print("✅ 向量数据库初始化成功")
                print()
            
            # 获取所有文件
            all_files = self.get_knowledge_files(pattern=file_pattern)
            if not all_files:
                print("❌ 知识库目录中没有找到支持的文件")
                print(f"支持的文件格式: {', '.join(SUPPORTED_EXTENSIONS)}")
                return {'success': False, 'error': 'no_files_found'}
            
            print(f"找到 {len(all_files)} 个文件待处理")
            print()
            
            # 检查已存在的文件（基于哈希值和文件名）
            print("正在检查已存在的文件记录...")
            existing_files_by_hash = self.check_existing_files_by_hash()
            
            # 向后兼容：也检查文件名和文件路径
            existing_files_by_name = {}
            existing_files_by_path = {}
            records = RagFileRecord.query.filter(RagFileRecord.status == 'active').all()
            for record in records:
                if record.file_path:
                    filename = Path(record.file_path).name
                    existing_files_by_name[filename] = record
                    # 也检查完整路径（用于更精确地去重）
                    existing_files_by_path[record.file_path] = record
            
            print(f"已存在 {len(existing_files_by_hash)} 个文件记录（基于哈希值）")
            print(f"已存在 {len(existing_files_by_name)} 个文件记录（基于文件名）")
            print(f"已存在 {len(existing_files_by_path)} 个文件记录（基于文件路径）")
            
            # 检查向量库中的重复数据
            duplicate_count = self._check_vector_db_duplicates(vector_db)
            if duplicate_count > 0:
                print(f"⚠️  向量库中发现 {duplicate_count} 个可能的重复文档块")
            print()
            
            # 统计变量
            success_count = 0
            skipped_count = 0
            error_count = 0
            duplicate_count = 0
            total_documents = 0
            total_size_mb = 0
            failed_files = []
            
            # 处理每个文件
            start_time = time.time()
            
            for i, file_info in enumerate(all_files, 1):
                filename = file_info['name']
                file_size_mb = file_info['size_mb']
                
                print(f"[{i}/{len(all_files)}] 处理: {filename}")
                if file_size_mb > 1:
                    print(f"  文件大小: {file_size_mb:.2f} MB")
                
                file_start_time = time.time()
                
                result = self.import_single_file(
                    file_info=file_info,
                    vector_db=vector_db,
                    existing_files_by_hash=existing_files_by_hash,
                    existing_files_by_name=existing_files_by_name,
                    existing_files_by_path=existing_files_by_path,
                    force_update=force_update,
                    dry_run=dry_run
                )
                
                file_processing_time = time.time() - file_start_time
                
                if result['success']:
                    if result.get('skipped'):
                        skipped_count += 1
                        if result.get('is_duplicate'):
                            duplicate_count += 1
                            print(f"  ⏭️  {result['message']}")
                        else:
                            print(f"  ⏭️  {result['message']}")
                    else:
                        success_count += 1
                        document_ids = result.get('document_ids', [])
                        total_documents += len(document_ids)
                        total_size_mb += file_size_mb
                        print(f"  ✅ {result['message']}")
                        if document_ids:
                            print(f"     文档块数: {len(document_ids)}")
                        print(f"     处理时间: {file_processing_time:.2f}s")
                        if result.get('file_hash'):
                            print(f"     哈希值: {result['file_hash'][:16]}...")
                else:
                    error_count += 1
                    failed_files.append({
                        'filename': filename,
                        'error': result.get('error', 'unknown'),
                        'message': result.get('message', '导入失败')
                    })
                    print(f"  ❌ {result['message']}")
                
                print()
                
                # 每处理10个文件提交一次数据库（避免事务过大）
                if not dry_run and i % 10 == 0:
                    try:
                        db.session.commit()
                        logger.debug(f"已提交前 {i} 个文件的数据库更改")
                    except Exception as e:
                        logger.warning(f"批量提交失败: {e}")
                        db.session.rollback()
            
            total_processing_time = time.time() - start_time
            
            # 最终提交数据库更改
            if not dry_run:
                try:
                    db.session.commit()
                    print("✅ 数据库更新成功")
                except Exception as e:
                    db.session.rollback()
                    print(f"❌ 数据库更新失败: {e}")
                    return {
                        'success': False,
                        'error': 'database_commit_failed',
                        'message': str(e)
                    }
            
            # 输出统计信息
            print("=" * 80)
            if dry_run:
                print("预览完成（未实际导入）")
            else:
                print("导入完成")
            print("=" * 80)
            print(f"成功导入: {success_count} 个文件")
            print(f"跳过处理: {skipped_count} 个文件")
            if duplicate_count > 0:
                print(f"  - 重复文件: {duplicate_count} 个（基于哈希值检测）")
            print(f"导入失败: {error_count} 个文件")
            if total_documents > 0:
                print(f"总文档块数: {total_documents}")
            if total_size_mb > 0:
                print(f"总文件大小: {total_size_mb:.2f} MB")
            print(f"总处理时间: {total_processing_time:.2f}s")
            if success_count > 0:
                print(f"平均处理时间: {total_processing_time/max(success_count, 1):.2f}s/文件")
            print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            if failed_files:
                print(f"\n{'=' * 80}")
                print(f"❌ 失败文件列表（共 {len(failed_files)} 个）")
                print(f"{'=' * 80}")
                print()
                
                # 显示所有失败文件，便于排查问题
                for idx, failed in enumerate(failed_files, 1):
                    print(f"{idx}. {failed['filename']}")
                    print(f"   错误类型: {failed.get('error', 'unknown')}")
                    print(f"   错误消息: {failed['message']}")
                    print()
                
                print(f"{'=' * 80}")
                print(f"💡 提示：以上 {len(failed_files)} 个文件导入失败，请检查日志获取详细信息")
                print(f"{'=' * 80}")
            
            print("=" * 80)
            
            # 导入后自动更新缺失的哈希值
            if update_hashes and not dry_run:
                print("\n")
                self._update_missing_hashes()
            
            # 导入后执行检查
            if check_after and not dry_run:
                print("\n")
                self._run_checks()
            
            return {
                'success': success_count > 0 or skipped_count > 0,
                'success_count': success_count,
                'skipped_count': skipped_count,
                'error_count': error_count,
                'duplicate_count': duplicate_count,
                'total_documents': total_documents,
                'total_processing_time': total_processing_time,
                'failed_files': failed_files
            }
    
    def _update_missing_hashes(self):
        """导入后自动更新缺失的哈希值"""
        print("=" * 80)
        print("自动更新缺失的哈希值")
        print("=" * 80)
        
        with self.app.app_context():
            records_without_hash = RagFileRecord.query.filter(
                RagFileRecord.status == 'active',
                db.or_(
                    RagFileRecord.file_hash == None,  # noqa: E711
                    RagFileRecord.file_hash == ''
                )
            ).limit(50).all()  # 限制一次最多更新50个
            
            if not records_without_hash:
                print("✅ 所有记录都有哈希值")
                return
            
            updated_count = 0
            for record in records_without_hash:
                try:
                    if record.file_path:
                        file_path = self.uploads_dir / record.file_path
                        if file_path.exists():
                            file_hash = self.knowledge_service.calculate_file_hash(str(file_path))
                            if file_hash:
                                record.file_hash = file_hash
                                updated_count += 1
                except Exception as e:
                    logger.warning(f"更新记录 ID {record.id} 哈希值失败: {e}")
            
            try:
                db.session.commit()
                print(f"✅ 成功更新 {updated_count} 个记录的哈希值")
            except Exception as e:
                db.session.rollback()
                print(f"❌ 更新哈希值失败: {e}")
    
    @staticmethod
    def _check_vector_db_duplicates(vector_db) -> int:
        """检查向量库中的重复数据"""
        try:
            actual_db = getattr(vector_db, '_vector_db', vector_db)
            
            # 检查是否是 SQLiteVectorStore
            if hasattr(actual_db, 'get_all'):
                # SQLiteVectorStore 路径
                all_docs = actual_db.get_all(include=['documents', 'metadatas'])
            else:
                # ChromaDB 路径：获取集合对象
                collection = getattr(actual_db, '_collection', None) or getattr(actual_db, 'collection', None)
                
                if not collection:
                    return 0
                
                # 获取所有文档
                # noqa: SC200 - metadatas 是 ChromaDB API 的正确参数名（复数形式）
                all_docs = collection.get(include=['documents', 'metadatas'])  # noqa: SC200
            
            if not all_docs or 'ids' not in all_docs:
                return 0
            
            # 检查重复的文档内容
            seen_contents = {}
            duplicates = 0
            
            for idx, doc_id in enumerate(all_docs['ids']):
                doc_content = all_docs.get('documents', [None])[idx] if 'documents' in all_docs else None
                if doc_content:
                    # 使用内容的前100个字符作为快速去重键
                    content_key = doc_content[:100].strip()
                    if content_key in seen_contents:
                        duplicates += 1
                    else:
                        seen_contents[content_key] = doc_id
            
            return duplicates
        except Exception as e:
            logger.warning(f"检查向量库重复数据失败: {e}")
            return 0
    
    def _run_checks(self):
        """导入后执行快速检查"""
        try:
            from scripts.check_knowledge_base import KnowledgeBaseChecker
            checker = KnowledgeBaseChecker(self.app)
            print("执行快速检查...")
            checker.check_file_hashes(limit=10)
        except Exception as e:
            logger.warning(f"执行检查失败: {e}")


def list_files(pattern: Optional[str] = None):
    """列出知识库目录中的文件"""
    app = create_app()
    importer = BatchKnowledgeImporter(app)
    
    files = importer.get_knowledge_files(pattern=pattern)
    
    if files:
        print("=" * 80)
        print("知识库目录中的文件")
        print("=" * 80)
        print(f"{'序号':<6} | {'文件名':<50} | {'大小':<12} | {'路径'}")
        print("-" * 80)
        
        total_size = 0
        for i, file_info in enumerate(files, 1):
            size_mb = file_info['size_mb']
            size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{file_info['size']:,} bytes"
            total_size += file_info['size']
            
            filename = file_info['name']
            if len(filename) > 50:
                filename = filename[:47] + "..."
            
            rel_path = str(file_info['relative_path'])
            if len(rel_path) > 30:
                rel_path = "..." + rel_path[-27:]
            
            print(f"{i:<6} | {filename:<50} | {size_str:<12} | {rel_path}")
        
        print("-" * 80)
        print(f"总计: {len(files)} 个文件, {total_size / (1024*1024):.2f} MB")
        print("=" * 80)
    else:
        print("知识库目录中没有找到支持的文件")
        print(f"支持的文件格式: {', '.join(SUPPORTED_EXTENSIONS)}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='批量导入知识库文档到向量数据库（增强版）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 一键导入所有文档
  python batch_import_knowledge.py
  
  # 强制更新已存在的文件
  python batch_import_knowledge.py --force
  
  # 仅导入包含特定关键词的文件
  python batch_import_knowledge.py --pattern "测试"
  
  # 预览模式：只显示将要导入的文件
  python batch_import_knowledge.py --dry-run
  
  # 导入后自动更新缺失的哈希值
  python batch_import_knowledge.py --update-hashes
  
  # 导入后执行完整检查
  python batch_import_knowledge.py --check
  
  # 组合使用
  python batch_import_knowledge.py --force --check --update-hashes
        """
    )
    
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='强制更新已存在的文件（基于哈希值去重仍然有效）'
    )
    parser.add_argument(
        '--pattern', '-p',
        type=str,
        help='文件名称过滤模式'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='仅列出文件，不执行导入'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览模式：只显示将要导入的文件，不实际导入'
    )
    parser.add_argument(
        '--update-hashes', '-u',
        action='store_true',
        help='导入后自动更新缺失的哈希值'
    )
    parser.add_argument(
        '--check', '-c',
        action='store_true',
        help='导入后执行快速检查'
    )
    
    args = parser.parse_args()
    
    app = create_app()
    
    try:
        if args.list:
            # 仅列出文件
            list_files(pattern=args.pattern)
        else:
            # 执行批量导入
            importer = BatchKnowledgeImporter(app)
            result = importer.batch_import(
                force_update=args.force,
                file_pattern=args.pattern,
                dry_run=args.dry_run,
                update_hashes=args.update_hashes,
                check_after=args.check
            )
            
            if result.get('success'):
                if not args.dry_run:
                    print("\n🎉 批量导入完成！")
            else:
                if not args.dry_run:
                    print("\n❌ 批量导入失败！")
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⏹️  导入被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 导入过程中发生异常: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
