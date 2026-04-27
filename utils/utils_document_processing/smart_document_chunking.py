#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
智能文档分块模块
实现语义分块、自适应分块大小、重叠优化等功能
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from utils.utils_core.logger import get_logger
from utils.utils_config_management.optimization_config import get_optimization_config

logger = get_logger(__name__)


class ChunkingStrategy(Enum):
    """分块策略枚举"""
    FIXED_SIZE = "fixed_size"        # 固定大小分块
    SEMANTIC = "semantic"            # 语义分块
    ADAPTIVE = "adaptive"            # 自适应分块
    HIERARCHICAL = "hierarchical"    # 层次化分块


class ContentType(Enum):
    """内容类型枚举"""
    TEXT = "text"                    # 普通文本
    CODE = "code"                    # 代码
    TABLE = "table"                  # 表格
    LIST = "list"                    # 列表
    HEADING = "heading"              # 标题
    PARAGRAPH = "paragraph"          # 段落


@dataclass
class ChunkMetadata:
    """分块元数据"""
    chunk_id: str
    content_type: ContentType
    position: int
    length: int
    quality_score: float
    semantic_coherence: float
    overlap_with_previous: int
    overlap_with_next: int


@dataclass
class DocumentChunk:
    """文档分块"""
    content: str
    metadata: ChunkMetadata
    parent_section: Optional[str] = None
    keywords: List[str] = None


@dataclass
class ChunkingConfig:
    """分块配置"""
    strategy: ChunkingStrategy = ChunkingStrategy.ADAPTIVE
    base_chunk_size: int = 1000
    min_chunk_size: int = 200
    max_chunk_size: int = 2000
    overlap_size: int = 200
    enable_semantic_boundary: bool = field(default=True)  # 启用语义边界检测
    enable_content_type_detection: bool = field(default=True)
    enable_quality_assessment: bool = field(default=True)
    quality_threshold: float = 0.7


