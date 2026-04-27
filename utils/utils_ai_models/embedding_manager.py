#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
智能Embedding管理器
使用轻量级 embedding backend（FastEmbed / ONNX），不依赖 PyTorch
"""
import time
import threading
from typing import List, Union, Optional, Dict, Any
from utils.utils_core.logger import get_logger
from utils.utils_ai_models.embedding_monitor import get_embedding_monitor
from utils.utils_ai_models.embedding_backends import FastEmbedBackend, EmbeddingBackend
from config.settings import settings

logger = get_logger(__name__)

# 全局线程锁，用于保护 EmbeddingManager 的初始化和使用
_embedding_manager_lock = threading.RLock()


class EmbeddingManager:
    """智能Embedding管理器（无 PyTorch 依赖）"""
    
    def __init__(self, model_name: Optional[str] = None, backend: Optional[EmbeddingBackend] = None):
        """
        初始化Embedding管理器
        
         重要：不再支持自动选择模型，必须通过配置明确指定
        
        Args:
            model_name: 模型名称（已废弃，从配置读取）
            backend: Embedding后端实例，如果为None则使用FastEmbedBackend（从配置读取）
        """
        self.monitor = get_embedding_monitor()
        # 初始化线程锁，用于保护模型访问
        self._encode_lock = threading.RLock()
        
        # 初始化 backend（从配置读取，不允许自动选择）
        if backend is not None:
            self.backend = backend
        else:
            # 从配置读取模型名称和维度（不允许自动选择）
            # 如果传入 model_name，记录警告（向后兼容）
            if model_name:
                logger.warning(
                    f" 通过参数传入 model_name={model_name} 已废弃，"
                    f"将使用配置 EMBEDDING_MODEL_NAME={settings.EMBEDDING_MODEL_NAME}"
                )
            self.backend = FastEmbedBackend()
        
        self.model_name = self.backend.model_name()
        self.device = 'cpu'  # FastEmbed 使用 ONNX，统一使用 CPU
        logger.info(f"EmbeddingManager 初始化成功: {self.model_name} (维度: {self.backend.dimension()})")
    
    @staticmethod
    def _clean_texts(texts: List[str]) -> List[str]:
        """
        清洗文本列表，移除无效字符
        
        Args:
            texts: 原始文本列表
            
        Returns:
            清洗后的文本列表
        """
        import re
        valid_texts = []
        
        for i, t in enumerate(texts):
            if t is None:
                continue
            
            # 确保是字符串类型
            if not isinstance(t, str):
                try:
                    t = str(t)
                except (TypeError, ValueError) as conv_err:
                    logger.warning(
                        f"跳过无法转换为字符串的项: 索引={i}, 类型={type(t).__name__}, 错误={conv_err}"
                    )
                    continue
            
            # 清理文本：移除控制字符和特殊Unicode字符
            try:
                # 移除控制字符（保留换行符、制表符、回车符）
                t = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', t)
                # 移除零宽字符
                t = re.sub(r'[\u200B-\u200D\uFEFF]', '', t)
                # 确保是有效的UTF-8
                t = t.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
            except Exception as clean_err:
                logger.warning(f"清理文本（索引 {i}）失败: {clean_err}")
                continue
            
            t = t.strip()
            if not t:
                continue
            
            valid_texts.append(t)
        
        return valid_texts
    
    def encode(self, texts: Union[str, List[str]],
               batch_size: int = None,
               show_progress: bool = False) -> List[List[float]]:
        """
        编码文本为向量（线程安全，输入强校验版）
        
        Args:
            texts: 文本或文本列表
            batch_size: 批处理大小（FastEmbed 内部处理，此参数保留兼容性）
            show_progress: 是否显示进度（FastEmbed 内部处理，此参数保留兼容性）
            
        Returns:
            向量列表，每个向量是 List[float]（float32）
        """
        with self._encode_lock:
            start_time = time.time()
            success = False
            tokens = 0

            try:
                # ---- 1️⃣ 输入预处理 ----
                if isinstance(texts, str):
                    texts = [texts]
                elif not isinstance(texts, list):
                    logger.warning(f"输入类型 {type(texts)} 非列表或字符串，强制转换为字符串列表")
                    texts = [str(texts)]

                # ---- 2️⃣ 清洗空文本和非法值 ----
                valid_texts = self._clean_texts(texts)

                if not valid_texts:
                    # 如果所有文本都无效，记录警告并返回空列表
                    logger.warning(
                        f"无有效文本可供编码（原始文本数量: {len(texts)}，全部为空或无效）。"
                        f"返回空列表以避免阻塞流程。"
                    )
                    return []

                # 如果过滤了部分文本，记录警告
                if len(valid_texts) != len(texts):
                    logger.warning(f"文本列表清理：从 {len(texts)} 个文本过滤到 {len(valid_texts)} 个有效文本")

                # ---- 3️⃣ 调用 backend 编码 ----
                embeddings = self.backend.embed_documents(valid_texts)
                
                success = True
                return embeddings

            except Exception as e:
                logger.error(f"文本编码失败: {e}", exc_info=True)
                # 错误监控
                try:
                    self.monitor.record_error(
                        error_type=type(e).__name__,
                        error_message=str(e),
                        model_name=self.model_name,
                        device=self.device,
                        input_length=len(texts) if isinstance(texts, list) else 1
                    )
                except Exception as monitor_error:
                    logger.warning(f"记录错误指标失败: {monitor_error}")
                raise

            finally:
                # ---- 性能指标记录 ----
                try:
                    duration = time.time() - start_time
                    # 估算tokens（用于性能监控）
                    if success and 'valid_texts' in locals():
                        tokens = sum(len(text.split()) for text in valid_texts)
                    self.monitor.record_call(
                        tokens=tokens,
                        duration=duration,
                        success=success,
                        cache_hit=False,
                        model_name=self.model_name,
                        device=self.device
                    )
                except Exception as monitor_error:
                    logger.warning(f"记录性能指标失败: {monitor_error}")

    def encode_queries(self, queries: Union[str, List[str]]) -> List[float]:
        """
        编码查询文本（针对查询优化）
        
         空输入语义约定：
            - encode_queries("") → 抛出 ValueError（不允许空字符串）
            - encode_queries([]) → 抛出 ValueError（不允许空列表）
            - 空输入必须由调用方处理，不在本方法中隐式处理
        
        Args:
            queries: 查询文本或文本列表（如果为列表，只取第一个）
            
        Returns:
            向量，List[float]（float32）
            
        Raises:
            ValueError: 如果输入为空字符串或空列表
        """
        with self._encode_lock:
            start_time = time.time()
            success = False
            tokens = 0

            try:
                # 处理输入
                if isinstance(queries, str):
                    query_text = queries
                elif isinstance(queries, list):
                    if len(queries) == 0:
                        raise ValueError("查询文本列表不能为空")
                    query_text = queries[0]
                else:
                    raise ValueError(f"无效的查询输入类型: {type(queries)}")

                # 清洗文本
                cleaned = self._clean_texts([query_text])
                if not cleaned:
                    # 空输入约定：抛出异常（不允许隐式处理）
                    raise ValueError("查询文本清洗后为空，不允许编码空文本")

                query_text = cleaned[0]

                # 调用 backend 编码（backend 会再次检查空字符串）
                embedding = self.backend.embed_query(query_text)
                
                success = True
                return embedding

            except Exception as e:
                logger.error(f"查询编码失败: {e}", exc_info=True)
                # 错误监控
                try:
                    self.monitor.record_error(
                        error_type=type(e).__name__,
                        error_message=str(e),
                        model_name=self.model_name,
                        device=self.device,
                        input_length=1
                    )
                except Exception as monitor_error:
                    logger.warning(f"记录错误指标失败: {monitor_error}")
                raise

            finally:
                # 性能指标记录
                try:
                    duration = time.time() - start_time
                    if success:
                        tokens = len(query_text.split()) if 'query_text' in locals() else 0
                    self.monitor.record_call(
                        tokens=tokens,
                        duration=duration,
                        success=success,
                        cache_hit=False,
                        model_name=self.model_name,
                        device=self.device
                    )
                except Exception as monitor_error:
                    logger.warning(f"记录性能指标失败: {monitor_error}")
    
    def encode_documents(self, documents: Union[str, List[str]]) -> List[List[float]]:
        """
        编码文档文本（针对文档优化）
        
        Args:
            documents: 文档文本或文本列表
            
        Returns:
            向量列表，每个向量是 List[float]（float32）
        """
        return self.encode(documents)
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
         重要：model_type 字段仅用于日志/展示/诊断，不允许作为业务逻辑分支条件
        
        Returns:
            模型信息字典，包含：
            - model_name: 模型名称
            - device: 设备类型（固定为 'cpu'）
            - max_seq_length: 最大序列长度
            - embedding_dimension: embedding 维度（与配置 EMBEDDING_DIM 一致）
            - model_type: 模型后端类型（仅用于展示，不可用于逻辑判断）
        """
        return {
            'model_name': self.model_name,
            'device': self.device,
            'max_seq_length': 512,  # FastEmbed 默认值
            'embedding_dimension': self.backend.dimension(),
            'model_type': 'fastembed'  #  仅用于展示，不可用于业务逻辑判断
        }
    
    def test_performance(self, test_texts: List[str] = None) -> Dict[str, Any]:
        """测试模型性能"""
        if test_texts is None:
            test_texts = [
                "这是一个测试文档，用于评估embedding模型的性能。",
                "This is a test document for evaluating embedding model performance.",
                "测试用例生成是软件测试的重要环节。",
                "Test case generation is an important part of software testing."
            ]
        
        import time
        
        # 测试编码速度
        start_time = time.time()
        embeddings = self.encode(test_texts)
        encoding_time = time.time() - start_time
        
        # 测试相似度计算（使用 numpy，但不在核心路径中）
        try:
            import numpy as np
            embeddings_array = np.array(embeddings, dtype=np.float32)
            start_time = time.time()
            similarity_matrix = np.dot(embeddings_array, embeddings_array.T)
            similarity_time = time.time() - start_time
            
            # 计算平均相似度作为性能指标
            avg_similarity = np.mean(similarity_matrix[np.triu_indices_from(similarity_matrix, k=1)])
            
            return {
                'encoding_time': encoding_time,
                'similarity_time': similarity_time,
                'texts_count': len(test_texts),
                'embedding_dimension': len(embeddings[0]) if embeddings else 0,
                'avg_encoding_time_per_text': encoding_time / len(test_texts),
                'avg_similarity': float(avg_similarity),
                'similarity_matrix_shape': similarity_matrix.shape
            }
        except ImportError:
            # 如果没有 numpy，只返回编码时间
            return {
                'encoding_time': encoding_time,
                'texts_count': len(test_texts),
                'embedding_dimension': len(embeddings[0]) if embeddings else 0,
                'avg_encoding_time_per_text': encoding_time / len(test_texts),
            }


