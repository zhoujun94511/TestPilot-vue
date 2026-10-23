#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import os
import time
import hashlib
from typing import Dict, Any, List, Optional
from pathlib import Path
from utils.utils_core.logger import get_logger
logger = get_logger(__name__)

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 修复导入问题
try:
    from utils.utils_document_processing.parser import file_loader
except ImportError as import_error:
    # 如果导入失败，定义占位符函数并记录警告
    logger.warning(f"无法导入file_loader模块: {import_error}，使用简化的文件加载器")
    
    def file_loader(file_path):
        """简化的文件加载器（仅支持纯文本）"""
        from pathlib import Path as FilePath
        logger.warning(f"使用简化文件加载器处理 {file_path}，仅支持纯文本格式")
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            # 返回正确格式：texts, splits, metadata
            metadata = [{
                'source': file_path,
                'file_name': FilePath(file_path).name
            }]
            return [content], [], metadata
        except Exception as ex:
            logger.error(f"文件加载失败: {ex}")
            return [], [], []

from flask import current_app
from models.models import RagFileRecord
from utils.utils_performance_monitoring.performance_monitor import get_performance_monitor
from utils.utils_ai_models.embedding_monitor import get_embedding_monitor
from utils.utils_intelligent_retrieval.smart_retrieval_strategy import get_smart_retrieval_strategy
from utils.utils_document_processing.smart_document_chunking import get_smart_document_chunker
from config.settings import settings

# 修复langchain导入问题（兼容不同版本的 langchain）
try:
    from langchain_core.documents import Document
except ImportError:
    try:
        from langchain.schema import Document
    except ImportError:
        try:
            from langchain.documents import Document
        except ImportError:
            # 如果都失败，定义占位符类
            class Document:
                def __init__(self, page_content: str, metadata: dict = None):
                    self.page_content = page_content
                    self.metadata = metadata or {}


class _DigestReader:
    """提供 file_digest 需要的二进制读取接口。"""

    def __init__(self, raw):
        self._raw = raw

    def readinto(self, buf: bytearray) -> int:
        chunk = self._raw.read(len(buf))
        if not isinstance(chunk, (bytes, bytearray)) or not chunk:
            return 0
        size = len(chunk)
        buf[:size] = chunk
        return size

    @staticmethod
    def readable() -> bool:
        return True


