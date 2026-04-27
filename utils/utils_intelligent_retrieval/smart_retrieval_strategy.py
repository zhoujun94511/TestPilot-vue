#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
智能检索策略模块
实现多策略检索、动态权重调整、上下文感知检索等功能
"""
import time
from enum import Enum
from dataclasses import dataclass
from utils.utils_core.logger import get_logger
from typing import List, Dict, Any, Optional
from utils.utils_intelligent_retrieval.rag_keyword_config import get_rag_keyword_config
from utils.utils_document_processing.content_similarity import ContentSimilarityDetector

logger = get_logger(__name__)


class RetrievalStrategy(Enum):
    """检索策略枚举"""
    SEMANTIC = "semantic"  # 语义检索
    KEYWORD = "keyword"    # 关键词检索
    HYBRID = "hybrid"      # 混合检索
    CONTEXT_AWARE = "context_aware"  # 上下文感知检索


@dataclass
class RetrievalResult:
    """检索结果数据类"""
    content: str
    score: float
    metadata: Dict[str, Any]
    strategy: RetrievalStrategy
    relevance_factors: Dict[str, float]


@dataclass
class RetrievalConfig:
    """检索配置"""
    top_k: int = 5
    score_threshold: float = 0.7
    enable_reranking: bool = True
    enable_query_expansion: bool = True
    enable_context_awareness: bool = True
    max_context_length: int = 2000
    similarity_threshold: float = 0.8


class SmartRetrievalStrategy:
    """智能检索策略管理器"""
    
    def __init__(self, config: Optional[RetrievalConfig] = None):
        """
        初始化智能检索策略
        
        Args:
            config: 检索配置，如果为None则使用默认配置
        """
        self.config = config or RetrievalConfig()
        self.keyword_config = get_rag_keyword_config()
        self.similarity_detector = ContentSimilarityDetector(
            similarity_threshold=self.config.similarity_threshold
        )
        
        # 整合 RequirementKeywordExtractor 增强关键词提取能力
        try:
            from utils.utils_intelligent_retrieval.requirement_keyword_extractor import get_requirement_keyword_extractor
            self.keyword_extractor = get_requirement_keyword_extractor(self.keyword_config)
            self._enhanced_keyword_extraction = True
        except Exception as e:
            logger.warning(f"无法加载 RequirementKeywordExtractor，使用简单关键词提取: {e}")
            self.keyword_extractor = None
            self._enhanced_keyword_extraction = False
        
        # 检索策略权重
        self.strategy_weights = {
            RetrievalStrategy.SEMANTIC: 0.6,
            RetrievalStrategy.KEYWORD: 0.3,
            RetrievalStrategy.HYBRID: 0.8,
            RetrievalStrategy.CONTEXT_AWARE: 0.9
        }

        # 性能统计
        self.performance_stats = {
            'total_queries': 0,
            'avg_response_time': 0.0,
            'strategy_usage': {strategy.value: 0 for strategy in RetrievalStrategy},
            'success_rate': 0.0
        }

    @staticmethod
    def _is_empty_query_error(error: Exception) -> bool:
        text = str(error or "")
        return ("查询文本清洗后为空" in text) or ("不允许编码空文本" in text)
    
    def retrieve(
        self, 
        query: str, 
        vector_db, 
        context: Optional[str] = None,
        strategy: Optional[RetrievalStrategy] = None,
        top_k: Optional[int] = None
    ) -> List[RetrievalResult]:
        """
        执行智能检索
        
        Args:
            query: 查询文本
            vector_db: 向量数据库
            context: 上下文信息
            strategy: 指定检索策略，如果为None则自动选择
            top_k: 返回结果数量，如果为None则使用配置中的top_k
            
        Returns:
            检索结果列表
        """
        start_time = time.time()
        
        # 使用传入的 top_k 或配置中的 top_k
        effective_top_k = top_k if top_k is not None else self.config.top_k
        
        try:
            # 自动选择最佳策略
            if strategy is None:
                strategy = self._select_optimal_strategy(query, context)
            
            # 临时更新配置以使用指定的 top_k
            original_top_k = self.config.top_k
            self.config.top_k = effective_top_k
            
            try:
                # 执行检索
                results = self._execute_retrieval(query, vector_db, context, strategy)
            finally:
                # 恢复原始配置
                self.config.top_k = original_top_k
            
            # 重排序
            if self.config.enable_reranking:
                results = self._rerank_results(results, query, context)
            
            # 更新性能统计
            self._update_performance_stats(strategy, time.time() - start_time, True)
            
            return results[:effective_top_k]
            
        except Exception as e:
            logger.error(f"智能检索失败: {e}")
            self._update_performance_stats(
                strategy if strategy is not None else RetrievalStrategy.SEMANTIC,
                time.time() - start_time,
                False
            )
            return []
    
    def _select_optimal_strategy(self, query: str, context: Optional[str] = None) -> RetrievalStrategy:
        """
        根据查询和上下文选择最佳检索策略
        
        Args:
            query: 查询文本
            context: 上下文信息
            
        Returns:
            最佳检索策略
        """
        # 分析查询特征
        query_features = self._analyze_query_features(query)
        
        # 如果有上下文且启用上下文感知，优先使用上下文感知检索
        if context and self.config.enable_context_awareness:
            return RetrievalStrategy.CONTEXT_AWARE
        
        # 如果查询包含大量关键词，使用混合检索
        if query_features['keyword_density'] > 0.3:
            return RetrievalStrategy.HYBRID
        
        # 如果查询较短且语义性强，使用语义检索
        if query_features['semantic_strength'] > 0.7:
            return RetrievalStrategy.SEMANTIC
        
        # 默认使用混合检索
        return RetrievalStrategy.HYBRID
    
    def _analyze_query_features(self, query: str) -> Dict[str, float]:
        """
        分析查询特征
        
        Args:
            query: 查询文本
            
        Returns:
            查询特征字典
        """
        # 获取关键词配置
        all_keywords = self.keyword_config.get_all_keywords()
        exclude_keywords = self.keyword_config.get_exclude_keywords()
        
        # 计算关键词密度
        query_lower = query.lower()
        keyword_matches = sum(1 for keyword in all_keywords if keyword in query_lower)
        keyword_density = keyword_matches / max(len(query.split()), 1)
        
        # 计算语义强度（基于查询长度和复杂度）
        semantic_strength = min(len(query) / 100.0, 1.0)
        
        # 计算排除关键词比例
        exclude_matches = sum(1 for keyword in exclude_keywords if keyword in query_lower)
        exclude_ratio = exclude_matches / max(len(query.split()), 1)
        
        return {
            'keyword_density': keyword_density,
            'semantic_strength': semantic_strength,
            'exclude_ratio': exclude_ratio,
            'query_length': len(query),
            'word_count': len(query.split())
        }
    
    def _execute_retrieval(
        self, 
        query: str, 
        vector_db, 
        context: Optional[str] = None,
        strategy: RetrievalStrategy = RetrievalStrategy.SEMANTIC
    ) -> List[RetrievalResult]:
        """
        执行具体检索策略
        
        Args:
            query: 查询文本
            vector_db: 向量数据库
            context: 上下文信息
            strategy: 检索策略
            
        Returns:
            检索结果列表
        """
        if strategy == RetrievalStrategy.SEMANTIC:
            return self._semantic_retrieval(query, vector_db)
        elif strategy == RetrievalStrategy.KEYWORD:
            return self._keyword_retrieval(query, vector_db)
        elif strategy == RetrievalStrategy.HYBRID:
            return self._hybrid_retrieval(query, vector_db)
        elif strategy == RetrievalStrategy.CONTEXT_AWARE:
            return self._context_aware_retrieval(query, vector_db, context)
        else:
            return self._semantic_retrieval(query, vector_db)
    
    def _semantic_retrieval(self, query: str, vector_db) -> List[RetrievalResult]:
        """语义检索"""
        try:
            # 尝试使用 similarity_search_with_score 获取文档ID和得分
            # 如果方法不存在，降级到 similarity_search
            try:
                docs_with_scores = vector_db.similarity_search_with_score(query, k=self.config.top_k)
                
                results = []
                for doc, score in docs_with_scores:
                    # 确保metadata存在
                    metadata = getattr(doc, 'metadata', {}) or {}
                    
                    results.append(RetrievalResult(
                        content=doc.page_content,
                        score=float(score) if score is not None else 0.8,
                        metadata=metadata,
                        strategy=RetrievalStrategy.SEMANTIC,
                        relevance_factors={'semantic_similarity': float(score) if score is not None else 0.8}
                    ))
                
                return results
            except AttributeError:
                # 如果 similarity_search_with_score 不存在，使用 similarity_search
                docs = vector_db.similarity_search(query, k=self.config.top_k)
                
                results = []
                for doc in docs:
                    # 计算语义相似度得分
                    score = getattr(doc, 'score', 0.8)  # 默认得分
                    # 确保metadata存在
                    metadata = getattr(doc, 'metadata', {}) or {}
                    
                    results.append(RetrievalResult(
                        content=doc.page_content,
                        score=score,
                        metadata=metadata,
                        strategy=RetrievalStrategy.SEMANTIC,
                        relevance_factors={'semantic_similarity': score}
                    ))
                
                return results
            
        except Exception as e:
            if self._is_empty_query_error(e):
                logger.debug(f"语义检索跳过（空查询）: {e}")
            else:
                logger.error(f"语义检索失败: {e}")
            return []
    
    def _keyword_retrieval(self, query: str, vector_db) -> List[RetrievalResult]:
        """关键词检索"""
        try:
            # 提取关键词
            keywords = self._extract_keywords(query)
            
            # 构建关键词查询
            keyword_query = " ".join(keywords)
            
            # 执行搜索
            docs = vector_db.similarity_search(keyword_query, k=self.config.top_k)
            
            results = []
            for doc in docs:
                # 计算关键词匹配得分
                keyword_score = self._calculate_keyword_score(doc.page_content, keywords)
                
                results.append(RetrievalResult(
                    content=doc.page_content,
                    score=keyword_score,
                    metadata=doc.metadata,
                    strategy=RetrievalStrategy.KEYWORD,
                    relevance_factors={'keyword_match': keyword_score}
                ))
            
            return results
            
        except Exception as e:
            if self._is_empty_query_error(e):
                logger.debug(f"关键词检索跳过（空查询）: {e}")
            else:
                logger.error(f"关键词检索失败: {e}")
            return []
    
    def _hybrid_retrieval(self, query: str, vector_db) -> List[RetrievalResult]:
        """混合检索"""
        try:
            # 执行语义检索
            semantic_results = self._semantic_retrieval(query, vector_db)
            
            # 执行关键词检索
            keyword_results = self._keyword_retrieval(query, vector_db)
            
            # 合并结果
            all_results = semantic_results + keyword_results
            
            # 去重并重新计算得分
            unique_results = self._deduplicate_and_merge_results(all_results)
            
            # 计算混合得分
            for result in unique_results:
                semantic_score = result.relevance_factors.get('semantic_similarity', 0)
                keyword_score = result.relevance_factors.get('keyword_match', 0)
                
                # 混合得分计算
                hybrid_score = (semantic_score * 0.6 + keyword_score * 0.4)
                result.score = hybrid_score
                result.strategy = RetrievalStrategy.HYBRID
                result.relevance_factors['hybrid_score'] = hybrid_score
            
            return unique_results
            
        except Exception as e:
            if self._is_empty_query_error(e):
                logger.debug(f"混合检索跳过（空查询）: {e}")
            else:
                logger.error(f"混合检索失败: {e}")
            return []
    
    def _context_aware_retrieval(self, query: str, vector_db, context: Optional[str] = None) -> List[RetrievalResult]:
        """上下文感知检索"""
        try:
            # 构建上下文增强查询
            enhanced_query = self._build_context_aware_query(query, context)
            
            # 执行混合检索
            results = self._hybrid_retrieval(enhanced_query, vector_db)
            
            # 应用上下文权重调整
            for result in results:
                context_score = self._calculate_context_relevance(result.content, context)
                result.score = result.score * (1 + context_score * 0.2)  # 上下文权重20%
                result.strategy = RetrievalStrategy.CONTEXT_AWARE
                result.relevance_factors['context_relevance'] = context_score
            
            return results
            
        except Exception as e:
            logger.error(f"上下文感知检索失败: {e}")
            return []
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        提取查询关键词（增强版：整合 RequirementKeywordExtractor）
        
        Args:
            query: 查询文本
            
        Returns:
            关键词列表
        """
        # 如果启用了增强关键词提取，使用 RequirementKeywordExtractor
        if self._enhanced_keyword_extraction and self.keyword_extractor:
            try:
                # 使用 RequirementKeywordExtractor 提取核心概念
                core_concepts = self.keyword_extractor.extract_core_concepts(query)
                
                # 合并所有关键词
                keywords = set()
                keywords.update(core_concepts['keywords'])
                keywords.update(core_concepts['entities'])
                keywords.update(core_concepts['tech_terms'])
                
                # 添加重要短语（限制长度）
                for phrase in core_concepts['phrases']:
                    if 2 <= len(phrase) <= 8:
                        keywords.add(phrase)
                
                return list(keywords)
            except Exception as e:
                logger.warning(f"增强关键词提取失败，回退到简单提取: {e}")
        
        # 回退到简单关键词提取（原有逻辑）
        all_keywords = self.keyword_config.get_all_keywords()
        exclude_keywords = self.keyword_config.get_exclude_keywords()
        
        # 简单的关键词提取
        query_words = query.lower().split()
        keywords = []
        
        for word in query_words:
            if word in all_keywords and word not in exclude_keywords:
                keywords.append(word)
        
        return keywords
    
    @staticmethod
    def _calculate_keyword_score(content: str, keywords: List[str]) -> float:
        """计算关键词匹配得分"""
        if not keywords:
            return 0.0
        
        content_lower = content.lower()
        matches = sum(1 for keyword in keywords if keyword in content_lower)
        return matches / len(keywords)
    
    @staticmethod
    def _calculate_context_relevance(content: str, context: Optional[str] = None) -> float:
        """计算上下文相关性"""
        if not context:
            return 0.0
        
        # 计算文本相似度
        try:
            from difflib import SequenceMatcher
            if not content and not context:
                return 1.0
            if not content or not context:
                return 0.0
            similarity = SequenceMatcher(None, content, context).ratio()
            return similarity
        except (AttributeError, TypeError, ValueError):
            return 0.0
    
    def _build_context_aware_query(self, query: str, context: Optional[str] = None) -> str:
        """
        构建上下文感知查询（增强版：支持查询扩展）
        
        Args:
            query: 原始查询文本
            context: 上下文信息
            
        Returns:
            增强后的查询文本
        """
        enhanced_parts = [query]
        
        # 如果启用了查询扩展，使用 RequirementKeywordExtractor 提取核心概念
        if self.config.enable_query_expansion and self._enhanced_keyword_extraction and self.keyword_extractor:
            try:
                core_concepts = self.keyword_extractor.extract_core_concepts(query)
                
                # 添加技术术语和实体
                if core_concepts['tech_terms']:
                    enhanced_parts.append(' '.join(core_concepts['tech_terms']))
                if core_concepts['entities']:
                    enhanced_parts.append(' '.join(core_concepts['entities']))
                
                # 添加重要短语
                important_phrases = [p for p in core_concepts['phrases'] if len(p) >= 4]
                if important_phrases:
                    enhanced_parts.append(' '.join(important_phrases[:3]))  # 最多3个短语
            except Exception as e:
                logger.debug(f"查询扩展失败: {e}")
        
        # 添加上下文（如果提供）
        if context:
            # 限制上下文长度
            if len(context) > self.config.max_context_length:
                context = context[:self.config.max_context_length]
            enhanced_parts.append(context)
        
        return ' '.join(enhanced_parts)
    
    @staticmethod
    def _deduplicate_and_merge_results(results: List[RetrievalResult]) -> List[RetrievalResult]:
        """去重并合并检索结果"""
        unique_results = {}
        
        for result in results:
            # 使用内容作为唯一标识
            content_key = result.content[:100]  # 使用前100个字符作为键
            
            if content_key not in unique_results:
                unique_results[content_key] = result
            else:
                # 合并得分和相关性因子
                existing = unique_results[content_key]
                existing.score = max(existing.score, result.score)
                existing.relevance_factors.update(result.relevance_factors)
        
        return list(unique_results.values())
    
    def _rerank_results(self, results: List[RetrievalResult], query: str, context: Optional[str] = None) -> List[RetrievalResult]:
        """重排序检索结果"""
        if not results:
            return results
        
        # 计算重排序得分
        for result in results:
            rerank_score = self._calculate_rerank_score(result, query, context)
            result.score = result.score * 0.7 + rerank_score * 0.3  # 混合原始得分和重排序得分
        
        # 按得分排序
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results
    
    @staticmethod
    def _calculate_rerank_score(result: RetrievalResult, query: str, context: Optional[str] = None) -> float:
        """计算重排序得分"""
        score = 0.0
        
        # 内容长度得分
        content_length = len(result.content)
        if 100 <= content_length <= 1000:
            score += 0.2
        elif content_length > 1000:
            score += 0.1
        
        # 关键词密度得分
        query_words = set(query.lower().split())
        content_words = set(result.content.lower().split())
        keyword_density = len(query_words.intersection(content_words)) / len(query_words)
        score += keyword_density * 0.3
        
        # 上下文相关性得分
        if context:
            context_relevance = result.relevance_factors.get('context_relevance', 0)
            score += context_relevance * 0.2
        
        # 元数据质量得分
        metadata = result.metadata
        if metadata.get('source') and metadata.get('type'):
            score += 0.1
        
        return min(score, 1.0)
    
    def _update_performance_stats(self, strategy: RetrievalStrategy, response_time: float, success: bool):
        """更新性能统计"""
        self.performance_stats['total_queries'] += 1
        self.performance_stats['strategy_usage'][strategy.value] += 1
        
        # 更新平均响应时间
        total_queries = self.performance_stats['total_queries']
        current_avg = self.performance_stats['avg_response_time']
        self.performance_stats['avg_response_time'] = (current_avg * (total_queries - 1) + response_time) / total_queries
        
        # 更新成功率
        if success:
            success_count = self.performance_stats.get('success_count', 0) + 1
            self.performance_stats['success_count'] = success_count
            self.performance_stats['success_rate'] = success_count / total_queries
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        return self.performance_stats.copy()
    
    def reset_performance_stats(self):
        """重置性能统计"""
        self.performance_stats = {
            'total_queries': 0,
            'avg_response_time': 0.0,
            'strategy_usage': {strategy.value: 0 for strategy in RetrievalStrategy},
            'success_rate': 0.0
        }


# 全局实例
_smart_retrieval_strategy: Optional[SmartRetrievalStrategy] = None


def get_smart_retrieval_strategy(config: Optional[RetrievalConfig] = None) -> SmartRetrievalStrategy:
    """获取智能检索策略实例（单例模式）"""
    global _smart_retrieval_strategy
    if _smart_retrieval_strategy is None:
        _smart_retrieval_strategy = SmartRetrievalStrategy(config)
    return _smart_retrieval_strategy


def create_retrieval_config(**kwargs) -> RetrievalConfig:
    """创建检索配置的便捷函数"""
    return RetrievalConfig(**kwargs)
