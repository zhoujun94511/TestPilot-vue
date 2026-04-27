#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import logging
import warnings
import threading
from typing import List

# 尝试导入 Embeddings（兼容不同版本的 langchain）
try:
    from langchain_core.embeddings import Embeddings
except ImportError:
    try:
        from langchain.schema.embeddings import Embeddings
    except ImportError:
        try:
            from langchain.embeddings.base import Embeddings
        except ImportError:
            # 如果都失败，定义一个基类作为 fallback
            from abc import ABC, abstractmethod
            class Embeddings(ABC):
                """Embeddings 基类（fallback）"""
                @abstractmethod
                def embed_documents(self, texts: List[str]) -> List[List[float]]:
                    pass
                @abstractmethod
                def embed_query(self, text: str) -> List[float]:
                    pass

# 完全禁用遥测
os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"
os.environ["CHROMA_DISABLE_TELEMETRY"] = "true"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_API_KEY"] = ""
# Windows 多线程安全配置 - 强制串行模式避免访问冲突
os.environ["CHROMA_ALLOW_RESET"] = "true"
os.environ["SQLITE_THREADSAFE"] = "1"
# 禁用 ChromaDB 的内部多线程（避免 Windows 上的访问冲突）
os.environ["CHROMA_DISABLE_VERBOSE_LOGGING"] = "true"
# 强制 SQLite 使用单线程模式（Windows 上的安全选择）
import platform
if platform.system() == "Windows":
    os.environ["SQLITE_SYNCHRONOUS"] = "FULL"
    os.environ["SQLITE_JOURNAL_MODE"] = "WAL"  # Write-Ahead Logging 模式更安全

# 禁用所有相关库的日志
logging.getLogger("chromadb").disabled = True
logging.getLogger("langchain").disabled = True
logging.getLogger("openai").disabled = True
logging.getLogger("langchain_community").disabled = True
logging.getLogger("langchain_core").disabled = True

# 禁用所有警告
warnings.filterwarnings("ignore")

from langchain_chroma import Chroma
from config.settings import settings
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)

# 线程锁，用于保护向量数据库访问
_vector_db_lock = threading.RLock()

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 使用 FastEmbed backend（无 PyTorch 依赖）
try:
    # 导入 EmbeddingManager（已重构为使用 FastEmbed）
    from utils.utils_ai_models.embedding_manager import get_embedding_manager
    
    class FastEmbedLangChainWrapper(Embeddings):
        """FastEmbed 包装器，兼容 LangChain 接口"""
        
        def __init__(self):
            # 使用已经在try块中导入的get_embedding_manager
            self.embedding_manager = get_embedding_manager()
            self.model_info = self.embedding_manager.get_model_info()
            logger.info(f"使用 FastEmbed 模型: {self.model_info['model_name']} (维度: {self.model_info['embedding_dimension']})")
        
        def embed_documents(self, texts: List[str]) -> List[List[float]]:
            """嵌入文档列表"""
            try:
                # 验证和清理文本列表，确保所有元素都是有效的字符串
                if not texts:
                    logger.warning("文本列表为空，返回空列表")
                    return []

                # 过滤掉None和非字符串类型的值
                valid_texts = []
                invalid_details = []
                for i, text in enumerate(texts):
                    if text is None:
                        logger.warning(f"跳过None值（索引 {i}）")
                        invalid_details.append((i, "None"))
                        continue
                    if not isinstance(text, str):
                        original_type = type(text).__name__
                        try:
                            text_str = str(text)
                            if not text_str.strip():
                                logger.warning(f"跳过非字符串类型（索引 {i}，类型：{original_type}），转换后为空")
                                invalid_details.append((i, f"{original_type}->empty"))
                                continue
                            text = text_str
                        except Exception as e:
                            logger.error(f"无法将文本转换为字符串（索引 {i}，类型：{original_type}）: {e}")
                            invalid_details.append((i, f"{original_type}->error:{e}"))
                            continue
                    if not text.strip():
                        logger.debug(f"跳过空文本（索引 {i}）")
                        invalid_details.append((i, "empty"))
                        continue
                    valid_texts.append(text)
                
                if not valid_texts:
                    # 如果所有文本都无效，返回空列表而不是抛出异常，避免阻塞流程
                    logger.warning(
                        f"所有文本都是None或空字符串，无法进行嵌入。原始文本列表长度：{len(texts)}。"
                        f"返回空列表以避免阻塞流程。"
                    )
                    if invalid_details:
                        logger.debug(f"无效索引详情：{invalid_details[:10]}")
                    # 记录前几个文本的详细信息用于调试
                    for i, text in enumerate(texts[:5]):
                        logger.debug(f"  文本[{i}]类型: {type(text)}, 值预览: {repr(text)[:200]}")
                    return []
                
                if len(valid_texts) != len(texts):
                    logger.warning(f"文本列表清理：从 {len(texts)} 个文本过滤到 {len(valid_texts)} 个有效文本")
                    if invalid_details:
                        logger.warning(f"无效文本详情：{invalid_details[:10]}")
                
                # 调用 EmbeddingManager，现在直接返回 List[List[float]]
                doc_embeddings = self.embedding_manager.encode_documents(valid_texts)
                
                # 检查返回的embeddings是否为空（使用 len() 而不是 .shape）
                if doc_embeddings is None or len(doc_embeddings) == 0:
                    logger.warning(
                        f"embedding编码返回空列表（输入文本数量: {len(valid_texts)}）。"
                        f"这可能是因为所有文本在编码阶段被过滤。返回空列表以避免阻塞流程。"
                    )
                    return []
                
                # 直接返回，不需要 .tolist()（已经是 List[List[float]]）
                return doc_embeddings
            except Exception as embed_error:
                logger.error(f"文档嵌入失败: {embed_error}", exc_info=True)
                raise
        
        def embed_query(self, text: str) -> List[float]:
            """嵌入查询文本"""
            try:
                # encode_queries 现在直接返回 List[float]，不需要索引和 .tolist()
                query_embedding = self.embedding_manager.encode_queries(text)
                return query_embedding
            except Exception as query_error:
                logger.error(f"查询嵌入失败: {query_error}")
                raise
    
    # 使用 FastEmbed
    embeddings = FastEmbedLangChainWrapper()
    logger.info("成功初始化 FastEmbed embeddings")
    