class KnowledgeService:
    """知识库管理服务"""

    def __init__(self):
        self.performance_monitor = get_performance_monitor()
        self.embedding_monitor = get_embedding_monitor()
        self.smart_retrieval = get_smart_retrieval_strategy()
        self.smart_chunker = get_smart_document_chunker()
        self.supported_formats = ['txt', 'csv', 'docx', 'pdf']
    
    @staticmethod
    def calculate_file_hash(file_path: str = None, file_stream=None) -> str:
        """计算文件的SHA256哈希值（用于文件去重）
        
        Args:
            file_path: 文件路径（字符串或Path对象），如果提供则从文件路径读取
            file_stream: 文件流对象（如Flask的request.files['file']），如果提供则从流读取
            
        Returns:
            文件的SHA256哈希值（64字符的十六进制字符串），失败返回空字符串
        """
        sha256_hash = hashlib.sha256()
        try:
            # 优先使用文件流（用于上传时提前检测）
            if file_stream is not None:
                # 保存当前位置
                original_position = file_stream.tell() if hasattr(file_stream, 'tell') else None
                
                # 重置到开头（如果支持）
                if hasattr(file_stream, 'seek') and original_position is not None:
                    file_stream.seek(0)
                
                # 分块读取，避免内存溢出
                while True:
                    chunk = file_stream.read(4096)
                    if not chunk:
                        break
                    sha256_hash.update(chunk)
                
                # 恢复原位置（如果支持）
                if hasattr(file_stream, 'seek') and original_position is not None:
                    file_stream.seek(original_position)
                
                result = sha256_hash.hexdigest()
                file_name = getattr(file_stream, 'filename', 'stream')
                logger.debug(f"文件流哈希计算成功: {file_name} -> {result[:8]}...")
                return result
            
            # 从文件路径读取
            if file_path:
                path = Path(file_path) if isinstance(file_path, str) else file_path
                
                # 确保文件存在
                if not path.exists():
                    logger.error(f"计算文件哈希失败: 文件不存在 - {file_path}")
                    return ''
                
                # 确保文件可读
                if not path.is_file():
                    logger.error(f"计算文件哈希失败: 不是文件或无法读取 - {file_path}")
                    return ''
                
                with open(path, 'rb') as handle:
                    result = hashlib.file_digest(_DigestReader(handle), 'sha256').hexdigest()
                return result
            
            logger.error("计算文件哈希失败: 未提供文件路径或文件流")
            return ''
            
        except PermissionError as e:
            logger.error(f"计算文件哈希失败: 权限不足 - {e}")
            return ''
        except Exception as e:
            logger.error(f"计算文件哈希失败: {e}", exc_info=True)
            return ''
    
    @staticmethod
    def check_and_handle_duplicate_file(
            file_hash: str,
            file_path: Path,
            _upload_folder: Path = None,
            _vector_db=None
    ) -> Dict[str, Any]:
        """检查是否存在重复文件（相同哈希值）
        
        Args:
            file_hash: 文件哈希值
            file_path: 新文件路径
            _upload_folder: 上传文件夹路径（未使用，保留以兼容接口）
            _vector_db: 向量数据库实例（未使用，保留以兼容接口）
            
        Returns:
            包含 is_duplicate 和 existing_record 的字典
        """
        from models.models import RagFileRecord
        
        if not file_hash:
            return {'is_duplicate': False, 'existing_record': None}
        
        # 检查是否存在相同哈希的文件
        existing_record = RagFileRecord.query.filter_by(
            file_hash=file_hash,
            status='active'
        ).first()
        
        if not existing_record:
            return {'is_duplicate': False, 'existing_record': None}
        
        logger.info(f"检测到重复文件（哈希: {file_hash[:8]}...）: {file_path.name} -> 已存在相同文件 (ID: {existing_record.id})，跳过处理")
        
        return {
            'is_duplicate': True,
            'existing_record': existing_record
        }
    
    def upload_knowledge_file_with_deduplication(
            self,
            file_path: str,
            original_filename: str,
            description: str = '',
            category: str = 'other',
            upload_folder: Path = None,
            vector_db=None
    ) -> Dict[str, Any]:
        """上传知识库文件（包含重复检测和覆盖逻辑）
        
        Args:
            file_path: 文件路径
            original_filename: 原始文件名
            description: 文件描述
            category: 文件分类
            upload_folder: 上传文件夹路径
            vector_db: 向量数据库实例
            
        Returns:
            上传结果字典
        """
        from models.models import db, RagFileRecord
        
        file_path_obj = Path(file_path)
        upload_folder = upload_folder or Path(file_path_obj.parent)
        
        # 确保文件已存在且可访问
        if not file_path_obj.exists():
            return {
                'success': False,
                'message': f'文件不存在: {file_path}',
                'error': 'file_not_found'
            }
        
        # 获取文件信息
        file_size = file_path_obj.stat().st_size
        file_type = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        
        # 计算文件哈希值（必须在文件保存后，确保文件已完全写入磁盘）
        file_hash = self.calculate_file_hash(str(file_path_obj))
        
        # 如果哈希值为空，尝试重试（可能是文件刚写入，需要短暂延迟）
        if not file_hash:
            import time
            logger.warning(f"文件哈希计算返回空值，尝试重试: {file_path}")
            time.sleep(0.2)  # 等待200ms后重试
            file_hash = self.calculate_file_hash(str(file_path_obj))
            
            if not file_hash:
                logger.warning(f"文件哈希计算重试后仍为空，继续处理文件（将保存为NULL）: {file_path}")
        
        # 检查是否存在重复文件（相同哈希值）
        # 注意：上传层已经提前检查过，这里再次检查作为双重保险
        duplicate_info = self.check_and_handle_duplicate_file(
            file_hash=file_hash,
            file_path=file_path_obj,
            _upload_folder=upload_folder,
            _vector_db=vector_db
        )
        
        is_duplicate = duplicate_info['is_duplicate']
        existing_record = duplicate_info.get('existing_record')
        
        # 如果检测到重复文件（上传层可能已经处理，但这里作为双重保险）
        if is_duplicate and existing_record:
            # 删除新上传的重复文件（节省存储空间）
            try:
                if file_path_obj.exists():
                    file_path_obj.unlink()
                    logger.info(f"已删除重复的新上传文件: {file_path_obj}")
            except (OSError, IOError) as e:
                logger.warning(f"删除重复文件失败: {e}")
            
            # 解析现有记录的文档ID列表
            doc_ids = []
            if existing_record.ids:
                try:
                    import ast
                    doc_ids = ast.literal_eval(existing_record.ids)
                    if not isinstance(doc_ids, list):
                        doc_ids = []
                except (ValueError, SyntaxError):
                    doc_ids = []
            
            # 返回现有记录信息，跳过所有处理
            return {
                'success': True,
                'message': f'文件已存在（相同哈希值），已跳过处理',
                'file_info': {
                    'id': existing_record.id,
                    'file_name': existing_record.file_name,  # 统一使用 file_name，与列表接口保持一致
                    'filename': existing_record.file_name,  # 保留 filename 以兼容旧代码
                    'file_size': existing_record.file_size,
                    'file_type': existing_record.file_type,
                    'document_count': len(doc_ids),
                    'created_time': existing_record.created_time.isoformat() if existing_record.created_time else None,
                    'is_duplicate': True
                }
            }
        
        # 处理文件并添加到向量数据库（非重复文件）
        process_result = self.process_knowledge_file(
            file_path=file_path,
            vector_db=vector_db
        )
        
        if not process_result['success']:
            return process_result
        
        # 保存或更新文件记录
        # 处理哈希值：空字符串转换为 None（让数据库处理 NULL）
        hash_value = file_hash if file_hash and file_hash.strip() else None
        
        rag_record = RagFileRecord(
            file_name=original_filename,
            file_path=str(file_path_obj.relative_to(upload_folder)),
            file_size=file_size,
            file_type=file_type,
            file_hash=hash_value,  # 使用处理后的哈希值（None 或有效哈希）
            ids=str(process_result['document_ids']),
            status='active',
            description=description,
            category=category
        )
        db.session.add(rag_record)
        
        try:
            db.session.commit()
            logger.info(f"数据库提交成功 - 记录ID: {rag_record.id}, 哈希值: {repr(hash_value)}")
            
            # 如果保存时哈希值为空，尝试补充（文件已保存到磁盘，应该可以计算）
            if not hash_value:
                logger.info(f"尝试为记录ID {rag_record.id} 补充哈希值...")
                import time
                time.sleep(0.1)  # 短暂延迟确保文件完全写入
                new_hash = self.calculate_file_hash(str(file_path_obj))
                if new_hash:
                    rag_record.file_hash = new_hash
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(rag_record, 'file_hash')
                    db.session.commit()
                    logger.info(f"成功补充哈希值: {new_hash[:16]}...")
                else:
                    logger.warning(f"无法为记录ID {rag_record.id} 补充哈希值，文件可能需要后续手动修复")
            
            # 提交后验证 - 直接从数据库查询确认（用于调试和验证）
            verify_record = RagFileRecord.query.get(rag_record.id)
            if verify_record:
                final_hash = verify_record.file_hash
                if final_hash != hash_value and final_hash:  # 如果补充成功，final_hash会不同
                    logger.info(f"哈希值已补充: {final_hash[:16] if final_hash else None}...")
                elif final_hash != hash_value:
                    logger.error(f"⚠️ 哈希值保存失败！期望: {repr(hash_value)}, 实际: {repr(final_hash)}")
                elif final_hash:
                    logger.debug(f"哈希值验证成功: {final_hash[:16]}...")
        except Exception as e:
            logger.error(f"数据库提交失败: {e}", exc_info=True)
            db.session.rollback()
            raise
        
        action = '上传'
        
        return {
            'success': True,
            'message': f'知识库文件{action}成功',
            'file_info': {
                'id': rag_record.id,
                'file_name': original_filename,  # 统一使用 file_name，与列表接口保持一致
                'filename': original_filename,  # 保留 filename 以兼容旧代码
                'file_size': file_size,
                'file_type': file_type,
                'document_count': len(process_result['document_ids']),
                'created_time': rag_record.created_time.isoformat() if rag_record.created_time else None,
                'is_duplicate': False
            }
        }

    def process_knowledge_file(
            self,
            file_path: str,
            vector_db=None
    ) -> Dict[str, Any]:
        """处理知识库文件"""
        try:
            failed_batch_count = 0
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'message': '文件不存在',
                    'error': 'file_not_found'
                }

            if not vector_db:
                return {
                    'success': False,
                    'message': '向量数据库未初始化',
                    'error': 'vector_db_not_initialized'
                }

            # 记录开始时间
            start_time = self.performance_monitor.start_timer()

            # 使用智能文档分块
            use_smart_chunking = getattr(settings, 'CHUNK_ENABLE_SEMANTIC_BOUNDARY', True)
            texts = []  # 初始化texts变量
            
            if use_smart_chunking:
                # 读取文件内容
                from utils.utils_core.common_utils import clean_text
                ext = Path(file_path).suffix.lower()
                
                # 对于需要特殊解析的文件类型（PDF、DOCX等），使用file_loader
                if ext in ['.pdf', '.docx', '.xlsx', '.csv', '.json', '.yaml', '.yml']:
                    # 使用文件加载器解析文档
                    texts, _, _ = file_loader(file_path)
                    # 合并文本并清理
                    content = '\n'.join(texts)
                    content = clean_text(content)
                else:
                    # 纯文本文件类型（txt、md等）直接读取
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    # 清理文本内容
                    content = clean_text(content)
                
                # 使用智能分块
                chunks = self.smart_chunker.chunk_document(
                    content=content,
                    metadata={'source': file_path, 'type': ext}
                )
                
                # 转换为LangChain Document格式（使用模块顶部已解析的 Document）
                from utils.utils_core.common_utils import clean_text
                splits = []
                for chunk in chunks:
                    # 检查chunk.content是否存在且为字符串
                    if not hasattr(chunk, 'content') or chunk.content is None:
                        logger.warning(f"跳过无效的chunk（缺少content）")
                        continue
                    
                    # 确保content是字符串类型
                    if not isinstance(chunk.content, str):
                        try:
                            chunk_content = str(chunk.content)
                        except Exception as e:
                            logger.warning(f"无法将chunk.content转换为字符串: {e}")
                            continue
                    else:
                        chunk_content = chunk.content
                    
                    # 清理chunk内容，确保没有乱码
                    cleaned_content = clean_text(chunk_content)
                    if not cleaned_content or not cleaned_content.strip():
                        logger.debug(f"跳过空内容chunk（清理后为空）")
                        continue
                    
                    # 将keywords列表转换为字符串（ChromaDB不支持list类型的metadata）
                    keywords_str = ', '.join(chunk.keywords) if chunk.keywords else ''
                    
                    # 🔧 清理metadata中的字符串值，移除代理对字符（ChromaDB无法处理）
                    def clean_metadata_value(value):
                        """清理metadata值，移除无效的UTF-8字符"""
                        if value is None:
                            return None
                        if isinstance(value, str):
                            # 移除代理对字符（会导致ChromaDB编码错误）
                            import re
                            cleaned = re.sub(r'[\uD800-\uDFFF]', '', value)
                            # 确保是有效的UTF-8
                            try:
                                cleaned.encode('utf-8').decode('utf-8')
                            except (UnicodeEncodeError, UnicodeDecodeError):
                                cleaned = cleaned.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                            return cleaned
                        return value
                    
                    doc_metadata = {
                        'source': clean_metadata_value(str(file_path)),
                        'file_name': clean_metadata_value(Path(file_path).name),
                        'chunk_id': clean_metadata_value(str(chunk.metadata.chunk_id)),
                        'content_type': clean_metadata_value(chunk.metadata.content_type.value),
                        'quality_score': float(chunk.metadata.quality_score),
                        'semantic_coherence': float(chunk.metadata.semantic_coherence),
                        'keywords': clean_metadata_value(keywords_str)
                    }
                    
                    # 最终验证：确保cleaned_content是有效的字符串
                    if not isinstance(cleaned_content, str):
                        logger.error(f"chunk.content清理后不是字符串类型: {type(cleaned_content)}")
                        cleaned_content = str(cleaned_content) if cleaned_content is not None else ""
                    
                    # 🔧 再次清理page_content，移除代理对字符（ChromaDB无法处理）
                    import re
                    cleaned_content = re.sub(r'[\uD800-\uDFFF]', '', cleaned_content)
                    # 确保是有效的UTF-8
                    try:
                        cleaned_content.encode('utf-8').decode('utf-8')
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        cleaned_content = cleaned_content.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                    
                    if not cleaned_content or not cleaned_content.strip():
                        logger.debug(f"跳过空内容chunk（清理后为空）")
                        continue
                    
                    splits.append(Document(
                        page_content=cleaned_content,
                        metadata=doc_metadata
                    ))
                    # 同时填充texts用于后续处理
                    texts.append(cleaned_content)
                
            else:
                # 使用传统文件加载器
                from utils.utils_core.common_utils import clean_text
                texts, splits, metadata = file_loader(file_path)
                if not texts:
                    return {
                        'success': False,
                        'message': '文件内容为空或无法解析',
                        'error': 'empty_content'
                    }

                # 清理文本内容，移除乱码
                texts = [clean_text(text) for text in texts if clean_text(text).strip()]
                
                # 内容预处理：去重和清理
                original_count = len(texts)
                texts = self._preprocess_texts(texts)
                processed_count = len(texts)

                logger.info(f"文档预处理：从{original_count}个文本块去重到{processed_count}个文本块")

                # 确保metadata包含必要字段（使用模块顶部已解析的 Document）
                base_metadata = metadata[0] if metadata else {}
                base_metadata['file_name'] = Path(file_path).name
                if 'source' not in base_metadata:
                    base_metadata['source'] = file_path
                
                # 如果有预处理后的文本或splits为空，重新生成splits
                if not splits or processed_count != original_count:
                    splits = []
                    for text in texts:
                        # 确保text是有效的字符串
                        if not text or not isinstance(text, str):
                            continue
                        text = text.strip()
                        if not text:
                            continue
                        splits.append(Document(page_content=text, metadata=base_metadata.copy()))
                else:
                    # 更新现有splits的metadata，并验证page_content
                    valid_splits = []
                    for split in splits:
                        if hasattr(split, 'metadata'):
                            split.metadata.update(base_metadata)
                        # 验证page_content
                        if hasattr(split, 'page_content'):
                            page_content = split.page_content
                            if not page_content or not isinstance(page_content, str):
                                logger.warning("跳过无效的split（page_content无效）")
                                continue
                            if not page_content.strip():
                                logger.debug("跳过空内容的split")
                                continue
                        valid_splits.append(split)
                    splits = valid_splits

            
            failed_batch_count = 0
            if splits:
                # 分批添加文档（从配置中获取批次大小，Windows 上需要更小的批次以避免访问冲突）
                batch_size = settings.get_vector_db_batch_size()
                batch_delay = settings.get_vector_db_batch_delay()
                is_windows = settings.is_windows()
                
                all_document_ids = []
                total_batches = (len(splits) + batch_size - 1) // batch_size
                
                for i in range(0, len(splits), batch_size):
                    batch = splits[i:i + batch_size]
                    batch_num = i // batch_size + 1
                    
                    # 验证批次中的每个文档的page_content
                    valid_batch = []
                    for idx, doc in enumerate(batch):
                        if not hasattr(doc, 'page_content'):
                            logger.warning(f"跳过无效文档（索引 {idx}，缺少page_content）")
                            continue
                        page_content = doc.page_content
                        original_type = type(page_content).__name__
                        
                        if page_content is None:
                            logger.warning(f"跳过无效文档（索引 {idx}，page_content为None）")
                            continue
                        
                        if not isinstance(page_content, str):
                            logger.error(f"文档（索引 {idx}）page_content不是字符串类型: {original_type}, 值: {repr(page_content)[:100]}")
                            try:
                                page_content_str = str(page_content)
                                if not page_content_str.strip():
                                    logger.warning(f"跳过无效文档（索引 {idx}，转换后为空）")
                                    continue
                                # 强制更新为字符串
                                doc.page_content = page_content_str
                                logger.info(f"已将文档（索引 {idx}）page_content从 {original_type} 转换为字符串")
                                page_content = page_content_str
                            except Exception as e:
                                logger.error(f"无法将page_content转换为字符串（索引 {idx}）: {e}")
                                continue
                        
                        if not page_content or not page_content.strip():
                            logger.debug(f"跳过空内容文档（索引 {idx}）")
                            continue
                        
                        # 最终验证：确保page_content是有效的字符串
                        if not isinstance(doc.page_content, str):
                            logger.error(f"文档（索引 {idx}）page_content验证失败，仍不是字符串: {type(doc.page_content)}")
                            continue
                        
                        valid_batch.append(doc)
                    
                    if not valid_batch:
                        logger.warning(f"批次 {batch_num} 中没有有效文档，跳过")
                        continue
                    
                    if len(valid_batch) != len(batch):
                        logger.warning(f"批次 {batch_num}：从 {len(batch)} 个文档过滤到 {len(valid_batch)} 个有效文档")
                    
                    # 🔧 提前检查：验证文档的page_content是否为空，避免ChromaDB处理空embeddings
                    # 提取所有文档的page_content用于embedding检查
                    batch_texts = [doc.page_content for doc in valid_batch if hasattr(doc, 'page_content') and doc.page_content]
                    if not batch_texts:
                        logger.warning(
                            f"批次 {batch_num} 中所有文档的page_content为空或无效，"
                            f"跳过以避免ChromaDB处理空embeddings"
                        )
                        continue
                    
                    try:
                        
                        # 添加批次时使用异常处理和重试机制
                        max_retries = getattr(settings, 'VECTOR_DB_BATCH_MAX_RETRIES', 3)
                        retry_wait_base = getattr(settings, 'VECTOR_DB_BATCH_RETRY_WAIT_BASE', 0.5)
                        retry_count = 0
                        batch_ids = None
                        
                        while retry_count < max_retries:
                            try:
                                batch_ids = vector_db.add_documents(valid_batch)
                                break  # 成功则跳出重试循环
                            except Exception as retry_error:
                                retry_count += 1
                                if retry_count < max_retries:
                                    import time
                                    wait_time = retry_count * retry_wait_base  # 递增等待时间
                                    logger.warning(f"批次 {batch_num} 添加失败，重试 {retry_count}/{max_retries} (等待 {wait_time}s): {retry_error}")
                                    time.sleep(wait_time)
                                else:
                                    raise  # 最后一次重试失败则抛出异常
                        
                        # 处理返回的ID格式
                        if isinstance(batch_ids, dict):
                            batch_ids = batch_ids.get('ids', [])
                        elif batch_ids is None:
                            logger.warning(f"批次 {batch_num} 返回None，可能添加失败")
                            batch_ids = []
                        elif not isinstance(batch_ids, list):
                            batch_ids = [batch_ids] if batch_ids else []
                        
                        # 检查返回的ID数量是否与文档数量匹配
                        if len(batch_ids) != len(valid_batch):
                            logger.warning(
                                f"批次 {batch_num} ID数量不匹配："
                                f"文档数量={len(valid_batch)}, 返回ID数量={len(batch_ids)}"
                            )
                            # 如果返回的ID为空但文档不为空，记录详细信息
                            if not batch_ids and valid_batch:
                                logger.error(f"批次 {batch_num} 未返回任何ID，但提交了 {len(valid_batch)} 个文档")
                                for doc_idx, doc in enumerate(valid_batch[:3]):
                                    logger.error(
                                        f"  文档[{doc_idx}]: page_content类型={type(doc.page_content).__name__}, "
                                        f"长度={len(doc.page_content) if hasattr(doc, 'page_content') and doc.page_content else 0}"
                                    )
                        
                        all_document_ids.extend(batch_ids)
                        if batch_ids:
                            logger.info(f"✅ 批次 {batch_num}/{total_batches} 添加成功，包含 {len(valid_batch)} 个文档块，获得 {len(batch_ids)} 个ID")
                        else:
                            logger.warning(f"⚠️ 批次 {batch_num}/{total_batches} 添加完成但未返回ID，包含 {len(valid_batch)} 个文档块")
                        
                        # 在批次之间添加延迟（Windows 上延迟更长，避免过快写入导致冲突）
                        if batch_delay > 0 and i + batch_size < len(splits):
                            import time
                            time.sleep(batch_delay)
                            
                    except Exception as batch_error:
                        logger.error(f"❌ 添加文档批次 {batch_num}/{total_batches} 失败: {batch_error}", exc_info=True)
                        failed_batch_count += 1
                        # 记录失败的文档内容类型信息，便于调试
                        if valid_batch:
                            sample_content = valid_batch[0].page_content if hasattr(valid_batch[0], 'page_content') else None
                            logger.error(f"失败批次示例内容类型: {type(sample_content)}, 长度: {len(sample_content) if sample_content else 0}")
                        # Windows 上即使失败也继续，避免整个流程中断
                        if is_windows:
                            logger.warning(f"Windows 环境下继续处理下一批次...")
                            continue
                        else:
                            # 非 Windows 环境下可以选择继续或中断
                            continue
                
                document_ids = all_document_ids
                if all_document_ids:
                    logger.info(f"文档分块添加完成：共 {len(splits)} 个块，分批 {len(all_document_ids)} 个ID")
                else:
                    logger.warning(f"文档分块添加完成：共 {len(splits)} 个块，但未获得任何ID（可能所有文档在验证阶段被过滤）")
            else:
                # 为每个文档添加metadata信息
                documents = [
                    Document(
                        page_content=text,
                        metadata={
                            'source': file_path,
                            'file_name': Path(file_path).name,
                            'chunk_index': i
                        }
                    ) for i, text in enumerate(texts)
                ]
                
                # 分批添加文档（从配置中获取批次大小，Windows 上需要更小的批次以避免访问冲突）
                batch_size = settings.get_vector_db_batch_size()
                batch_delay = settings.get_vector_db_batch_delay()
                is_windows = settings.is_windows()
                
                all_document_ids = []
                total_batches = (len(documents) + batch_size - 1) // batch_size
                
                for i in range(0, len(documents), batch_size):
                    batch = documents[i:i + batch_size]
                    batch_num = i // batch_size + 1
                    
                    # 🔧 提前检查：验证文档的page_content是否为空，避免ChromaDB处理空embeddings
                    batch_texts = [doc.page_content for doc in batch if hasattr(doc, 'page_content') and doc.page_content]
                    if not batch_texts:
                        logger.warning(
                            f"批次 {batch_num} 中所有文档的page_content为空或无效，"
                            f"跳过以避免ChromaDB处理空embeddings"
                        )
                        continue
                    
                    try:
                        logger.debug(f"开始添加批次 {batch_num}/{total_batches}，包含 {len(batch)} 个文档")
                        
                        # 添加批次时使用异常处理和重试机制
                        max_retries = getattr(settings, 'VECTOR_DB_BATCH_MAX_RETRIES', 3)
                        retry_wait_base = getattr(settings, 'VECTOR_DB_BATCH_RETRY_WAIT_BASE', 0.5)
                        retry_count = 0
                        batch_ids = None
                        
                        while retry_count < max_retries:
                            try:
                                batch_ids = vector_db.add_documents(batch)
                                break  # 成功则跳出重试循环
                            except Exception as retry_error:
                                retry_count += 1
                                if retry_count < max_retries:
                                    import time
                                    wait_time = retry_count * retry_wait_base  # 递增等待时间
                                    logger.warning(f"批次 {batch_num} 添加失败，重试 {retry_count}/{max_retries} (等待 {wait_time}s): {retry_error}")
                                    time.sleep(wait_time)
                                else:
                                    raise  # 最后一次重试失败则抛出异常
                        
                        # 处理返回的ID格式
                        if isinstance(batch_ids, dict):
                            batch_ids = batch_ids.get('ids', [])
                        elif batch_ids is None:
                            batch_ids = []
                        elif not isinstance(batch_ids, list):
                            batch_ids = [batch_ids] if batch_ids else []
                        
                        all_document_ids.extend(batch_ids)
                        logger.info(f"✅ 批次 {batch_num}/{total_batches} 添加成功，包含 {len(batch)} 个文档，获得 {len(batch_ids)} 个ID")
                        
                        # 在批次之间添加延迟（Windows 上延迟更长，避免过快写入导致冲突）
                        if batch_delay > 0 and i + batch_size < len(documents):
                            import time
                            time.sleep(batch_delay)
                            
                    except Exception as batch_error:
                        logger.error(f"❌ 添加文档批次 {batch_num}/{total_batches} 失败: {batch_error}", exc_info=True)
                        failed_batch_count += 1
                        # Windows 上即使失败也继续，避免整个流程中断
                        if is_windows:
                            logger.warning(f"Windows 环境下继续处理下一批次...")
                            continue
                        else:
                            continue
                
                document_ids = all_document_ids
            
            # 确保 document_ids 是列表格式
            if document_ids is None:
                return {
                    'success': False,
                    'message': '文档添加到向量数据库失败',
                    'error': 'vector_add_failed'
                }
            
            # 如果返回的是字典（ChromaDB的某些版本可能返回字典），提取ids
            if isinstance(document_ids, dict):
                if 'ids' in document_ids:
                    document_ids = document_ids['ids']
                else:
                    return {
                        'success': False,
                        'message': '文档添加到向量数据库失败：返回格式错误',
                        'error': 'invalid_return_format'
                    }
            
            if not document_ids:
                # 检查是否所有文档都被过滤掉了
                splits_count = len(splits) if 'splits' in locals() and splits else 0
                if splits_count == 0:
                    return {
                        'success': False,
                        'message': '文档内容为空或全部被过滤，无法添加到向量数据库',
                        'error': 'empty_content'
                    }
                else:
                    # 有文档但未返回ID，可能是ChromaDB的问题
                    logger.error(
                        f"文档添加到向量数据库失败：提交了 {splits_count} 个文档块，但未返回任何ID。"
                        f"这可能是因为：1) 所有文档在验证阶段被过滤；2) ChromaDB返回了空ID列表；"
                        f"3) embedding编码失败导致文档被跳过。请检查日志中的详细错误信息。"
                    )
                    return {
                        'success': False,
                        'message': f'文档添加到向量数据库失败：提交了 {splits_count} 个文档块，但未返回文档ID。请检查日志获取详细信息。',
                        'error': 'no_document_ids'
                    }

            # 记录性能指标
            elapsed_time = self.performance_monitor.end_timer(start_time)

            message = f'成功处理文档，添加了{len(document_ids)}个文档块'
            if failed_batch_count:
                message += f'，另有{failed_batch_count}个批次写入失败'
            return {
                'success': True,
                'message': message,
                'partial': bool(failed_batch_count),
                'document_ids': document_ids,
                'processing_time': elapsed_time,
                'content_length': sum(len(text) for text in texts)
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'知识库文件处理失败: {str(e)}',
                'error': str(e)
            }

    def search_knowledge(
            self,
            query: str,
            vector_db=None,
            top_k: int = None,
            score_threshold: float = None,
            use_smart_retrieval: bool = True,
            context: Optional[str] = None
    ) -> Dict[str, Any]:
        """搜索知识库（支持智能检索）"""
        try:
            # 使用 settings 中的默认值
            if top_k is None:
                top_k = getattr(settings, 'RAG_TOP_K', 5)
            if score_threshold is None:
                score_threshold = getattr(settings, 'RAG_SCORE_THRESHOLD', 0.7)
                
            if not query.strip():
                return {
                    'success': False,
                    'message': '搜索查询不能为空',
                    'error': 'empty_query'
                }

            if not vector_db:
                return {
                    'success': False,
                    'message': '向量数据库未初始化',
                    'error': 'vector_db_not_initialized'
                }

            # 记录开始时间
            start_time = self.performance_monitor.start_timer()

            # 使用智能检索策略
            if use_smart_retrieval:
                # 执行智能检索，直接传入 top_k 参数
                smart_results = self.smart_retrieval.retrieve(
                    query=query,
                    vector_db=vector_db,
                    context=context,
                    top_k=top_k
                )
                
                # 转换为标准格式，并补充文件信息
                search_results = []
                for result in smart_results:
                    # 如果metadata为空或缺少source，尝试通过内容查找文件
                    metadata = result.metadata or {}
                    if not metadata.get('source'):
                        # 通过文档内容查找对应的文件
                        file_info = self._find_file_by_content(result.content)
                        if file_info:
                            metadata['source'] = file_info.get('file_path', '')
                            metadata['file_name'] = file_info.get('file_name', '未知文件')
                            metadata['file_id'] = file_info.get('file_id')
                    
                    # 清理搜索结果内容，移除乱码
                    from utils.utils_core.common_utils import clean_text
                    cleaned_content = clean_text(result.content) if result.content else ''
                    
                    search_results.append({
                        'content': cleaned_content,
                        'score': result.score,
                        'metadata': metadata,
                        'strategy': result.strategy.value,
                        'relevance_factors': result.relevance_factors
                    })
                search_results = [
                    item for item in search_results
                    if float(item.get('score') or 0) >= float(score_threshold)
                ]
                
            else:
                # 使用传统搜索
                search_start_time = time.time()
                results = vector_db.similarity_search(query, k=top_k)
                search_duration = time.time() - search_start_time
                
                # 记录embedding性能指标
                self.embedding_monitor.record_call(
                    tokens=len(query.split()),
                    duration=search_duration,
                    success=True,
                    cache_hit=False,
                    model_name="sentence-transformers",
                    device="auto"
                )

                # 处理搜索结果 + 阈值过滤
                from utils.utils_core.common_utils import clean_text
                search_results = []
                for i, doc in enumerate(results):
                    score = getattr(doc, 'score', 1.0)  # 默认得分 1.0
                    if score < score_threshold:
                        continue
                    # 清理搜索结果内容，移除乱码
                    cleaned_content = clean_text(doc.page_content) if doc.page_content else ''
                    search_results.append({
                        'rank': i + 1,
                        'content': cleaned_content,
                        'metadata': getattr(doc, 'metadata', {}),
                        'relevance_score': score,
                        'relevance_level': self._calculate_relevance(score)
                    })

            # 注意：文件信息补充在blueprint中调用，因为需要在应用上下文中执行
            # 这里不调用，避免应用上下文问题
            
            # 记录性能指标
            elapsed_time = self.performance_monitor.end_timer(start_time)

            return {
                'success': True,
                'query': query,
                'documents': search_results,
                'total_results': len(search_results),
                'search_time': elapsed_time
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'知识库搜索失败: {str(e)}',
                'error': str(e)
            }

    @staticmethod
    def _preprocess_texts(texts):
        """
        对文本进行预处理：去重、清理

        Args:
            texts: 文本列表

        Returns:
            预处理后的文本列表
        """
        if not texts:
            return texts

        # 计算文本相似度的简单方法：基于Jaccard相似度
        def calculate_similarity(text1, text2):
            """计算两个文本的Jaccard相似度"""  # noqa: SC200
            try:
                # 分词（简单空格分割）
                words1 = set(text1.lower().split())
                words2 = set(text2.lower().split())

                if not words1 or not words2:
                    return 0.0

                # 计算交集和并集
                intersection = len(words1.intersection(words2))
                union = len(words1.union(words2))

                return intersection / union if union > 0 else 0.0
            except (AttributeError, TypeError, ValueError):
                return 0.0

        processed_texts = []

        for text in texts:
            # 跳过过短的文本
            if len(text.strip()) < 10:
                continue

            # 检查是否与已有文本过于相似
            is_duplicate = False
            for existing_text in processed_texts:
                similarity = calculate_similarity(text, existing_text)
                if similarity > 0.85:  # 相似度阈值85%
                    is_duplicate = True
                    break

            if not is_duplicate:
                processed_texts.append(text.strip())

        return processed_texts

    def get_document_preview(
            self,
            document_id: str,
            vector_db=None,
            max_length: int = 2000
    ) -> Dict[str, Any]:
        """获取文档预览"""
        try:
            if not vector_db:
                return {
                    'success': False,
                    'message': '向量数据库未初始化',
                    'error': 'vector_db_not_initialized'
                }

            # 获取多个文档块来组成更完整的预览
            content = self._get_multiple_documents_by_id(document_id, vector_db, max_chunks=5)
            if content is None or not content.strip():
                return {
                    'success': False,
                    'message': '文档不存在或无法访问',
                    'error': 'document_not_found'
                }

            preview = content[:max_length] + "..." if len(content) > max_length else content

            return {
                'success': True,
                'document_id': document_id,
                'preview': preview,
                'full_length': len(content)
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'获取文档预览失败: {str(e)}',
                'error': str(e)
            }

    @staticmethod
    def delete_documents(
            document_ids: List[str],
            vector_db=None
    ) -> Dict[str, Any]:
        """从向量数据库中删除文档"""
        try:
            if not document_ids:
                return {
                    'success': False,
                    'message': '文档ID列表不能为空',
                    'error': 'empty_document_ids'
                }

            if not vector_db:
                return {
                    'success': False,
                    'message': '向量数据库未初始化',
                    'error': 'vector_db_not_initialized'
                }

            # 分批删除（ChromaDB可能有批量删除限制）
            batch_size = 1000
            total_deleted = 0
            
            for i in range(0, len(document_ids), batch_size):
                batch_ids = document_ids[i:i + batch_size]
                try:
                    # 使用 ChromaDB 的 delete 方法
                    if hasattr(vector_db, 'delete'):
                        vector_db.delete(ids=batch_ids)
                        total_deleted += len(batch_ids)
                        logger.debug(f"已删除批次 {i//batch_size + 1}，包含 {len(batch_ids)} 个文档ID")
                    else:
                        logger.warning("向量数据库不支持 delete 方法")
                except Exception as batch_error:
                    logger.error(f"删除文档批次 {i//batch_size + 1} 失败: {batch_error}")
                    # 继续处理下一批次，不中断整个流程
                    continue

            return {
                'success': True,
                'message': f'成功删除{total_deleted}个文档',
                'deleted_count': total_deleted,
                'deleted_ids': document_ids[:total_deleted] if total_deleted > 0 else []
            }

        except Exception as e:
            logger.error(f"删除向量数据库文档失败: {e}")
            return {
                'success': False,
                'message': f'删除文档失败: {str(e)}',
                'error': str(e)
            }

    def rebuild_knowledge_base(
            self,
            vector_db=None,
            force: bool = False,
            clear_all: bool = False
    ) -> Dict[str, Any]:
        """
        重建知识库
        
        功能：
        1. (可选) 完全清空向量数据库
        2. 获取所有活跃的知识库文件
        3. 删除旧的向量数据
        4. 重新处理文件并生成新的向量数据（包含完整metadata）
        5. 更新数据库记录
        
        Args:
            vector_db: 向量数据库实例
            force: 是否强制重建（即使文件已有向量数据）
            clear_all: 是否完全清空向量数据库（包括孤儿数据）
            
        Returns:
            重建结果信息
        """
        try:
            if not vector_db:
                return {
                    'success': False,
                    'message': '向量数据库未初始化',
                    'error': 'vector_db_not_initialized'
                }

            start_time = self.performance_monitor.start_timer()
            
            # 如果需要完全清空向量数据库
            if clear_all:
                logger.info("开始清空向量数据库...")
                try:
                    # 获取所有文档ID并删除
                    # 检查是否是 SQLiteVectorStore
                    actual_db = getattr(vector_db, '_vector_db', vector_db)
                    if hasattr(actual_db, 'get_all'):
                        # SQLiteVectorStore 路径
                        all_data = actual_db.get_all(include=['ids'])
                    else:
                        # ChromaDB 路径
                        all_data = vector_db.get()
                    
                    if all_data and 'ids' in all_data:
                        all_ids = all_data['ids']
                        if all_ids:
                            logger.info(f"找到{len(all_ids)}个向量数据，开始清空...")
                            vector_db.delete(ids=all_ids)
                            logger.info("向量数据库已完全清空")
                except Exception as clear_error:
                    logger.warning(f"清空向量数据库失败: {clear_error}")
                    # 继续执行，不中断重建流程
            
            # 导入必要的模块
            from models.models import RagFileRecord, db
            from flask import current_app
            import ast
            
            logger.info("开始重建知识库...")
            
            # 获取所有活跃的知识库文件
            files = RagFileRecord.query.filter(
                RagFileRecord.status == 'active'
            ).all()
            
            if not files:
                return {
                    'success': True,
                    'message': '知识库为空，无需重建',
                    'info': {
                        'total_files': 0,
                        'processed': 0,
                        'failed': 0
                    }
                }
            
            logger.info(f"找到{len(files)}个知识库文件，开始重建...")
            
            processed_count = 0
            failed_count = 0
            failed_files = []
            
            for file_record in files:
                try:
                    logger.info(f"处理文件: {file_record.file_name} (ID: {file_record.id})")
                    
                    # 构建文件完整路径
                    upload_folder = current_app.config.get('UPLOAD_FOLDER', '')
                    file_path = Path(upload_folder) / file_record.file_path
                    
                    if not file_path.exists():
                        logger.warning(f"文件不存在，跳过: {file_path}")
                        failed_count += 1
                        failed_files.append({
                            'id': file_record.id,
                            'name': file_record.file_name,
                            'reason': '文件不存在'
                        })
                        continue
                    
                    # 删除旧的向量数据
                    if file_record.ids:
                        try:
                            old_ids = ast.literal_eval(file_record.ids)
                            if isinstance(old_ids, list) and old_ids:
                                logger.debug(f"删除旧向量数据: {len(old_ids)}个文档块")
                                # ChromaDB的删除方法
                                try:
                                    vector_db.delete(ids=old_ids)
                                except Exception as delete_error:
                                    logger.warning(f"删除旧向量数据失败: {delete_error}")
                        except (ValueError, SyntaxError, AttributeError) as e:
                            logger.warning(f"解析旧文档ID失败: {e}")
                    
                    # 重新处理文件
                    result = self.process_knowledge_file(
                        file_path=str(file_path),
                        vector_db=vector_db
                    )
                    
                    if result['success']:
                        # 更新数据库记录
                        file_record.ids = str(result['document_ids'])
                        db.session.commit()
                        
                        processed_count += 1
                        logger.info(f"成功重建文件: {file_record.file_name}, "
                                  f"生成{len(result['document_ids'])}个文档块")
                    else:
                        failed_count += 1
                        failed_files.append({
                            'id': file_record.id,
                            'name': file_record.file_name,
                            'reason': result.get('message', '处理失败')
                        })
                        logger.error(f"重建文件失败: {file_record.file_name}, "
                                   f"原因: {result.get('message')}")
                
                except Exception as file_error:
                    failed_count += 1
                    failed_files.append({
                        'id': file_record.id,
                        'name': file_record.file_name,
                        'reason': str(file_error)
                    })
                    logger.error(f"处理文件异常: {file_record.file_name}, 错误: {file_error}")
                    continue
            
            # 记录性能指标
            elapsed_time = self.performance_monitor.end_timer(start_time)
            
            rebuild_info = {
                'total_files': len(files),
                'processed': processed_count,
                'failed': failed_count,
                'failed_files': failed_files,
                'rebuild_time': float(elapsed_time),
                'force': force
            }
            
            success_rate = (processed_count / len(files) * 100) if files else 0
            
            logger.info(f"知识库重建完成！总文件数: {len(files)}, "
                       f"成功: {processed_count}, 失败: {failed_count}, "
                       f"成功率: {success_rate:.1f}%, 耗时: {elapsed_time:.2f}秒")
            
            return {
                'success': True,
                'message': f'知识库重建完成！成功处理{processed_count}个文件，失败{failed_count}个',
                'info': rebuild_info
            }

        except Exception as e:
            logger.error(f"知识库重建失败: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'知识库重建失败: {str(e)}',
                'error': str(e)
            }

    @staticmethod
    def _calculate_relevance(score: float) -> str:
        """计算相关性等级"""
        if score >= 0.9:
            return 'critical'
        elif score >= 0.8:
            return 'high'
        elif score >= 0.7:
            return 'medium'
        else:
            return 'low'

    @staticmethod
    def enrich_search_results_with_file_info(search_results: List[Dict[str, Any]], app=None) -> List[Dict[str, Any]]:
        """
        为搜索结果补充文件信息（需要在应用上下文中调用）
        
        Args:
            search_results: 搜索结果列表
            app: Flask应用实例（可选）
            
        Returns:
            补充文件信息后的搜索结果列表
        """
        try:
            logger.info(f"开始补充文件信息，共{len(search_results)}个搜索结果")
            
            # 如果metadata为空，尝试通过文档内容查找文件
            from utils.utils_core.common_utils import clean_text
            
            for idx, result in enumerate(search_results):
                metadata = result.get('metadata', {}) or {}
                
                # 清理搜索结果内容，确保没有乱码
                if 'content' in result:
                    result['content'] = clean_text(result.get('content', ''))
                
                # 如果metadata为空或缺少source，尝试通过内容查找
                if not metadata.get('source') or not metadata.get('file_name'):
                    # 通过文档内容在文件中查找
                    content = result.get('content', '')
                    
                    file_info = KnowledgeService._find_file_by_content(content, app=app)
                    if file_info:
                        logger.info(f"通过内容匹配找到文件: {file_info.get('file_name')}")
                        metadata.update({
                            'source': file_info.get('file_path', ''),
                            'file_name': file_info.get('file_name', '未知文件'),
                            'file_id': file_info.get('file_id')
                        })
                        result['metadata'] = metadata
                    else:
                        logger.warning(f"无法匹配文件，内容长度: {len(content)}")
                        # 即使找不到，也要确保metadata不为空
                        if not metadata:
                            metadata = {'file_name': '未知文件', 'source': ''}
                            result['metadata'] = metadata
            
            logger.info(f"文件信息补充完成")
            return search_results
            
        except Exception as e:
            logger.error(f"补充文件信息失败: {e}", exc_info=True)
            return search_results
    
    @staticmethod
    def _find_file_by_content(content: str, max_length: int = 300, app=None) -> Optional[Dict[str, Any]]:
        """
        通过文档内容片段查找对应的文件
        
        Args:
            content: 文档内容
            max_length: 用于匹配的内容长度
            app: Flask应用实例（可选，用于获取配置）
            
        Returns:
            文件信息字典，包含 file_id, file_name, file_path
        """
        try:
            
            # 获取应用实例
            try:
                application = app or current_app
            except RuntimeError:
                logger.warning("无Flask应用上下文，无法查找文件")
                return None
            
            # 获取内容的前N个字符用于匹配
            content_snippet = content[:max_length].strip()
            if not content_snippet:
                return None
            
            # 优化：使用更短的匹配字符串来提高匹配成功率
            # 去除可能的空白字符和换行符
            content_snippet = ' '.join(content_snippet.split())
            match_snippet = content_snippet[:100]  # 使用前100个字符进行匹配
            
            # 查询所有活跃的文件记录
            files = RagFileRecord.query.filter(
                RagFileRecord.status == 'active'
            ).all()
            
            # 尝试在文件内容中查找匹配
            for file_record in files:
                if not file_record.file_path:
                    continue
                
                try:
                    # 读取文件内容（部分）进行匹配
                    upload_folder = application.config.get('UPLOAD_FOLDER', '')
                    full_path = Path(upload_folder) / file_record.file_path
                    
                    if not full_path.exists():
                        continue
                    
                    # 读取文件前N个字符进行匹配
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        # 读取足够的内容用于匹配（读取整个文件或前10KB）
                        file_content = f.read(10000)
                    
                    # 标准化文件内容（去除多余空白）
                    normalized_file_content = ' '.join(file_content.split())
                    
                    # 检查搜索内容是否在文件中（支持部分匹配）
                    if match_snippet in normalized_file_content or content_snippet[:50] in file_content:
                        # 提取文件名
                        file_name = Path(file_record.file_path).name
                        logger.info(f"内容匹配成功: 文件 {file_name}")
                        return {
                            'file_id': file_record.id,
                            'file_name': file_name,
                            'file_path': file_record.file_path
                        }
                        
                except (IOError, OSError, UnicodeDecodeError, FileNotFoundError, PermissionError) as e:
                    # 记录文件读取错误，但继续处理其他文件
                    logger.warning(f"读取文件失败: {file_record.file_name} - {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"通过内容查找文件失败: {e}", exc_info=True)
            return None
    
    
    @staticmethod
    def _get_document_by_id(doc_id: str, vector_db) -> Optional[str]:
        """根据ID获取文档内容"""
        try:
            if not vector_db:
                return None
                
            # 从向量数据库获取文档
            result = vector_db.get(ids=[doc_id])
            
            if result and 'documents' in result and result['documents']:
                return result['documents'][0]
            else:
                return None
                
        except Exception as e:
            logger.error(f"获取文档{doc_id}失败: {e}")
            return None

    @staticmethod
    def _get_multiple_documents_by_id(doc_id: str, vector_db, max_chunks: int = 5) -> Optional[str]:
        """根据ID获取多个文档块内容"""
        try:
            if not vector_db:
                return None
                
            # 从向量数据库获取文档
            result = vector_db.get(ids=[doc_id])
            
            if result and 'documents' in result and result['documents']:
                # 获取第一个文档块
                first_chunk = result['documents'][0]
                
                # 尝试获取更多相关的文档块
                # 这里我们使用一个简单的策略：获取同一文档的其他块
                try:
                    # 获取所有文档，然后筛选出相关的块
                    # 检查是否是 SQLiteVectorStore
                    actual_db = getattr(vector_db, '_vector_db', vector_db)
                    meta_key = 'metadata' + 's'  # ChromaDB/SQLiteVectorStore API collection field
                    if hasattr(actual_db, 'get_all'):
                        # SQLiteVectorStore 路径
                        all_docs = actual_db.get_all(include=['documents', meta_key])
                    else:
                        # ChromaDB 路径
                        all_docs = vector_db.get()

                    if all_docs and 'documents' in all_docs and meta_key in all_docs:
                        documents = all_docs['documents']
                        metadata_list = all_docs[meta_key]
                        
                        # 找到与当前文档相关的其他块
                        related_chunks = []
                        for i, metadata in enumerate(metadata_list):
                            if metadata and 'source' in metadata:
                                # 如果来源相同，认为是同一文档的其他块
                                if metadata['source'] == first_chunk.get('source', ''):
                                    related_chunks.append(documents[i])
                                    if len(related_chunks) >= max_chunks:
                                        break
                        
                        # 合并所有相关块
                        if related_chunks:
                            combined_content = '\n\n'.join([chunk for chunk in related_chunks if chunk])
                            return combined_content
                        else:
                            return first_chunk
                    else:
                        return first_chunk
                except Exception as e:
                    logger.warning(f"获取相关文档块失败: {e}")
                    return first_chunk
            else:
                return None
                
        except Exception as e:
            logger.error(f"获取文档{doc_id}失败: {e}")
            return None

    @staticmethod
    def get_knowledge_statistics(vector_db=None) -> Dict[str, Any]:
        """获取知识库统计信息"""
        try:
            if not vector_db:
                return {
                    'success': False,
                    'message': '向量数据库未初始化',
                    'error': 'vector_db_not_initialized'
                }

            stats = {
                'total_documents': 0,
                'total_chunks': 0,
                'database_size': 0,
                'last_updated': None
            }

            return {
                'success': True,
                'statistics': stats
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'知识库统计失败: {str(e)}',
                'error': str(e)
            }