class SmartDocumentChunker:
    """智能文档分块器"""
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        """
        初始化智能文档分块器
        
        Args:
            config: 分块配置，如果为None则使用默认配置
        """
        self.config: ChunkingConfig = config or ChunkingConfig()
        self.opt_config = get_optimization_config()
        
        # 内容类型检测模式
        self.content_patterns = {
            ContentType.CODE: [
                r'```[\s\S]*?```',  # 代码块
                r'`[^`]+`',         # 行内代码
                r'^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*\(',  # 函数定义
            ],
            ContentType.TABLE: [
                r'\|.*\|',          # Markdown表格
                r'^\s*\|.*\|.*$',   # 表格行
            ],
            ContentType.LIST: [
                r'^\s*[-*+]\s+',    # 无序列表
                r'^\s*\d+\.\s+',    # 有序列表
            ],
            ContentType.HEADING: [
                r'^#{1,6}\s+',      # Markdown标题
                r'^\s*[A-Z][A-Z\s]+$',  # 大写标题
            ],
            ContentType.PARAGRAPH: [
                r'^[A-Za-z\u4e00-\u9fa5]',  # 段落开始
            ]
        }
        
        # 语义边界检测模式
        self.semantic_boundary_patterns = [
            r'[.!?]\s+',            # 句子结束
            r'\n\s*\n',             # 段落分隔
            r'#{1,6}\s+',           # 标题
            r'^\s*[-*+]\s+',        # 列表项
            r'^\s*\d+\.\s+',        # 编号列表
        ]
        
        # 性能统计
        self.performance_stats: Dict[str, Any] = {
            'total_chunks_created': 0,
            'avg_chunk_size': 0.0,
            'quality_scores': [],
            'strategy_usage': {strategy.value: 0 for strategy in ChunkingStrategy}
        }

    def chunk_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        strategy: Optional[ChunkingStrategy] = None
    ) -> List[DocumentChunk]:
        """
        对文档进行智能分块

        Args:
            content: 文档内容
            metadata: 文档元数据
            strategy: 分块策略，如果为None则使用配置中的策略

        Returns:
            文档分块列表
        """
        if not content or not content.strip():
            return []

        strategy = strategy or self.config.strategy

        try:
            # 预处理内容
            processed_content = self._preprocess_content(content)

            # 检测内容类型
            content_type = self._detect_content_type(processed_content)

            # 根据策略执行分块
            if strategy == ChunkingStrategy.FIXED_SIZE:
                chunks = self._fixed_size_chunking(processed_content, content_type)
            elif strategy == ChunkingStrategy.SEMANTIC:
                chunks = self._semantic_chunking(processed_content, content_type)
            elif strategy == ChunkingStrategy.ADAPTIVE:
                chunks = self._adaptive_chunking(processed_content, content_type)
            elif strategy == ChunkingStrategy.HIERARCHICAL:
                chunks = self._hierarchical_chunking(processed_content, content_type)
            else:
                chunks = self._adaptive_chunking(processed_content, content_type)

            # 后处理分块
            chunks = self._postprocess_chunks(chunks, metadata)

            # 更新性能统计
            actual_strategy = strategy if strategy is not None else self.config.strategy
            self._update_performance_stats(actual_strategy, chunks)

            return chunks

        except Exception as e:
            logger.error(f"文档分块失败: {e}")
            return []

    @staticmethod
    def _preprocess_content(content: str) -> str:
        """预处理文档内容"""
        # 标准化换行符
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # 移除多余的空白字符
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # 移除行首行尾空白
        lines = content.split('\n')
        lines = [line.rstrip() for line in lines]
        content = '\n'.join(lines)
        
        return content.strip()
    
    def _detect_content_type(self, content: str) -> ContentType:
        """检测内容类型"""
        if not self.config.enable_content_type_detection:
            return ContentType.TEXT
        
        # 计算各种内容类型的匹配度
        type_scores = {}
        
        for content_type, patterns in self.content_patterns.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, content, re.MULTILINE)
                score += len(matches)
            
            type_scores[content_type] = score
        
        # 返回得分最高的内容类型
        if type_scores:
            return max(type_scores.items(), key=lambda x: x[1])[0]
        
        return ContentType.TEXT
    
    def _fixed_size_chunking(self, content: str, content_type: ContentType) -> List[DocumentChunk]:
        """固定大小分块"""
        chunks = []
        chunk_size = self.config.base_chunk_size
        overlap = self.config.overlap_size
        
        start = 0
        chunk_id = 0
        
        while start < len(content):
            end = min(start + chunk_size, len(content))
            
            # 尝试在语义边界处分割
            if self.config.enable_semantic_boundary and end < len(content):
                boundary_pos = self._find_semantic_boundary(content, start, end)
                if boundary_pos > start:
                    end = boundary_pos
            
            chunk_content = content[start:end]
            
            # 创建分块
            chunk = self._create_chunk(
                content=chunk_content,
                chunk_id=f"chunk_{chunk_id}",
                position=start,
                content_type=content_type
            )
            
            chunks.append(chunk)
            
            # 计算下一个分块的起始位置
            start = max(start + chunk_size - overlap, end)
            chunk_id += 1
        
        return chunks
    
    def _semantic_chunking(self, content: str, content_type: ContentType) -> List[DocumentChunk]:
        """语义分块"""
        chunks = []
        
        # 找到所有语义边界
        boundaries = self._find_all_semantic_boundaries(content)
        
        if not boundaries:
            # 如果没有找到语义边界，使用固定大小分块
            return self._fixed_size_chunking(content, content_type)
        
        # 根据语义边界创建分块
        start = 0
        chunk_id = 0
        
        for boundary in boundaries:
            if boundary <= start:
                continue
            
            chunk_content = content[start:boundary]
            
            # 检查分块大小是否合适
            if len(chunk_content) < self.config.min_chunk_size:
                continue
            
            # 如果分块太大，需要进一步分割
            if len(chunk_content) > self.config.max_chunk_size:
                sub_chunks = self._split_large_chunk(chunk_content, start, chunk_id)
                chunks.extend(sub_chunks)
                chunk_id += len(sub_chunks)
            else:
                chunk = self._create_chunk(
                    content=chunk_content,
                    chunk_id=f"chunk_{chunk_id}",
                    position=start,
                    content_type=content_type
                )
                chunks.append(chunk)
                chunk_id += 1
            
            start = boundary
        
        # 处理剩余内容
        if start < len(content):
            remaining_content = content[start:]
            if len(remaining_content) >= self.config.min_chunk_size:
                chunk = self._create_chunk(
                    content=remaining_content,
                    chunk_id=f"chunk_{chunk_id}",
                    position=start,
                    content_type=content_type
                )
                chunks.append(chunk)
        
        return chunks
    
    def _adaptive_chunking(self, content: str, content_type: ContentType) -> List[DocumentChunk]:
        """自适应分块"""
        chunks = []
        
        # 分析内容特征
        content_features = self._analyze_content_features(content)
        
        # 根据内容特征调整分块参数
        adaptive_chunk_size = self._calculate_adaptive_chunk_size(content_features)
        adaptive_overlap = self._calculate_adaptive_overlap(adaptive_chunk_size)
        
        # 使用调整后的参数进行分块
        start = 0
        chunk_id = 0
        
        while start < len(content):
            # 计算当前分块的目标大小
            current_chunk_size = self._get_dynamic_chunk_size(content, start, adaptive_chunk_size)
            end = min(start + current_chunk_size, len(content))
            
            # 寻找最佳分割点
            if end < len(content):
                best_boundary = self._find_best_split_point(content, start, end)
                if best_boundary > start:
                    end = best_boundary
            
            chunk_content = content[start:end]
            
            # 创建分块
            chunk = self._create_chunk(
                content=chunk_content,
                chunk_id=f"chunk_{chunk_id}",
                position=start,
                content_type=content_type
            )
            
            chunks.append(chunk)
            
            # 计算下一个分块的起始位置
            start = max(start + current_chunk_size - adaptive_overlap, end)
            chunk_id += 1
        
        return chunks
    
    def _hierarchical_chunking(self, content: str, content_type: ContentType) -> List[DocumentChunk]:
        """层次化分块"""
        chunks = []
        
        # 首先按主要结构分割（如标题）
        major_sections = self._split_by_major_structure(content)
        
        chunk_id = 0
        for section_start, section_end, section_title in major_sections:
            section_content = content[section_start:section_end]
            
            # 对每个主要部分进行子分块
            sub_chunks = self._adaptive_chunking(section_content, content_type)
            
            # 为子分块添加父级信息
            for sub_chunk in sub_chunks:
                sub_chunk.parent_section = section_title
                sub_chunk.metadata.chunk_id = f"chunk_{chunk_id}"
                chunks.append(sub_chunk)
                chunk_id += 1
        
        return chunks
    
    def _find_semantic_boundary(self, content: str, start: int, end: int) -> int:
        """在指定范围内查找语义边界"""
        search_content = content[start:end]
        
        for pattern in self.semantic_boundary_patterns:
            matches = list(re.finditer(pattern, search_content))
            if matches:
                # 返回最后一个匹配的位置
                last_match = matches[-1]
                return start + last_match.end()
        
        return end
    
    def _find_all_semantic_boundaries(self, content: str) -> List[int]:
        """查找所有语义边界"""
        boundaries = []
        
        for pattern in self.semantic_boundary_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                boundaries.append(match.end())
        
        # 去重并排序
        boundaries = sorted(list(set(boundaries)))
        
        return boundaries
    
    def _split_large_chunk(self, content: str, start_pos: int, base_chunk_id: int) -> List[DocumentChunk]:
        """分割过大的分块"""
        chunks = []
        chunk_size = self.config.base_chunk_size
        overlap = self.config.overlap_size
        
        sub_start = 0
        sub_chunk_id = 0
        
        while sub_start < len(content):
            sub_end = min(sub_start + chunk_size, len(content))
            
            # 寻找语义边界
            if sub_end < len(content):
                boundary = self._find_semantic_boundary(content, sub_start, sub_end)
                if boundary > sub_start:
                    sub_end = boundary
            
            sub_content = content[sub_start:sub_end]
            
            chunk = self._create_chunk(
                content=sub_content,
                chunk_id=f"chunk_{base_chunk_id}_{sub_chunk_id}",
                position=start_pos + sub_start,
                content_type=ContentType.TEXT
            )
            
            chunks.append(chunk)
            
            sub_start = max(sub_start + chunk_size - overlap, sub_end)
            sub_chunk_id += 1
        
        return chunks
    
    def _analyze_content_features(self, content: str) -> Dict[str, Any]:
        """分析内容特征"""
        features = {
            'length': len(content),
            'line_count': content.count('\n'),
            'paragraph_count': len(re.findall(r'\n\s*\n', content)),
            'sentence_count': len(re.findall(r'[.!?]+', content)),
            'avg_sentence_length': 0,
            'complexity_score': 0.0
        }
        
        # 计算平均句子长度
        sentences = re.split(r'[.!?]+', content)
        if sentences:
            features['avg_sentence_length'] = int(sum(len(s.split()) for s in sentences) / len(sentences))

        # 计算复杂度得分
        features['complexity_score'] = self._calculate_complexity_score(content)
        
        return features
    
    @staticmethod
    def _calculate_complexity_score(content: str) -> float:
        """计算内容复杂度得分"""
        score = 0.0
        
        # 基于句子长度
        sentences = re.split(r'[.!?]+', content)
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            score += min(avg_sentence_length / 20.0, 1.0) * 0.3
        
        # 基于词汇多样性
        words = content.lower().split()
        if words:
            unique_words = len(set(words))
            diversity = unique_words / len(words)
            score += diversity * 0.4
        
        # 基于结构复杂度
        structure_elements = len(re.findall(r'[.!?]', content))
        if structure_elements > 0:
            structure_score = min(structure_elements / 50.0, 1.0)
            score += structure_score * 0.3
        
        return min(score, 1.0)
    
    def _calculate_adaptive_chunk_size(self, features: Dict[str, Any]) -> int:
        """计算自适应分块大小"""
        base_size = self.config.base_chunk_size
        
        # 根据内容长度调整
        if features['length'] < 5000:
            size_multiplier = 0.8
        elif features['length'] < 20000:
            size_multiplier = 1.0
        else:
            size_multiplier = 1.2
        
        # 根据复杂度调整
        complexity = features['complexity_score']
        if complexity > 0.7:
            size_multiplier *= 0.8  # 复杂内容使用更小的分块
        elif complexity < 0.3:
            size_multiplier *= 1.2  # 简单内容可以使用更大的分块
        
        adaptive_size = int(base_size * size_multiplier)
        
        return max(self.config.min_chunk_size, 
                  min(adaptive_size, self.config.max_chunk_size))
    
    def _calculate_adaptive_overlap(self, chunk_size: int) -> int:
        """计算自适应重叠大小"""
        # 重叠大小通常是分块大小的10-20%
        overlap_ratio = 0.15
        adaptive_overlap = int(chunk_size * overlap_ratio)
        
        return max(50, min(adaptive_overlap, self.config.overlap_size))
    
    @staticmethod
    def _get_dynamic_chunk_size(content: str, start: int, base_size: int) -> int:
        """获取动态分块大小"""
        # 检查当前位置附近的内容特征
        window_size = min(200, len(content) - start)
        window_content = content[start:start + window_size]
        
        # 如果遇到列表或表格，调整分块大小
        if re.search(r'^\s*[-*+]\s+', window_content, re.MULTILINE):
            return min(base_size, 500)  # 列表使用较小的分块
        
        if re.search(r'\|.*\|', window_content):
            return min(base_size, 800)  # 表格使用中等分块
        
        return base_size
    
    @staticmethod
    def _find_best_split_point(content: str, start: int, end: int) -> int:
        """寻找最佳分割点"""
        search_content = content[start:end]
        
        # 优先级：段落边界 > 句子边界 > 词边界
        for pattern in [r'\n\s*\n', r'[.!?]\s+', r'\s+']:
            matches = list(re.finditer(pattern, search_content))
            if matches:
                # 选择最接近末尾的匹配
                best_match = None
                for match in matches:
                    if match.end() > len(search_content) * 0.7:  # 在70%位置之后
                        best_match = match
                        break
                
                if best_match:
                    return start + best_match.end()
        
        return end
    
    @staticmethod
    def _split_by_major_structure(content: str) -> List[Tuple[int, int, str]]:
        """按主要结构分割内容"""
        sections = []
        
        # 查找标题
        heading_pattern = r'^(#{1,6}\s+.+)$'
        matches = list(re.finditer(heading_pattern, content, re.MULTILINE))
        
        if not matches:
            # 如果没有标题，将整个内容作为一个部分
            return [(0, len(content), "Main Content")]
        
        for i, match in enumerate(matches):
            start = match.start()
            title = match.group(1).strip()
            
            # 确定结束位置
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(content)
            
            sections.append((start, end, title))
        
        return sections
    
    def _create_chunk(
        self, 
        content: str, 
        chunk_id: str, 
        position: int, 
        content_type: ContentType
    ) -> DocumentChunk:
        """创建文档分块"""
        # 计算质量得分
        quality_score = self._calculate_chunk_quality(content) if self.config.enable_quality_assessment else 1.0
        
        # 计算语义连贯性
        semantic_coherence = self._calculate_semantic_coherence(content)
        
        # 创建元数据
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            content_type=content_type,
            position=position,
            length=len(content),
            quality_score=quality_score,
            semantic_coherence=semantic_coherence,
            overlap_with_previous=0,  # 将在后处理中计算
            overlap_with_next=0
        )
        
        # 提取关键词
        keywords = self._extract_keywords(content)
        
        return DocumentChunk(
            content=content,
            metadata=metadata,
            keywords=keywords
        )
    
    def _calculate_chunk_quality(self, content: str) -> float:
        """计算分块质量得分"""
        score = 0.0
        
        # 长度得分
        length = len(content)
        if self.config.min_chunk_size <= length <= self.config.max_chunk_size:
            score += 0.3
        elif length < self.config.min_chunk_size:
            score += 0.1
        else:
            score += 0.2
        
        # 完整性得分（检查是否在句子中间截断）
        if content.endswith(('.', '!', '?', '。', '！', '？')):
            score += 0.3
        elif content.endswith(('\n', ' ', '\t')):
            score += 0.2
        else:
            score += 0.1
        
        # 结构得分
        if re.search(r'[.!?]', content):
            score += 0.2  # 包含句子结束符
        
        if re.search(r'\n', content):
            score += 0.1  # 包含换行符
        
        # 内容密度得分
        words = content.split()
        if words:
            avg_word_length = sum(len(word) for word in words) / len(words)
            if 2 <= avg_word_length <= 10:
                score += 0.2
        
        return min(score, 1.0)
    
    @staticmethod
    def _calculate_semantic_coherence(content: str) -> float:
        """计算语义连贯性"""
        # 简单的语义连贯性计算
        sentences = re.split(r'[.!?]+', content)
        if len(sentences) < 2:
            return 1.0
        
        # 计算句子间的词汇重叠
        total_overlap = 0
        for i in range(len(sentences) - 1):
            words1 = set(sentences[i].lower().split())
            words2 = set(sentences[i + 1].lower().split())
            
            if words1 and words2:
                overlap = len(words1.intersection(words2)) / len(words1.union(words2))
                total_overlap += overlap
        
        return total_overlap / (len(sentences) - 1) if len(sentences) > 1 else 1.0
    
    @staticmethod
    def _extract_keywords(content: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取
        words = re.findall(r'\b\w+\b', content.lower())
        
        # 过滤停用词和短词
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        # 返回最常见的词
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:10]]  # 返回前10个关键词
    
    def _postprocess_chunks(self, chunks: List[DocumentChunk], metadata: Optional[Dict[str, Any]]) -> List[DocumentChunk]:
        """后处理分块"""
        if not chunks:
            return chunks
        
        # 计算重叠信息
        for i in range(len(chunks)):
            if i > 0:
                prev_chunk = chunks[i - 1]
                curr_chunk = chunks[i]
                overlap = self._calculate_overlap(prev_chunk.content, curr_chunk.content)
                curr_chunk.metadata.overlap_with_previous = overlap
                prev_chunk.metadata.overlap_with_next = overlap
        
        # 过滤低质量分块
        if self.config.enable_quality_assessment:
            chunks = [chunk for chunk in chunks if chunk.metadata.quality_score >= self.config.quality_threshold]
        
        # 添加文档元数据
        if metadata:
            for chunk in chunks:
                chunk.metadata.chunk_id = f"{metadata.get('source', 'doc')}_{chunk.metadata.chunk_id}"
        
        return chunks
    
    def _calculate_overlap(self, content1: str, content2: str) -> int:
        """计算两个分块的重叠长度"""
        # 简单的重叠计算：检查末尾和开头的相同内容
        max_overlap = min(len(content1), len(content2), self.config.overlap_size)
        
        for i in range(max_overlap, 0, -1):
            if content1[-i:] == content2[:i]:
                return i
        
        return 0
    
    def _update_performance_stats(self, strategy: ChunkingStrategy, chunks: List[DocumentChunk]):
        """更新性能统计"""
        self.performance_stats['total_chunks_created'] += len(chunks)
        self.performance_stats['strategy_usage'][strategy.value] += 1
        
        if chunks:
            avg_size = sum(chunk.metadata.length for chunk in chunks) / len(chunks)
            self.performance_stats['avg_chunk_size'] = avg_size
            
            if self.config.enable_quality_assessment:
                quality_scores = [chunk.metadata.quality_score for chunk in chunks]
                self.performance_stats['quality_scores'].extend(quality_scores)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        stats = self.performance_stats.copy()
        
        if stats['quality_scores']:
            stats['avg_quality_score'] = sum(stats['quality_scores']) / len(stats['quality_scores'])
        else:
            stats['avg_quality_score'] = 0.0
        
        return stats
    
    def reset_performance_stats(self):
        """重置性能统计"""
        self.performance_stats = {
            'total_chunks_created': 0,
            'avg_chunk_size': 0.0,
            'quality_scores': [],
            'strategy_usage': {strategy.value: 0 for strategy in ChunkingStrategy}
        }


# 全局实例
_smart_document_chunker: Optional[SmartDocumentChunker] = None


def get_smart_document_chunker(config: Optional[ChunkingConfig] = None) -> SmartDocumentChunker:
    """获取智能文档分块器实例（单例模式）"""
    global _smart_document_chunker
    if _smart_document_chunker is None:
        _smart_document_chunker = SmartDocumentChunker(config)
    return _smart_document_chunker


def create_chunking_config(**kwargs) -> ChunkingConfig:
    """创建分块配置的便捷函数"""
    # 处理字符串到枚举的转换
    if 'strategy' in kwargs and isinstance(kwargs['strategy'], str):
        strategy_map = {
            'fixed_size': ChunkingStrategy.FIXED_SIZE,
            'semantic': ChunkingStrategy.SEMANTIC,
            'adaptive': ChunkingStrategy.ADAPTIVE,
            'hierarchical': ChunkingStrategy.HIERARCHICAL
        }
        kwargs['strategy'] = strategy_map.get(kwargs['strategy'], ChunkingStrategy.ADAPTIVE)
    
    return ChunkingConfig(**kwargs)