except ImportError as import_error:
    logger.warning(f"FastEmbed不可用: {import_error}")
    logger.info("降级到Ollama embeddings")
    
    # 在except块中预先定义变量（避免未定义错误）
    OllamaEmbeddings = None
    get_embedding_manager = None
    
    # 在except块中确保导入可用（避免未定义错误）
    try:
        from utils.utils_ai_models.embedding_manager import get_embedding_manager
    except ImportError:
        get_embedding_manager = None
    
    # 降级到Ollama
    try:
        from langchain_ollama import OllamaEmbeddings
        embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")
        logger.info("使用Ollama embeddings作为备选方案")
    except ImportError:
        # 在 except 块中定义 OllamaEmbeddings 以避免未定义错误
        OllamaEmbeddings = None
        logger.error("无法导入 OllamaEmbeddings，embeddings 未初始化")
        embeddings = None
    
except Exception as init_error:
    logger.error(f"初始化embeddings失败: {init_error}")
    logger.info("降级到Ollama embeddings")
    
    # 在except块中预先定义变量（避免未定义错误）
    OllamaEmbeddings = None
    get_embedding_manager = None
    
    # 在except块中确保导入可用（避免未定义错误）
    try:
        from utils.utils_ai_models.embedding_manager import get_embedding_manager
    except ImportError:
        get_embedding_manager = None
    
    # 最终降级到Ollama
    try:
        from langchain_ollama import OllamaEmbeddings
        embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")
        logger.warning("使用Ollama embeddings作为最终备选方案")
    except ImportError:
        # 在 except 块中定义 OllamaEmbeddings 以避免未定义错误
        OllamaEmbeddings = None
        logger.error("无法导入 OllamaEmbeddings，embeddings 未初始化")
        embeddings = None

def get_embeddings():
    return embeddings