class EmbeddingCache:
    """Embedding缓存管理器（适配 List[float] 类型）"""
    
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.access_count = {}
    
    def get(self, text: str) -> Optional[List[float]]:
        """获取缓存的embedding"""
        cache_key = hash(text)
        if cache_key in self.cache:
            self.access_count[cache_key] = self.access_count.get(cache_key, 0) + 1
            return self.cache[cache_key]
        return None
    
    def set(self, text: str, embedding: List[float]):
        """设置缓存的embedding"""
        cache_key = hash(text)
        
        # 如果缓存已满，删除最少使用的项
        if len(self.cache) >= self.max_size:
            least_used_key = min(self.access_count.keys(), 
                                key=lambda k: self.access_count.get(k, 0))
            del self.cache[least_used_key]
            del self.access_count[least_used_key]
        
        self.cache[cache_key] = embedding
        self.access_count[cache_key] = 1
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.access_count.clear()


# 全局实例
_embedding_manager = None
_embedding_cache = None

def get_embedding_manager() -> EmbeddingManager:
    """获取全局embedding管理器实例（线程安全）"""
    global _embedding_manager
    with _embedding_manager_lock:
        if _embedding_manager is None:
            try:
                _embedding_manager = EmbeddingManager()
            except Exception as e:
                logger.error(f"初始化EmbeddingManager失败: {e}", exc_info=True)
                raise
        return _embedding_manager

def get_embedding_cache() -> EmbeddingCache:
    """获取全局embedding缓存实例"""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache

def encode_texts(texts: Union[str, List[str]], use_cache: bool = True) -> List[List[float]]:
    """
    便捷函数：编码文本
    
    Args:
        texts: 文本或文本列表
        use_cache: 是否使用缓存
        
    Returns:
        向量列表，每个向量是 List[List[float]]（float32）
    """
    manager = get_embedding_manager()
    
    if use_cache and isinstance(texts, list) and len(texts) == 1:
        # 单个文本尝试从缓存获取
        cache = get_embedding_cache()
        cached_embedding = cache.get(texts[0])
        if cached_embedding is not None:
            return [cached_embedding]  # 包装成列表
    
    # 编码文本
    embeddings = manager.encode(texts)
    
    # 缓存结果（支持单个和批量）
    if use_cache:
        cache = get_embedding_cache()
        if isinstance(texts, str):
            if embeddings:
                cache.set(texts, embeddings[0])
        elif isinstance(texts, list):
            for i, text in enumerate(texts):
                if i < len(embeddings):
                    cache.set(text, embeddings[i])
    
    return embeddings
