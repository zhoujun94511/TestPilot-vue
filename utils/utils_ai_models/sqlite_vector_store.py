#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
SQLite + sqlite-vec 向量存储实现
替换 ChromaDB，使用 SQLite 单文件数据库 + sqlite-vec 扩展
"""
import os
import sqlite3
import json
import threading
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

# 尝试导入 Document（兼容不同版本的 langchain）
try:
    from langchain_core.documents import Document
except ImportError:
    try:
        from langchain.schema import Document
    except ImportError:
        try:
            from langchain.documents import Document
        except ImportError:
            # 如果都失败，定义一个简单的 Document 类作为 fallback
            from typing import Dict, Any, Optional
            class Document:
                """Document 类（fallback）"""
                def __init__(self, page_content: str, metadata: Optional[Dict[str, Any]] = None):
                    self.page_content = page_content
                    self.metadata = metadata or {}
from utils.utils_core.logger import get_logger
from config.settings import settings
from utils.utils_ai_models.embedding_manager import get_embedding_manager

logger = get_logger(__name__)


class SQLiteVectorStore:
    """
    SQLite + sqlite-vec 向量存储实现
    
    接口与 Chroma 保持一致，支持：
    - add_documents()
    - similarity_search()
    - similarity_search_with_score()
    - delete()
    - get()
    """
    
    def __init__(self, db_path: Optional[str] = None, embedding_function=None):
        """
        初始化 SQLite 向量存储
        
        Args:
            db_path: SQLite 数据库文件路径，如果为 None 则使用默认路径
            embedding_function: Embedding 函数（LangChain 接口），如果为 None 则使用默认
        """
        # 数据库路径
        if db_path is None:
            # 使用与 ChromaDB 相同的目录，但文件名不同
            vector_store_dir = Path(settings.VECTOR_STORE_DIR)
            vector_store_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(vector_store_dir / 'vector_store.db')
        else:
            self.db_path = db_path
        
        # Embedding 函数（LangChain 接口）
        if embedding_function is None:
            from utils.utils_ai_models.embeddings import get_embeddings
            self.embedding_function = get_embeddings()
        else:
            self.embedding_function = embedding_function
        
        # Embedding 管理器（用于获取维度）
        # 如果传入了 embedding_function，则不初始化真实的 embedding_manager（用于测试）
        if embedding_function is None:
            self.embedding_manager = get_embedding_manager()
        else:
            # 测试环境：不初始化真实的 embedding_manager
            self.embedding_manager = None
        self.embedding_dim = settings.EMBEDDING_DIM
        
        # 线程锁
        self._lock = threading.RLock()
        
        # sqlite-vec 索引可用标志（在初始化时设置）
        self._vec_index_available = False
        
        # FTS5 全文索引可用标志（在初始化时设置）
        self._fts5_available = False
        
        # 初始化数据库
        self._initialize_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接（线程安全）"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # 返回字典式行对象
        return conn
    
    def _load_sqlite_vec_extension(self, conn: sqlite3.Connection):
        """
        加载 sqlite-vec 扩展
        
        Args:
            conn: SQLite 连接
            
        Raises:
            RuntimeError: 如果无法加载扩展
        """
        try:
            # 启用扩展加载权限（必需，否则会报 "not authorized" 错误）
            extension_loading_enabled = False
            try:
                conn.enable_load_extension(True)
                extension_loading_enabled = True
            except AttributeError:
                # 如果 SQLite 构建时未启用扩展支持，此方法可能不存在
                logger.warning("SQLite 不支持扩展加载（可能是在没有扩展支持的情况下编译的）")
            except Exception as e:
                logger.warning(f"启用扩展加载权限失败: {e}")
            
            # 如果无法启用扩展加载，直接进入 fallback 流程
            if not extension_loading_enabled:
                logger.warning("无法启用扩展加载权限，将使用降级模式（全表扫描）")
                return
            
            extension_loaded = False
            
            # 方法1: 使用环境变量指定的路径
            if settings.SQLITE_VEC_EXTENSION_PATH:
                ext_path = settings.SQLITE_VEC_EXTENSION_PATH
                if os.path.exists(ext_path):
                    try:
                        conn.load_extension(ext_path)
                        logger.info(f"成功加载 sqlite-vec 扩展: {ext_path}")
                        extension_loaded = True
                    except Exception as e:
                        logger.warning(f"从指定路径加载扩展失败: {e}")
            
            # 方法2: 尝试从常见位置加载
            if not extension_loaded:
                import platform
                system = platform.system()
                
                # 根据平台构建可能的扩展路径列表
                if system == "Windows":
                    possible_paths = [
                        os.path.join(os.path.dirname(__file__), '..', '..', 'sqlite-vec', 'vec0.dll'),
                        'vec0.dll',
                    ]
                else:
                    possible_paths = [
                        os.path.join(os.path.dirname(__file__), '..', '..', 'sqlite-vec', 'vec0.so'),
                        '/usr/local/lib/vec0.so',
                        '/usr/lib/vec0.so',
                        'vec0.so',
                    ]
                
                for ext_path in possible_paths:  # noqa: B007
                    if os.path.exists(ext_path):
                        try:
                            conn.load_extension(ext_path)
                            logger.info(f"成功加载 sqlite-vec 扩展: {ext_path}")
                            extension_loaded = True
                            break
                        except Exception as e:
                            logger.debug(f"尝试加载扩展失败 {ext_path}: {e}")
                            continue
            
            # 方法3: 尝试使用 Python 包（如果 sqlite-vec 提供）
            if not extension_loaded:
                try:
                    import sqlite_vec  # noqa: F401, PLC0415
                    # sqlite-vec Python 包可能提供自动加载机制
                    # 根据实际包实现，可能需要调用特定方法
                    if hasattr(sqlite_vec, 'load'):
                        sqlite_vec.load(conn)
                        extension_loaded = True
                except (ImportError, AttributeError):
                    pass
            
            # 验证扩展是否加载成功
            if not extension_loaded:
                # 尝试直接使用 SQL 函数验证（可能已预加载）
                try:
                    # sqlite-vec 可能提供的函数：vec_version, vec0, vec_distance 等
                    test_queries = [
                        "SELECT vec_version()",
                        "SELECT sqlite_version()",  # 至少验证 SQLite 可用
                    ]
                    for query in test_queries:
                        try:
                            conn.execute(query).fetchone()
                            if "vec_version" in query:
                                logger.info("sqlite-vec 扩展已可用（可能已预加载）")
                                extension_loaded = True
                                break
                        except sqlite3.OperationalError:
                            continue
                except (ImportError, AttributeError, OSError):
                    pass
            
            if not extension_loaded:
                error_msg = (
                    f"❌ 无法加载 sqlite-vec 扩展\n"
                    f"   数据库路径: {self.db_path}\n"
                    f"\n"
                    f"⚠️ 解决方法：\n"
                    f"   1. 安装 sqlite-vec 扩展\n"
                    f"   2. 设置环境变量 SQLITE_VEC_EXTENSION_PATH 指定扩展路径\n"
                    f"   3. 确保扩展文件可访问\n"
                    f"\n"
                    f"⚠️ 注意：当前实现使用全表扫描 + 手动计算距离（性能较差）\n"
                    f"   生产环境应使用 sqlite-vec 的索引搜索以获得最佳性能"
                )
                logger.error(error_msg)
                # 不抛出异常，允许降级到全表扫描模式
                logger.warning("将使用降级模式（全表扫描），性能可能较差")
            
        except Exception as e:
            logger.error(f"加载 sqlite-vec 扩展失败: {e}", exc_info=True)
            logger.warning("将使用降级模式（全表扫描），性能可能较差")
    
    def _initialize_database(self):
        """初始化数据库表结构（幂等）"""
        with self._lock:
            conn = self._get_connection()
            try:
                # 加载 sqlite-vec 扩展
                self._load_sqlite_vec_extension(conn)
                
                # 创建表（使用 IF NOT EXISTS 确保幂等）
                
                # documents 表：存储文档元数据
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id TEXT PRIMARY KEY,
                        content TEXT,
                        metadata TEXT  -- JSON 字符串
                    )
                """)
                
                # chunks 表：存储文档块
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS chunks (
                        id TEXT PRIMARY KEY,
                        document_id TEXT,
                        content TEXT,
                        metadata TEXT,  -- JSON 字符串
                        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                    )
                """)
                
                # chunk_embeddings 表：存储向量（使用 sqlite-vec）
                # 注意：sqlite-vec 使用特殊的向量列类型
                conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS chunk_embeddings (
                        chunk_id TEXT PRIMARY KEY,
                        embedding BLOB,  -- float32 buffer
                        FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
                    )
                """)
                
                # 创建 sqlite-vec 向量索引（vec0 虚拟表）
                # sqlite-vec 使用虚拟表进行向量索引和搜索
                # DDL: CREATE VIRTUAL TABLE ... USING vec0(...)
                try:
                    # 测试 sqlite-vec 是否可用
                    try:
                        conn.execute("SELECT vec_version()").fetchone()
                    except sqlite3.OperationalError:
                        # 如果 vec_version() 不可用，尝试其他方式验证
                        pass
                    
                    # 创建 vec0 虚拟表作为向量索引
                    # 语法：CREATE VIRTUAL TABLE vec_index USING vec0(embedding float32[dim])
                    # 注意：sqlite-vec 的语法可能因版本而异，这里使用常见格式
                    vec_index_ddl = f"""
                        CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embedding_index
                        USING vec0(
                            chunk_id TEXT PRIMARY KEY,
                            embedding float32[{self.embedding_dim}]
                        )
                    """
                    
                    # 尝试创建虚拟表
                    conn.execute(vec_index_ddl)
                    self._vec_index_available = True
                    
                except sqlite3.OperationalError as e:
                    # 如果虚拟表创建失败，可能是语法不同或扩展不可用
                    error_msg = str(e).lower()
                    
                    # 尝试替代语法（某些版本的 sqlite-vec 可能使用不同语法）
                    try:
                        # 替代语法1：不使用维度声明
                        vec_index_ddl_alt1 = """
                            CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embedding_index
                            USING vec0(chunk_id, embedding)
                        """
                        conn.execute(vec_index_ddl_alt1)
                        self._vec_index_available = True
                    except sqlite3.OperationalError:
                        try:
                            # 替代语法2：使用不同的列定义方式
                            vec_index_ddl_alt2 = f"""
                                CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embedding_index
                                USING vec0(
                                    rowid,
                                    embedding float32[{self.embedding_dim}]
                                )
                            """
                            conn.execute(vec_index_ddl_alt2)
                            self._vec_index_available = True
                        except sqlite3.OperationalError as e2:
                            # 所有语法都失败，使用降级模式
                            self._vec_index_available = False
                            logger.warning(
                                f"⚠️ 无法创建 sqlite-vec 向量索引: {e2}\n"
                                f"   将使用全表扫描模式（性能较差）\n"
                                f"   错误详情: {error_msg}"
                            )
                except Exception as e:
                    # 其他异常，使用降级模式
                    self._vec_index_available = False
                    logger.warning(f"⚠️ 创建 sqlite-vec 向量索引时发生异常: {e}\n"
                                 f"   将使用全表扫描模式（性能较差）")
                
                # 创建普通索引
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chunks_document_id 
                    ON chunks(document_id)
                """)
                
                # 创建 FTS5 全文索引（用于关键词召回）
                # FTS5 是 SQLite 内置的全文搜索模块，无需额外扩展
                try:
                    conn.execute("""
                        CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts
                        USING fts5(
                            chunk_id UNINDEXED,
                            content,
                            tokenize = 'porter unicode61'
                        )
                    """)
                    self._fts5_available = True
                except sqlite3.OperationalError as e:
                    # FTS5 是 SQLite 内置功能，通常不会失败
                    # 如果失败，可能是 SQLite 版本不支持 FTS5
                    self._fts5_available = False
                    logger.warning(f"⚠️ 无法创建 FTS5 全文索引: {e}\n"
                                 f"   将禁用混合检索，仅使用纯向量检索")
                
                conn.commit()
                
            except Exception as e:
                conn.rollback()
                logger.error(f"初始化数据库失败: {e}", exc_info=True)
                raise
            finally:
                conn.close()
    
    @staticmethod
    def _calculate_adaptive_fts_candidate_k(
        top_k: int,
        query: str,
        base_factor: int = None,
        max_candidate_k: int = None
    ) -> int:
        """
        计算自适应 FTS5 候选数量
        
        ⚠️ 自适应策略设计意图：
        1. 基础策略：fts_candidate_k = min(topK * factor, MAX_FTS_CANDIDATE_K)
        2. Query 复杂度调节：根据 query token 数动态调整 factor
        3. 安全约束：所有候选数量必须 ≤ SQLite IN 参数安全上限
        
        Args:
            top_k: 最终返回结果数量（k 参数）
            query: 查询文本
            base_factor: 基础因子（如果为 None，从配置读取）
            max_candidate_k: 候选数量上限（如果为 None，从配置读取）
            
        Returns:
            计算得到的 FTS5 候选数量
        """
        if base_factor is None:
            base_factor = settings.FTS_CANDIDATE_FACTOR
        if max_candidate_k is None:
            max_candidate_k = settings.MAX_FTS_CANDIDATE_K
        
        # 2️⃣ Query 复杂度调节：根据 query token 数动态调整 factor
        # 简单查询（token <= 2）：扩大召回范围（factor *= 2）
        # 复杂查询（token >= 8）：缩小召回范围（factor = max(10, factor // 2)）
        query_tokens = len(query.split())
        
        if query_tokens <= 2:
            # 简单查询：扩大召回范围，避免遗漏
            adjusted_factor = base_factor * 2
            fts_candidate_k = top_k * adjusted_factor
        elif query_tokens >= 8:
            # 复杂查询：缩小召回范围，减少算力浪费
            adjusted_factor = max(10, base_factor // 2)
            fts_candidate_k = top_k * adjusted_factor
        else:
            # 中等复杂度查询：使用基础 factor
            fts_candidate_k = top_k * base_factor
        
        # 3️⃣ 安全约束：所有候选数量必须 ≤ MAX_FTS_CANDIDATE_K
        # 同时考虑 SQLite IN 参数安全上限（999，但留出安全余量）
        sqlite_safe_limit = 800  # 留出安全余量（考虑其他参数）
        final_candidate_k = min(fts_candidate_k, max_candidate_k, sqlite_safe_limit)
        
        return final_candidate_k
    
    @staticmethod
    def _escape_fts5_query(query: str) -> str:
        """
        转义 FTS5 查询中的特殊字符
        
        FTS5 特殊字符包括：-、#、:、*、^、+、@、等
        对于包含特殊字符的查询，使用短语搜索（双引号包裹）是最可靠的方式
        
        Args:
            query: 原始查询文本
            
        Returns:
            转义后的查询文本
        """
        if not query:
            return query
        
        import re
        
        # FTS5 特殊字符完整列表
        # 运算符：AND、OR、NOT、NEAR、^（优先级）、*（前缀）
        # 特殊字符：-、#、:、[、]、{、}、(、)、"、+、@
        # 策略：对所有包含特殊字符或看起来不像简单关键词的查询，使用短语搜索
        
        # 1. 如果查询已经被引号包裹，直接返回（用户可能已经手动处理）
        if query.startswith('"') and query.endswith('"'):
            return query
        
        # 2. 检测是否包含FTS5特殊字符
        # 扩展特殊字符列表，包括所有可能导致解析错误的字符
        special_chars_pattern = r'[#\-:\[\]{}()\*\^"\+@]'
        
        # 3. 检测是否包含FTS5保留操作符（不区分大小写）
        reserved_operators = ['AND', 'OR', 'NOT', 'NEAR']
        query_upper = query.upper()
        has_operator = any(op in query_upper for op in reserved_operators)
        
        # 4. 如果包含特殊字符或操作符，使用短语搜索
        if re.search(special_chars_pattern, query) or has_operator:
            # 使用短语搜索：将整个查询用双引号包裹
            # FTS5 中，双引号内的内容会被视为短语，特殊字符会被当作普通字符处理
            # 如果查询本身包含双引号，需要转义为两个双引号
            escaped = query.replace('"', '""')
            return f'"{escaped}"'
        
        # 5. 对于简单的关键词查询，直接返回
        return query
    
    @staticmethod
    def _embedding_to_buffer(embedding: List[float]) -> bytes:
        """
        将 embedding 转换为 float32 buffer
        
        Args:
            embedding: List[float] 向量
            
        Returns:
            float32 buffer (bytes)
        """
        # 转换为 numpy array，然后转为 float32 buffer
        arr = np.array(embedding, dtype=np.float32)
        return arr.tobytes()
    
    @staticmethod
    def _buffer_to_embedding(buffer: bytes) -> List[float]:
        """
        将 float32 buffer 转换为 embedding
        
        Args:
            buffer: float32 buffer (bytes)
            
        Returns:
            List[float] 向量
        """
        # 从 buffer 恢复 numpy array
        arr = np.frombuffer(buffer, dtype=np.float32)
        return arr.tolist()
    
    def add_documents(self, documents: List[Document], **kwargs):  # noqa: ARG002, D102
        """
        添加文档到向量存储
        
        Args:
            documents: Document 列表
            **kwargs: 其他参数（保留兼容性）
        """
        _ = kwargs  # 保留参数以保持接口兼容性
        if not documents:
            return []  # 返回空列表而不是 None
        
        with self._lock:
            conn = self._get_connection()
            try:
                # 批量处理：先收集所有数据，然后批量插入
                chunks_to_insert = []
                embeddings_to_insert = []
                chunk_ids = []  # 收集所有 chunk_id，用于返回
                
                for doc in documents:
                    # 确保 doc 有 metadata
                    if not hasattr(doc, 'metadata') or doc.metadata is None:
                        doc.metadata = {}
                    
                    # 生成 chunk_id（使用文档的 id 或自动生成）
                    chunk_id = doc.metadata.get('chunk_id') or doc.metadata.get('id')
                    if not chunk_id:
                        # 如果没有 id，使用内容哈希生成
                        import hashlib
                        chunk_id = f"chunk_{hashlib.md5(doc.page_content.encode()).hexdigest()[:16]}"
                    
                    # 收集 chunk_id 用于返回
                    chunk_ids.append(chunk_id)
                    
                    document_id = doc.metadata.get('document_id') or doc.metadata.get('source', 'unknown')
                    
                    # 如果没有 document_id，创建文档记录
                    # 注意：documents 表存储完整文档内容（可能很长），这里只存储前1000字符作为预览
                    conn.execute("""
                        INSERT OR IGNORE INTO documents (id, content, metadata)
                        VALUES (?, ?, ?)
                    """, (document_id, doc.page_content[:1000], json.dumps(doc.metadata)))
                    
                    # 准备 chunk 数据
                    chunks_to_insert.append((
                        chunk_id,
                        document_id,
                        doc.page_content,
                        json.dumps(doc.metadata)
                    ))
                    
                    # 生成 embedding（使用 embed_documents 以支持批量）
                    # 注意：embed_query 用于单个查询，embed_documents 用于批量文档
                    # 这里每个 doc 单独处理，可以优化为批量处理
                    try:
                        # 使用 embed_documents 支持批量（但当前是逐个处理）
                        embeddings_list = self.embedding_function.embed_documents([doc.page_content])
                        embedding = embeddings_list[0] if embeddings_list else []
                    except Exception as e:
                        logger.warning(f"批量 embedding 失败，降级到单个处理: {e}")
                        embedding = self.embedding_function.embed_query(doc.page_content)
                    
                    # 验证 embedding 维度
                    if len(embedding) != self.embedding_dim:
                        raise ValueError(
                            f"Embedding 维度不匹配: 期望 {self.embedding_dim}, 实际 {len(embedding)}"
                        )
                    
                    embedding_buffer = self._embedding_to_buffer(embedding)
                    
                    embeddings_to_insert.append((
                        chunk_id,
                        embedding_buffer
                    ))
                
                # 批量插入 chunks
                conn.executemany("""
                    INSERT OR REPLACE INTO chunks (id, document_id, content, metadata)
                    VALUES (?, ?, ?, ?)
                """, chunks_to_insert)
                
                # 批量插入 embeddings（原始 buffer，保留用于兼容性）
                conn.executemany("""
                    INSERT OR REPLACE INTO chunk_embeddings (chunk_id, embedding)
                    VALUES (?, ?)
                """, embeddings_to_insert)
                
                # 批量插入 sqlite-vec 向量索引（如果可用）
                # ⚠️ 工程认知：现在直接使用 chunk_embeddings 表 + vec_distance_cosine 函数
                # 这避免了 MATCH 语法的兼容性问题
                # chunk_embeddings 表已经存储了向量数据（bytes buffer格式）
                # 查询时直接对这个表使用 vec_distance_cosine 函数即可
                # 注：不再需要维护单独的 chunk_embedding_index 虚拟表
                
                # 批量插入 FTS5 全文索引（如果可用）
                if self._fts5_available:
                    try:
                        # 准备 FTS5 数据（chunk_id 和 content）
                        fts5_data = [(chunk_id, content) for chunk_id, _, content, _ in chunks_to_insert]
                        
                        # 插入 FTS5 索引
                        conn.executemany("""
                            INSERT OR REPLACE INTO chunk_fts (chunk_id, content)
                            VALUES (?, ?)
                        """, fts5_data)
                        logger.debug(f"✅ 成功写入 {len(fts5_data)} 个文档到 FTS5 全文索引")
                    except Exception as e:
                        # 如果 FTS5 写入失败，记录警告但不中断流程
                        logger.warning(f"⚠️ 写入 FTS5 全文索引失败: {e}")
                        # 标记 FTS5 不可用，后续查询将禁用混合检索
                        self._fts5_available = False
                
                conn.commit()
                logger.info(f"成功添加 {len(documents)} 个文档到向量存储")
                
                # 返回 chunk_id 列表（兼容 ChromaDB API）
                logger.debug(f"add_documents 返回 {len(chunk_ids)} 个 ID: {chunk_ids[:5] if chunk_ids else '[]'}...")
                return chunk_ids
                
            except Exception as e:
                conn.rollback()
                logger.error(f"添加文档失败: {e}", exc_info=True)
                raise
            finally:
                conn.close()
    
    def similarity_search(self, query: str, k: int = 4, **kwargs) -> List[Document]:  # noqa: ARG002
        """
        相似度搜索（不带分数）
        
        Args:
            query: 查询文本
            k: 返回结果数量
            **kwargs: 其他参数（如 filter，当前版本简化处理）
            
        Returns:
            Document 列表
        """
        results_with_scores = self.similarity_search_with_score(query, k=k, **kwargs)
        # 只返回 Document，不返回分数
        return [doc for doc, score in results_with_scores]
    
    def similarity_search_with_score(  # noqa: ARG002
        self, 
        query: str, 
        k: int = 4, 
        **kwargs
    ) -> List[Tuple[Document, float]]:
        """
        相似度搜索（带分数）
        
        Args:
            query: 查询文本
            k: 返回结果数量
            **kwargs: 其他参数（如 filter，当前版本简化处理）
            
        Returns:
            (Document, similarity_score) 元组列表
            similarity_score ∈ [0, 1]，越大越相似
        """
        _ = kwargs  # 保留参数以保持接口兼容性
        with self._lock:
            conn = self._get_connection()
            try:
                # 生成查询向量
                query_embedding = self.embedding_function.embed_query(query)
                
                # 混合检索流程：FTS5 → sqlite-vec
                # 第一阶段：FTS5 召回候选 chunk_ids（如果启用混合检索）
                candidate_chunk_ids = None
                if settings.ENABLE_HYBRID_RETRIEVAL and self._fts5_available:
                    try:
                        # ⚠️ 自适应候选策略：根据 topK 和 query 复杂度动态计算候选数量
                        # 策略设计：
                        # 1. 基础策略：fts_candidate_k = min(topK * factor, MAX_FTS_CANDIDATE_K)
                        # 2. Query 复杂度调节：根据 query token 数动态调整 factor
                        # 3. FTS 命中率修正：若实际命中 < topK → 不裁剪；若命中过多 → 裁剪
                        # 4. 安全约束：所有候选数量必须 ≤ SQLite IN 参数安全上限
                        
                        # 计算自适应候选数量
                        adaptive_candidate_k = self._calculate_adaptive_fts_candidate_k(
                            top_k=k,
                            query=query
                        )
                        
                        # 转义 FTS5 特殊字符（#、-、:、等）
                        # FTS5 特殊字符需要转义或用引号包裹
                        fts_query = self._escape_fts5_query(query)

                        fts_results = conn.execute("""
                            SELECT chunk_id
                            FROM chunk_fts
                            WHERE chunk_fts MATCH ?
                            LIMIT ?
                        """, (fts_query, adaptive_candidate_k)).fetchall()
                        
                        if fts_results:
                            candidate_chunk_ids = [row['chunk_id'] for row in fts_results]
                            actual_hit_count = len(candidate_chunk_ids)
                            
                            # 3️⃣ FTS 命中率修正（可选但推荐）
                            # 若 FTS 实际命中 < topK → 不裁剪（避免过度裁剪导致召回不足）
                            # 若命中过多 → 裁剪到 adaptive_candidate_k（已在 LIMIT 中处理）
                            if actual_hit_count < k:
                                logger.debug(
                                    f"📊 FTS5 命中率修正：实际命中 {actual_hit_count} < topK {k}，"
                                    f"保留所有命中结果（不裁剪）"
                                )
                                # 不裁剪，保留所有命中结果
                            else:
                                logger.debug(
                                    f"✅ FTS5 召回 {actual_hit_count} 个候选 chunk_ids "
                                    f"(自适应候选数量: {adaptive_candidate_k}, topK: {k})"
                                )
                        else:
                            # FTS5 返回为空，fallback 到纯向量检索
                            candidate_chunk_ids = None
                        
                        # ⚠️ 架构认知：FTS5 排名现在"没用"，但这是优势不是缺陷
                        # 当前设计：FTS 只负责召回，vec 负责排序
                        # 优势：不混用 ranking 信号，逻辑清晰
                        # 未来：如果要做"三阶段检索"（FTS → vec → rerank），
                        #       那时再引入 bm25(chunk_fts) 会更合理
                        
                        # ⚠️ 架构认知：FTS5 排名现在"没用"，但这是优势不是缺陷
                        # 当前设计：FTS 只负责召回，vec 负责排序
                        # 优势：不混用 ranking 信号，逻辑清晰
                        # 未来：如果要做"三阶段检索"（FTS → vec → rerank），
                        #       那时再引入 bm25(chunk_fts) 会更合理
                            
                    except Exception as fts_error:
                        # FTS5 查询失败，fallback 到纯向量检索
                        # 记录详细错误信息以便调试
                        error_msg = str(fts_error)
                        if 'unrecognized token' in error_msg:
                            # 特殊字符导致的解析错误（已经做了转义，但可能仍有问题）
                            logger.debug(
                                f"⚠️ FTS5 查询语法错误（特殊字符），fallback 到纯向量检索\n"
                                f"   原始查询: {query[:100]}\n"
                                f"   转义后查询: {fts_query[:100]}\n"
                                f"   错误: {error_msg}"
                            )
                        else:
                            # 其他类型的FTS5错误
                            logger.warning(
                                f"⚠️ FTS5 查询失败，fallback 到纯向量检索\n"
                                f"   查询: {query[:100]}\n"
                                f"   错误: {fts_error}"
                            )
                        candidate_chunk_ids = None
                
                # 第二阶段：sqlite-vec 向量检索（对候选集或全量）
                # 尝试使用 sqlite-vec 索引搜索（如果可用）
                if self._vec_index_available:
                    try:
                        # 确保扩展已加载（每次查询前都尝试加载，因为连接可能不同）
                        self._load_sqlite_vec_extension(conn)
                        
                        # ⚠️ 工程认知：sqlite-vec 的 MATCH 语法支持因版本而异
                        # 某些版本不支持 MATCH，需要使用函数式查询
                        # 优先尝试函数式查询（兼容性更好）
                        
                        # 准备查询向量（bytes buffer格式，性能更好）
                        query_buffer = self._embedding_to_buffer(query_embedding)
                        
                        # 方法1: 使用 vec_distance_cosine 函数（推荐，兼容性好）
                        try:
                            # 使用 bytes buffer 格式（与存储格式一致）
                            # 这避免了 MATCH 语法的兼容性问题
                            
                            # 如果启用混合检索且有候选集，则对候选集做向量检索
                            if candidate_chunk_ids is not None:
                                # 混合检索：对 FTS5 候选集做向量精排
                                # 从 chunk_embeddings 表读取候选集的向量
                                
                                # ⚠️ P0-1 修复：SQLite IN 参数上限（默认 999）
                                # 如果候选数量 >= 999，需要分批处理
                                sqlite_in_param_limit = 999
                                safe_batch_size = 800  # 留出安全余量（考虑其他参数）
                                
                                if len(candidate_chunk_ids) >= sqlite_in_param_limit:
                                    logger.warning(
                                        f"⚠️ FTS5 候选数量 ({len(candidate_chunk_ids)}) 超过或接近 SQLite IN 参数上限 ({sqlite_in_param_limit})，"
                                        f"将分批处理（批次大小: {safe_batch_size}）"
                                    )
                                    
                                    # 方案A：分批执行 + 合并排序
                                    all_batch_results = []
                                    for i in range(0, len(candidate_chunk_ids), safe_batch_size):
                                        batch_ids = candidate_chunk_ids[i:i + safe_batch_size]
                                        batch_placeholders = ','.join(['?'] * len(batch_ids))
                                        
                                        # 对每一批执行向量精排（不限制每批返回数量，后续统一排序）
                                        batch_results = conn.execute(f"""
                                            SELECT 
                                                ce.chunk_id,
                                                vec_distance_cosine(ce.embedding, ?) as distance
                                            FROM chunk_embeddings ce
                                            WHERE ce.chunk_id IN ({batch_placeholders})
                                        """, (query_buffer, *batch_ids)).fetchall()
                                        
                                        all_batch_results.extend(batch_results)
                                    
                                    # 合并所有批次结果，按 distance 排序，取 topK
                                    all_batch_results.sort(key=lambda x: x['distance'])
                                    results = all_batch_results[:k]
                                    
                                    logger.debug(
                                        f"✅ 混合检索（分批处理）："
                                        f"共 {len(candidate_chunk_ids)} 个FTS5候选，"
                                        f"分 {((len(candidate_chunk_ids) - 1) // safe_batch_size) + 1} 批处理，"
                                        f"返回 {len(results)} 个结果（请求: {k} 个）"
                                    )
                                else:
                                    # 候选数量 < 999，正常处理
                                    placeholders = ','.join(['?'] * len(candidate_chunk_ids))
                                    results = conn.execute(f"""
                                        SELECT 
                                            ce.chunk_id,
                                            vec_distance_cosine(ce.embedding, ?) as distance
                                        FROM chunk_embeddings ce
                                        WHERE ce.chunk_id IN ({placeholders})
                                        ORDER BY distance
                                        LIMIT ?
                                    """, (query_buffer, *candidate_chunk_ids, k)).fetchall()
                            else:
                                # 纯向量检索：对全量数据做向量搜索
                                results = conn.execute("""
                                    SELECT 
                                        ce.chunk_id,
                                        vec_distance_cosine(ce.embedding, ?) as distance
                                    FROM chunk_embeddings ce
                                    ORDER BY distance
                                    LIMIT ?
                                """, (query_buffer, k)).fetchall()
                            
                            # 如果成功，处理结果
                            if results:
                                chunk_ids = [row['chunk_id'] for row in results]
                                distances = [row['distance'] for row in results]
                                
                                # 获取对应的 chunks 数据
                                placeholders = ','.join(['?'] * len(chunk_ids))
                                chunks_data = conn.execute(f"""
                                    SELECT c.id, c.content, c.metadata
                                    FROM chunks c
                                    WHERE c.id IN ({placeholders})
                                """, chunk_ids).fetchall()
                                
                                # 组装结果
                                results_list: List[Tuple[Document, float]] = []
                                for row in chunks_data:
                                    chunk_id = row['id']
                                    content = row['content']
                                    metadata_json = row['metadata']
                                    
                                    # 找到对应的 distance
                                    idx = chunk_ids.index(chunk_id)
                                    distance = distances[idx]
                                    
                                    # 将 distance 转换为 similarity_score
                                    # ⚠️ P1-1 增强：明确映射假设
                                    # 
                                    # 假设：vec_distance_cosine 返回范围 [0, 2]
                                    #   - 0 = 完全相同（向量方向一致）
                                    #   - 2 = 完全相反（向量方向相反）
                                    # 
                                    # 映射公式：similarity = 1 - (distance / 2)
                                    #   - distance = 0 → similarity = 1.0（最相似）
                                    #   - distance = 2 → similarity = 0.0（最不相似）
                                    #   - 范围：similarity ∈ [0, 1]
                                    # 
                                    # TODO: 如果未来升级 sqlite-vec 版本，需要验证：
                                    #   1. vec_distance_cosine 的实际返回范围是否仍为 [0, 2]
                                    #   2. 如果范围变化，需要调整映射公式
                                    #   3. 建议在初始化时测试 distance 范围并记录日志
                                    similarity: float = max(0.0, 1.0 - float(distance) / 2.0)
                                    similarity = min(1.0, similarity)  # 确保 similarity ∈ [0, 1]
                                    
                                    # 解析 metadata
                                    try:
                                        metadata = json.loads(metadata_json) if metadata_json else {}
                                    except (json.JSONDecodeError, TypeError):
                                        metadata = {}
                                    
                                    results_list.append((
                                        Document(
                                            page_content=content,
                                            metadata=metadata
                                        ),
                                        similarity
                                    ))
                                
                                return results_list
                            # 如果 results 为空，继续执行到全表扫描（fallback）
                                
                        except sqlite3.OperationalError as func_error:
                            # vec_distance_cosine 函数不可用
                            logger.warning(
                                f"⚠️ sqlite-vec vec_distance_cosine 函数不可用\n"
                                f"   错误: {func_error}\n"
                                f"   可能原因: sqlite-vec 扩展未正确加载"
                            )
                            # 降级到全表扫描
                            self._vec_index_available = False
                            logger.warning("⚠️ 降级到全表扫描模式（纯 Python 计算）")
                    
                    except Exception as index_error:
                        # 其他未预料的错误
                        logger.warning(
                            f"⚠️ sqlite-vec 查询发生异常\n"
                            f"   错误: {index_error}"
                        )
                        # 降级到全表扫描
                        self._vec_index_available = False
                        logger.warning("⚠️ 降级到全表扫描模式")
                
                # Fallback: 全表扫描模式（如果索引不可用或查询失败）
                # 确保所有路径都有返回值
                logger.debug("使用全表扫描模式（降级实现）")
                
                all_embeddings = conn.execute("""
                    SELECT ce.chunk_id, ce.embedding, c.content, c.metadata
                    FROM chunk_embeddings ce
                    JOIN chunks c ON ce.chunk_id = c.id
                """).fetchall()
                
                # 计算相似度（余弦相似度）
                query_arr = np.array(query_embedding, dtype=np.float32)
                query_norm: float = float(np.linalg.norm(query_arr))
                
                similarities: List[Tuple[float, Document]] = []
                
                for row in all_embeddings:
                    embedding_buffer = row['embedding']
                    content = row['content']
                    metadata_json = row['metadata']
                    
                    # 从 buffer 恢复向量
                    embedding_arr = np.frombuffer(embedding_buffer, dtype=np.float32)
                    
                    # 计算余弦相似度
                    dot_product: float = float(np.dot(query_arr, embedding_arr))
                    embedding_norm: float = float(np.linalg.norm(embedding_arr))
                    
                    if query_norm > 0 and embedding_norm > 0:
                        cosine_similarity: float = dot_product / (query_norm * embedding_norm)
                        # 余弦相似度范围是 [-1, 1]，转换为 [0, 1] 的相似度分数
                        # 注意：全表扫描模式使用余弦相似度，与 sqlite-vec 的 distance 映射不同
                        # 但最终 similarity_score 范围一致：∈ [0, 1]
                        similarity: float = (cosine_similarity + 1.0) / 2.0
                        similarity = max(0.0, min(1.0, similarity))
                    else:
                        similarity: float = 0.0
                    
                    # 解析 metadata
                    try:
                        metadata = json.loads(metadata_json) if metadata_json else {}
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}
                    
                    similarities.append((
                        similarity,
                        Document(
                            page_content=content,
                            metadata=metadata
                        )
                    ))
                
                # 按相似度排序，取 top K
                similarities.sort(key=lambda x: x[0], reverse=True)
                results = similarities[:k]
                
                # 返回 (Document, similarity_score) 列表
                return [(doc, score) for score, doc in results]
                    
            except Exception as e:
                logger.error(f"相似度搜索失败: {e}", exc_info=True)
                raise
            finally:
                conn.close()
        
        # 保底返回（理论上不会执行到这里，但确保类型安全）
        return []
    
    def _verify_fts_chunks_consistency(self, conn: sqlite3.Connection) -> List[str]:
        """
        验证 FTS5 与 chunks 一致性（内部调试工具）
        
        ⚠️ 注意：此方法仅用于调试/日志/测试，不参与正常检索逻辑
        不要在每次查询时调用，仅在需要时（如 delete 后、测试时）调用
        
        Args:
            conn: SQLite 数据库连接
            
        Returns:
            所有存在于 chunk_fts 但不存在于 chunks 的 chunk_id 列表（幽灵数据）
            如果 FTS5 不可用或没有幽灵数据，返回空列表
        """
        if not self._fts5_available:
            return []
        
        try:
            # 使用 LEFT JOIN 检测幽灵数据
            orphan_fts = conn.execute("""
                SELECT cft.chunk_id
                FROM chunk_fts cft
                LEFT JOIN chunks c ON cft.chunk_id = c.id
                WHERE c.id IS NULL
            """).fetchall()
            
            orphan_ids = [row['chunk_id'] for row in orphan_fts]
            
            if orphan_ids:
                logger.warning(
                    f"⚠️ 发现 FTS5 中的幽灵数据（{len(orphan_ids)} 条）: "
                    f"{orphan_ids[:10]}{'...' if len(orphan_ids) > 10 else ''}"
                )
            
            return orphan_ids
            
        except Exception as e:
            # 不抛异常，只记录 warning（这是调试工具，不应影响主流程）
            logger.warning(f"验证 FTS5 一致性时发生异常: {e}")
            return []
    
    def delete(self, ids: Optional[List[str]] = None, **kwargs):  # noqa: ARG002, D102
        """
        删除文档
        
        Args:
            ids: chunk_id 列表
            **kwargs: 其他参数（保留兼容性）
        """
        _ = kwargs  # 保留参数以保持接口兼容性
        if not ids:
            return
        
        with self._lock:
            conn = self._get_connection()
            try:
                # 删除 embeddings
                placeholders = ','.join(['?'] * len(ids))
                conn.execute(f"""
                    DELETE FROM chunk_embeddings 
                    WHERE chunk_id IN ({placeholders})
                """, ids)
                
                # 注：不再使用 chunk_embedding_index 虚拟表
                # 查询直接使用 chunk_embeddings 表 + vec_distance_cosine 函数
                
                # 删除 FTS5 索引中的数据（如果可用）
                if self._fts5_available:
                    try:
                        conn.execute(f"""
                            DELETE FROM chunk_fts 
                            WHERE chunk_id IN ({placeholders})
                        """, ids)
                    except Exception as e:
                        logger.warning(f"删除 FTS5 索引数据失败: {e}")
                
                # 删除 chunks
                conn.execute(f"""
                    DELETE FROM chunks 
                    WHERE id IN ({placeholders})
                """, ids)
                
                # 删除孤立的 documents（没有关联的 chunks）
                conn.execute("""
                    DELETE FROM documents 
                    WHERE id NOT IN (SELECT DISTINCT document_id FROM chunks)
                """)
                
                conn.commit()
                logger.info(f"成功删除 {len(ids)} 个文档")
                
                # ⚠️ P0-2 修复：删除后验证 FTS5 一致性（仅调试/测试用）
                # 注意：此验证不影响主流程，仅用于发现潜在问题
                if self._fts5_available:
                    orphan_ids = self._verify_fts_chunks_consistency(conn)
                    if orphan_ids:
                        logger.warning(
                            f"⚠️ 删除后检测到 FTS5 幽灵数据（{len(orphan_ids)} 条），"
                            f"这可能是异常路径导致的，建议检查事务一致性"
                        )
                
            except Exception as e:
                conn.rollback()
                logger.error(f"删除文档失败: {e}", exc_info=True)
                raise
            finally:
                conn.close()
    
    def count(self) -> int:
        """
        获取向量总数
        
        Returns:
            向量总数
        """
        with self._lock:
            conn = self._get_connection()
            try:
                result = conn.execute("""
                    SELECT COUNT(*) as cnt FROM chunk_embeddings
                """).fetchone()
                return result['cnt'] if result else 0
            except Exception as e:
                logger.error(f"获取向量总数失败: {e}", exc_info=True)
                return 0
            finally:
                conn.close()
    
    def get_all(self, include: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        获取所有文档（兼容 ChromaDB API）
        
        Args:
            include: 要包含的字段列表，如 ['documents', 'metadatas', 'embeddings']
                   如果为 None，返回所有字段
        
        Returns:
            包含 ids, documents, metadatas, embeddings 的字典
        """
        if include is None:
            include = ['documents', 'metadatas', 'embeddings']
        
        with self._lock:
            conn = self._get_connection()
            try:
                # 获取所有 chunks 和对应的 embeddings
                rows = conn.execute("""
                    SELECT c.id, c.content, c.metadata, ce.embedding
                    FROM chunks c
                    LEFT JOIN chunk_embeddings ce ON c.id = ce.chunk_id
                    ORDER BY c.id
                """).fetchall()
                
                result_ids = []
                documents = []
                metadatas = []
                embeddings = []
                
                for row in rows:
                    result_ids.append(row['id'])
                    
                    if 'documents' in include:
                        documents.append(row['content'])
                    else:
                        documents.append(None)
                    
                    # 解析 metadata
                    if 'metadatas' in include:
                        try:
                            metadata = json.loads(row['metadata']) if row['metadata'] else {}
                        except (json.JSONDecodeError, TypeError):
                            metadata = {}
                        metadatas.append(metadata)
                    else:
                        metadatas.append(None)
                    
                    # 恢复 embedding
                    if 'embeddings' in include and row['embedding']:
                        embedding = self._buffer_to_embedding(row['embedding'])
                        embeddings.append(embedding)
                    else:
                        embeddings.append(None)
                
                result = {'ids': result_ids}
                if 'documents' in include:
                    result['documents'] = documents
                if 'metadatas' in include:
                    result['metadatas'] = metadatas
                if 'embeddings' in include:
                    result['embeddings'] = embeddings
                
                return result
                
            except Exception as e:
                logger.error(f"获取所有文档失败: {e}", exc_info=True)
                raise
            finally:
                conn.close()
    
    def get(self, ids: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:  # noqa: ARG002, D102
        """
        获取文档
        
        Args:
            ids: chunk_id 列表
            **kwargs: 其他参数（保留兼容性）
            
        Returns:
            包含 ids, documents, embeddings, metadatas 的字典
        """
        _ = kwargs  # 保留参数以保持接口兼容性
        if not ids:
            return {'ids': [], 'documents': [], 'embeddings': [], 'metadatas': []}
        
        with self._lock:
            conn = self._get_connection()
            try:
                placeholders = ','.join(['?'] * len(ids))
                rows = conn.execute(f"""
                    SELECT c.id, c.content, c.metadata, ce.embedding
                    FROM chunks c
                    LEFT JOIN chunk_embeddings ce ON c.id = ce.chunk_id
                    WHERE c.id IN ({placeholders})
                """, ids).fetchall()
                
                result_ids = []
                documents = []
                embeddings = []
                metadatas = []
                
                for row in rows:
                    result_ids.append(row['id'])
                    documents.append(row['content'])
                    
                    # 解析 metadata
                    try:
                        metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}
                    metadatas.append(metadata)  # 保持 API 兼容性（ChromaDB 使用 metadatas）
                    
                    # 恢复 embedding
                    if row['embedding']:
                        embedding = self._buffer_to_embedding(row['embedding'])
                        embeddings.append(embedding)
                    else:
                        embeddings.append(None)
                
                return {
                    'ids': result_ids,
                    'documents': documents,
                    'embeddings': embeddings,
                    'metadatas': metadatas
                }
                
            except Exception as e:
                logger.error(f"获取文档失败: {e}", exc_info=True)
                raise
            finally:
                conn.close()