def clear_vector_db(app=None):
    """清空向量数据库中的所有数据（保留数据库结构）
    
    类似 init_db.py 的 clear 命令，只清空数据，不删除文件
    
    Args:
        app: Flask应用实例，如果提供，会使用应用中的vector_db连接
    """
    try:
        # 如果提供了Flask应用，使用应用中的vector_db
        if app and hasattr(app, 'vector_db') and app.vector_db is not None:
            vector_db = app.vector_db
        else:
            # 否则创建新的连接
            vector_db = create_vector_db()
        
        if not vector_db:
            logger.warning("无法获取向量数据库连接")
            return False
        
        # 如果是ThreadSafeVectorDB，获取底层对象
        actual_db = getattr(vector_db, '_vector_db', vector_db)
        
        # 检查是否是 SQLiteVectorStore（通过检查是否有 get_all 方法）
        if hasattr(actual_db, 'get_all'):
            # SQLiteVectorStore 路径
            try:
                all_data = actual_db.get_all(include=['ids'])
                if all_data and 'ids' in all_data:
                    all_ids = all_data['ids']
                    if all_ids:
                        logger.info(f"找到 {len(all_ids)} 个向量数据，开始清空...")
                        actual_db.delete(ids=all_ids)
                        logger.info(f"已清空 {len(all_ids)} 个向量数据")
                        return True
                    else:
                        logger.info("向量数据库为空，无需清空")
                        return True
                else:
                    logger.info("向量数据库为空，无需清空")
                    return True
            except Exception as e:
                logger.error(f"清空向量数据库失败: {e}")
                return False
        else:
            # ChromaDB 路径：获取集合对象
            collection = getattr(actual_db, '_collection', None) or getattr(actual_db, 'collection', None)
            
            if collection:
                # 获取所有文档ID
                try:
                    all_data = collection.get()
                    if all_data and 'ids' in all_data:
                        all_ids = all_data['ids']
                        if all_ids:
                            logger.info(f"找到 {len(all_ids)} 个向量数据，开始清空...")
                            # 删除所有文档
                            collection.delete(ids=all_ids)
                            logger.info(f"已清空 {len(all_ids)} 个向量数据")
                            return True
                        else:
                            logger.info("向量数据库为空，无需清空")
                            return True
                    else:
                        logger.info("向量数据库为空，无需清空")
                        return True
                except Exception as e:
                    logger.error(f"清空向量数据库失败: {e}")
                    return False
            else:
                # 如果没有集合对象，尝试使用 vector_db 的 delete 方法
                try:
                    # 尝试获取所有数据
                    all_data = vector_db.get()
                    if all_data and 'ids' in all_data:
                        all_ids = all_data['ids']
                        if all_ids:
                            logger.info(f"找到 {len(all_ids)} 个向量数据，开始清空...")
                            vector_db.delete(ids=all_ids)
                            logger.info(f"已清空 {len(all_ids)} 个向量数据")
                            return True
                        else:
                            logger.info("向量数据库为空，无需清空")
                            return True
                    else:
                        logger.info("向量数据库为空，无需清空")
                        return True
                except Exception as e:
                    logger.error(f"清空向量数据库失败: {e}")
                    return False
                
    except Exception as e:
        logger.error(f"清空向量数据库失败: {e}")
        return False

def create_vector_db():
    """
    创建向量数据库（线程安全）
    
    当 ENABLE_VECTOR_STORE=false 时直接返回 None，不导入 sqlite_vector_store/chroma，
    便于无向量库依赖运行或 PyInstaller 打包时缩减体积。
    
    支持两种后端（仅在 ENABLE_VECTOR_STORE=true 时生效）：
    - sqlite: SQLite + sqlite-vec（默认）
    - chroma: ChromaDB（保留用于回滚）
    """
    if not getattr(settings, 'ENABLE_VECTOR_STORE', True):
        return None
    with _vector_db_lock:
        # 检查后端配置
        backend = settings.VECTOR_BACKEND.lower()
        
        if backend == 'sqlite':
            # 使用 SQLite + sqlite-vec
            try:
                from utils.utils_ai_models.sqlite_vector_store import SQLiteVectorStore
                vector_db = SQLiteVectorStore(embedding_function=embeddings)
                return ThreadSafeVectorDB(vector_db)
            except Exception as e:
                logger.error(f"创建 SQLite 向量存储失败: {e}", exc_info=True)
                logger.warning("降级到 ChromaDB 后端")
                # 降级到 ChromaDB
                backend = 'chroma'
        
        if backend == 'chroma':
            # 使用 ChromaDB（保留用于回滚）
            try:
                import platform
                import chromadb
                from chromadb.config import Settings as ChromaSettings
                
                # 使用新版本的 ChromaDB 客户端 API
                # 创建 ChromaDB 客户端设置
                chroma_settings = ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                    is_persistent=True,
                )
                
                # Windows 上的特殊配置
                if platform.system() == "Windows":
                    # Windows 上强制使用持久化客户端
                    try:
                        # 创建持久化客户端
                        chroma_client = chromadb.PersistentClient(
                            path=settings.VECTOR_STORE_DIR,
                            settings=chroma_settings
                        )
                        
                        # 使用新 API 创建 Chroma 向量存储
                        vector_db = Chroma(
                            client=chroma_client,
                            embedding_function=embeddings,
                            collection_name=settings.CHROMA_COLLECTION_NAME
                        )
                    except Exception as client_error:
                        logger.warning(f"使用新 API 创建客户端失败，降级到旧方式: {client_error}")
                        # 降级到简单方式
                        vector_db = Chroma(
                            embedding_function=embeddings,
                            persist_directory=settings.VECTOR_STORE_DIR,
                            collection_name=settings.CHROMA_COLLECTION_NAME
                        )
                else:
                    # 非 Windows 平台
                    try:
                        chroma_client = chromadb.PersistentClient(
                            path=settings.VECTOR_STORE_DIR,
                            settings=chroma_settings
                        )
                        vector_db = Chroma(
                            client=chroma_client,
                            embedding_function=embeddings,
                            collection_name=settings.CHROMA_COLLECTION_NAME
                        )
                    except (ImportError, AttributeError, TypeError, ValueError) as client_fallback_error:
                        # 降级到旧方式（处理客户端创建失败的情况）
                        logger.warning(f"使用新 API 创建客户端失败，降级到旧方式: {client_fallback_error}")
                        vector_db = Chroma(
                            embedding_function=embeddings,
                            persist_directory=settings.VECTOR_STORE_DIR,
                            collection_name=settings.CHROMA_COLLECTION_NAME
                        )
                
                # 包装为线程安全的代理
                return ThreadSafeVectorDB(vector_db)
                
            except Exception as e:
                error_msg = str(e).lower()
                # 处理维度不匹配问题
                if "dimension" in error_msg:
                    logger.warning(f"检测到维度不匹配问题: {e}")
                    logger.info("清理旧数据库并重新创建...")
                    clear_vector_db()
                    # 重新创建（使用简单方式）
                    vector_db = Chroma(
                        embedding_function=embeddings,
                        persist_directory=settings.VECTOR_STORE_DIR,
                        collection_name=settings.CHROMA_COLLECTION_NAME
                    )
                    return ThreadSafeVectorDB(vector_db)
                # 处理弃用警告（如果新 API 不可用，降级到旧方式）
                elif "deprecated" in error_msg or "migration" in error_msg:
                    logger.warning(f"检测到 ChromaDB 配置弃用警告: {e}")
                    logger.info("尝试使用新版本的客户端 API...")
                    try:
                        import chromadb
                        chroma_client = chromadb.PersistentClient(path=settings.VECTOR_STORE_DIR)
                        vector_db = Chroma(
                            client=chroma_client,
                            embedding_function=embeddings,
                            collection_name=settings.CHROMA_COLLECTION_NAME
                        )
                        return ThreadSafeVectorDB(vector_db)
                    except Exception as fallback_error:
                        logger.error(f"使用新 API 失败，使用旧方式: {fallback_error}")
                        # 最后降级到最简单的旧方式（忽略弃用警告）
                        vector_db = Chroma(
                            embedding_function=embeddings,
                            persist_directory=settings.VECTOR_STORE_DIR,
                            collection_name=settings.CHROMA_COLLECTION_NAME
                        )
                        return ThreadSafeVectorDB(vector_db)
                else:
                    raise
        else:
            # 未知的后端类型
            raise ValueError(
                f"未知的向量存储后端: {backend}，"
                f"支持的值: 'sqlite', 'chroma'"
            )

def create_vector_db_from_texts(texts):
    """从文本创建向量数据库，自动处理维度不匹配问题"""
    try:
        # 尝试创建向量数据库
        return Chroma.from_texts(
            texts=texts,
            embedding=embeddings,
            persist_directory=settings.VECTOR_STORE_DIR
        )
    except Exception as e:
        if "dimension" in str(e).lower():
            logger.warning(f"检测到维度不匹配问题: {e}")
            logger.info("清理旧数据库并重新创建...")
            clear_vector_db()
            # 重新创建
            return Chroma.from_texts(
                texts=texts,
                embedding=embeddings,
                persist_directory=settings.VECTOR_STORE_DIR
            )
        else:
            raise

def create_vector_db_from_docs(documents):
    """
    通过 Document 对象列表创建向量数据库，自动处理维度不匹配问题
    """
    try:
        # 尝试创建向量数据库
        return Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=settings.VECTOR_STORE_DIR
        )
    except Exception as e:
        if "dimension" in str(e).lower():
            logger.warning(f"检测到维度不匹配问题: {e}")
            logger.info("清理旧数据库并重新创建...")
            clear_vector_db()
            # 重新创建
            return Chroma.from_documents(
                documents=documents,
                embedding=embeddings,
                persist_directory=settings.VECTOR_STORE_DIR
            )
        else:
            raise

class ThreadSafeVectorDB:
    """线程安全的向量数据库包装器
    
    包装 Chroma 对象，确保所有操作都是线程安全的
    这对于 Windows 上的多线程环境特别重要
    """
    
    def __init__(self, vector_db):
        """初始化线程安全的向量数据库包装器
        
        Args:
            vector_db: 原始 Chroma 向量数据库实例
        """
        self._vector_db = vector_db
        self._lock = threading.RLock()
    
    def __getattr__(self, name):
        """代理属性访问到原始向量数据库"""
        attr = getattr(self._vector_db, name)
        
        # 对于可能修改数据库的方法，使用锁保护
        # 注意：similarity_search 和 similarity_search_with_score 有专门的实现，不在这里处理
        if callable(attr) and name in ['add_documents', 'delete', 'update', 'upsert', 
                                       'get', 'delete_collection']:
            def thread_safe_method(*args, **kwargs):
                with self._lock:
                    try:
                        return attr(*args, **kwargs)
                    except Exception as e:
                        logger.error(f"向量数据库操作失败 ({name}): {e}", exc_info=True)
                        raise
            return thread_safe_method
        
        return attr
    
    def add_documents(self, documents, **kwargs):
        """线程安全的添加文档"""
        with self._lock:
            try:
                result = self._vector_db.add_documents(documents, **kwargs)
                logger.debug(f"ThreadSafeVectorDB.add_documents 返回: {type(result)}, 长度: {len(result) if result else 0}")
                return result
            except Exception as e:
                logger.error(f"添加文档到向量数据库失败: {e}", exc_info=True)
                raise
    
    def delete(self, ids=None, **kwargs):
        """线程安全的删除文档"""
        with self._lock:
            try:
                return self._vector_db.delete(ids=ids, **kwargs)
            except Exception as e:
                logger.error(f"从向量数据库删除文档失败: {e}", exc_info=True)
                raise
    
    def count(self):
        """线程安全的获取向量总数（SQLiteVectorStore 支持）"""
        with self._lock:
            try:
                # 获取实际的向量数据库对象（可能是 ThreadSafeVectorDB 包装的）
                actual_db = getattr(self._vector_db, '_vector_db', self._vector_db)
                
                # 检查向量数据库类型
                vector_db_type = type(actual_db).__name__
                
                # SQLiteVectorStore 支持 count 方法
                if vector_db_type == 'SQLiteVectorStore':
                    return actual_db.count()
                # 检查是否有 count 方法
                elif hasattr(actual_db, 'count'):
                    return actual_db.count()
                else:
                    # ChromaDB 不支持 count，返回 None 或抛出异常
                    raise AttributeError("向量数据库不支持 count 方法")
            except AttributeError as e:
                # ChromaDB 不支持 count 方法，这是已知限制，使用 DEBUG 级别
                logger.debug(f"向量数据库不支持 count 方法（ChromaDB 限制）: {e}")
                raise
            except Exception as e:
                logger.error(f"获取向量总数失败: {e}", exc_info=True)
                raise
    
    def get_all(self, include=None):
        """线程安全的获取所有文档（SQLiteVectorStore 支持）"""
        with self._lock:
            try:
                if hasattr(self._vector_db, 'get_all'):
                    return self._vector_db.get_all(include=include)
                else:
                    # ChromaDB 不支持 get_all，返回 None 或抛出异常
                    raise AttributeError("向量数据库不支持 get_all 方法")
            except Exception as e:
                logger.error(f"获取所有文档失败: {e}", exc_info=True)
                raise
    
    def similarity_search(self, query, k=4, **kwargs):
        """线程安全的相似性搜索（过滤不支持的 filter 操作符）"""
        with self._lock:
            try:
                # 清理 kwargs，移除 ChromaDB 1.1.0 不支持的 filter 操作符
                cleaned_kwargs = self._clean_filter_kwargs(kwargs.copy())
                return self._vector_db.similarity_search(query, k=k, **cleaned_kwargs)
            except Exception as e:
                error_msg = str(e)
                # 如果是 $contains 错误，尝试移除 filter 重试
                if "$contains" in error_msg:
                    logger.warning(f"检测到不支持的 $contains 操作符，移除 filter 重试")
                    cleaned_kwargs = kwargs.copy()
                    cleaned_kwargs.pop('filter', None)
                    cleaned_kwargs.pop('where', None)
                    return self._vector_db.similarity_search(query, k=k, **cleaned_kwargs)
                logger.error(f"向量数据库相似性搜索失败: {e}", exc_info=True)
                raise
    
    def similarity_search_with_score(self, query, k=4, **kwargs):
        """线程安全的相似性搜索（带得分，过滤不支持的 filter 操作符）"""
        with self._lock:
            try:
                # 清理 kwargs，移除 ChromaDB 1.1.0 不支持的 filter 操作符
                cleaned_kwargs = self._clean_filter_kwargs(kwargs.copy())
                return self._vector_db.similarity_search_with_score(query, k=k, **cleaned_kwargs)
            except Exception as e:
                error_msg = str(e)
                # 如果是 $contains 错误，尝试移除 filter 重试
                if "$contains" in error_msg:
                    logger.warning(f"检测到不支持的 $contains 操作符，移除 filter 重试")
                    cleaned_kwargs = kwargs.copy()
                    cleaned_kwargs.pop('filter', None)
                    cleaned_kwargs.pop('where', None)
                    return self._vector_db.similarity_search_with_score(query, k=k, **cleaned_kwargs)
                logger.error(f"向量数据库相似性搜索（带得分）失败: {e}", exc_info=True)
                raise
    
    @staticmethod
    def _clean_filter_kwargs(kwargs):
        """清理 filter 参数，移除 ChromaDB 不支持的操作符
        
        ChromaDB 1.1.0 支持的操作符: $gt, $gte, $lt, $lte, $ne, $eq, $in, $nin
        不支持的操作符: $contains, $not_contains 等
        """
        if 'filter' not in kwargs and 'where' not in kwargs:
            return kwargs
        
        cleaned_kwargs = kwargs.copy()
        
        # 检查并清理 filter
        if 'filter' in cleaned_kwargs:
            filter_dict = cleaned_kwargs['filter']
            if isinstance(filter_dict, dict):
                # 递归检查并移除包含 $contains 的字段
                cleaned_filter = ThreadSafeVectorDB._remove_contains_from_filter(filter_dict)
                if cleaned_filter:
                    cleaned_kwargs['filter'] = cleaned_filter
                else:
                    # 如果 filter 被完全清空，移除 filter 参数
                    cleaned_kwargs.pop('filter', None)
        
        # 检查并清理 where（ChromaDB 新版本可能使用 where）
        if 'where' in cleaned_kwargs:
            where_dict = cleaned_kwargs['where']
            if isinstance(where_dict, dict):
                cleaned_where = ThreadSafeVectorDB._remove_contains_from_filter(where_dict)
                if cleaned_where:
                    cleaned_kwargs['where'] = cleaned_where
                else:
                    cleaned_kwargs.pop('where', None)
        
        return cleaned_kwargs
    
    @staticmethod
    def _remove_contains_from_filter(filter_dict):
        """递归移除 filter 中的 $contains 操作符"""
        if not isinstance(filter_dict, dict):
            return filter_dict
        
        cleaned = {}
        for key, value in filter_dict.items():
            if isinstance(value, dict):
                # 检查是否包含 $contains
                if '$contains' in value or '$not_contains' in value:
                    # 跳过包含不支持操作符的字段
                    continue
                # 递归处理嵌套字典
                cleaned_value = ThreadSafeVectorDB._remove_contains_from_filter(value)
                if cleaned_value:
                    cleaned[key] = cleaned_value
            else:
                cleaned[key] = value
        
        return cleaned if cleaned else None
    
    def get(self, ids=None, **kwargs):
        """线程安全的获取文档"""
        with self._lock:
            try:
                return self._vector_db.get(ids=ids, **kwargs)
            except Exception as e:
                logger.error(f"从向量数据库获取文档失败: {e}", exc_info=True)
                raise


if __name__ == '__main__':
    pass