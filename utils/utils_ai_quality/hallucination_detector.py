#!/usr/bin/env python3
"""
幻觉检测模块
用于检测AI生成内容中的幻觉、不准确信息和逻辑矛盾
"""

import re
from typing import Dict, List, Any
from dataclasses import dataclass
from difflib import SequenceMatcher
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class HallucinationResult:
    """幻觉检测结果"""
    is_hallucination: bool
    confidence: float
    issues: List[str]
    suggestions: List[str]
    source_verification: Dict[str, Any]


class HallucinationDetector:
    """幻觉检测器"""
    
    def __init__(self, similarity_threshold: float = 0.8, confidence_threshold: float = 0.7):
        """
        初始化幻觉检测器
        
        Args:
            similarity_threshold: 相似度阈值
            confidence_threshold: 置信度阈值
        """
        self.similarity_threshold = similarity_threshold
        self.confidence_threshold = confidence_threshold
        
        # 常见幻觉模式
        self.hallucination_patterns = [
            r'根据.*?研究表明',  # 虚假引用
            r'专家.*?认为',      # 未验证的专家观点
            r'众所周知',        # 模糊表述
            r'一般来说',        # 过度概括
            r'通常情况下',      # 缺乏具体性
            r'大多数.*?都',     # 统计性表述
            r'经过.*?验证',     # 未验证的声明
        ]
        
        # 逻辑矛盾关键词
        self.contradiction_keywords = [
            ('必须', '不能'),
            ('总是', '从不'),
            ('所有', '没有'),
            ('完全', '部分'),
            ('绝对', '可能'),
        ]
        
        # 事实性检查关键词
        self.factual_keywords = [
            '数据', '统计', '研究', '报告', '调查', '实验',
            '证明', '证实', '验证', '测试', '分析'
        ]

    def detect_hallucination(self, 
                           generated_content: str, 
                           source_documents: List[Dict[str, Any]] = None,
                           context: str = None) -> HallucinationResult:
        """
        检测生成内容中的幻觉
        
        Args:
            generated_content: AI生成的内容
            source_documents: 源文档列表
            context: 上下文信息
            
        Returns:
            幻觉检测结果
        """
        try:
            issues = []
            
            # 1. 模式匹配检测
            pattern_issues = self._detect_pattern_hallucination(generated_content)
            issues.extend(pattern_issues)
            
            # 2. 逻辑一致性检测
            logic_issues = self._detect_logic_contradictions(generated_content)
            issues.extend(logic_issues)
            
            # 3. 事实性验证
            factual_issues = self._detect_factual_inconsistencies(generated_content, source_documents)
            issues.extend(factual_issues)
            
            # 4. 内容一致性检查
            consistency_issues = self._detect_content_inconsistency(generated_content, source_documents)
            issues.extend(consistency_issues)
            
            # 5. 来源验证
            source_verification = self._verify_sources(generated_content, source_documents)
            
            # 6. 上下文一致性检查（如果提供上下文）
            if context:
                context_issues = self._check_context_consistency(generated_content, context)
                issues.extend(context_issues)
            
            # 计算置信度
            confidence = self._calculate_confidence(issues, generated_content)
            
            # 生成建议
            suggestions = self._generate_suggestions(issues, generated_content)
            
            # 判断是否为幻觉
            is_hallucination = len(issues) > 0 and confidence > self.confidence_threshold
            
            return HallucinationResult(
                is_hallucination=is_hallucination,
                confidence=confidence,
                issues=issues,
                suggestions=suggestions,
                source_verification=source_verification
            )
            
        except Exception as e:
            logger.error(f"幻觉检测失败: {str(e)}")
            return HallucinationResult(
                is_hallucination=False,
                confidence=0.0,
                issues=[f"检测过程出错: {str(e)}"],
                suggestions=["请检查输入内容的格式"],
                source_verification={}
            )

    def _detect_pattern_hallucination(self, content: str) -> List[str]:
        """检测模式化幻觉"""
        issues = []
        
        for pattern in self.hallucination_patterns:
            matches = re.findall(pattern, content)
            if matches:
                issues.append(f"检测到可能的幻觉模式: '{matches[0]}' - 缺乏具体依据")
        
        return issues

    def _detect_logic_contradictions(self, content: str) -> List[str]:
        """检测逻辑矛盾"""
        issues = []
        
        for positive, negative in self.contradiction_keywords:
            if positive in content and negative in content:
                issues.append(f"检测到逻辑矛盾: 同时包含'{positive}'和'{negative}'")
        
        return issues

    def _detect_factual_inconsistencies(self, content: str, source_documents: List[Dict[str, Any]] = None) -> List[str]:
        """检测事实性不一致"""
        issues = []
        
        if not source_documents:
            return issues
        
        # 检查事实性关键词
        factual_claims = []
        for keyword in self.factual_keywords:
            if keyword in content:
                factual_claims.append(keyword)
        
        if factual_claims and not source_documents:
            issues.append(f"内容包含事实性声明 {factual_claims}，但缺乏源文档支持")
        
        return issues

    def _detect_content_inconsistency(self, content: str, source_documents: List[Dict[str, Any]] = None) -> List[str]:
        """检测内容一致性"""
        issues = []
        
        if not source_documents:
            return issues
        
        # 计算与源文档的相似度
        max_similarity = 0.0
        for doc in source_documents:
            doc_content = doc.get('content', '') or doc.get('page_content', '')
            if doc_content:
                similarity = SequenceMatcher(None, content, doc_content).ratio()
                max_similarity = max(max_similarity, similarity)
        
        if max_similarity < self.similarity_threshold:
            issues.append(f"生成内容与源文档相似度过低 ({max_similarity:.2f})，可能存在幻觉")
        
        return issues

    @staticmethod
    def _check_context_consistency(content: str, context: str) -> List[str]:
        """检查与上下文的一致性"""
        issues = []
        
        # 简单的上下文一致性检查
        if context and content:
            # 检查内容是否偏离了上下文主题
            context_words = set(context.lower().split())
            content_words = set(content.lower().split())
            
            # 计算词汇重叠度
            if context_words and content_words:
                overlap = len(context_words.intersection(content_words))
                total_unique = len(context_words.union(content_words))
                
                if total_unique > 0:
                    overlap_ratio = overlap / total_unique
                    if overlap_ratio < 0.1:  # 重叠度太低
                        issues.append(f"生成内容与上下文关联度过低 ({overlap_ratio:.2f})，可能存在偏离主题")
        
        return issues

    @staticmethod
    def _verify_sources(content: str, source_documents: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """验证来源"""
        verification = {
            'has_sources': bool(source_documents),
            'source_count': len(source_documents) if source_documents else 0,
            'source_quality': 0.0,
            'coverage': 0.0
        }
        
        if source_documents:
            # 计算源文档质量
            quality_scores = []
            for doc in source_documents:
                quality = doc.get('quality_score', 0.5)
                quality_scores.append(quality)
            
            verification['source_quality'] = sum(quality_scores) / len(quality_scores)
            
            # 计算覆盖率
            total_source_length = sum(len(doc.get('content', '') or doc.get('page_content', '')) for doc in source_documents)
            if total_source_length > 0:
                verification['coverage'] = min(len(content) / total_source_length, 1.0)
        
        return verification

    @staticmethod
    def _calculate_confidence(issues: List[str], content: str) -> float:
        """计算置信度"""
        if not issues:
            return 0.0
        
        # 基于问题数量计算基础置信度
        base_confidence = min(len(issues) / 3.0, 1.0)  # 最多3个问题，每个问题0.33
        
        # 根据内容长度调整（避免短内容置信度过低）
        if len(content) < 50:
            length_factor = 0.8  # 短内容也给予较高置信度
        else:
            length_factor = min(len(content) / 500.0, 1.0)  # 500字符为基准
        
        return min(base_confidence * length_factor, 1.0)

    @staticmethod
    def _generate_suggestions(issues: List[str], content: str) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if not issues:
            return suggestions
        
        # 基于问题类型生成建议
        if any('幻觉模式' in issue for issue in issues):
            suggestions.append("避免使用模糊表述，提供具体的事实依据")
        
        if any('逻辑矛盾' in issue for issue in issues):
            suggestions.append("检查内容中的逻辑一致性，避免自相矛盾的表述")
        
        if any('相似度过低' in issue for issue in issues):
            suggestions.append("确保生成内容与源文档保持一致")
        
        if any('缺乏源文档' in issue for issue in issues):
            suggestions.append("为事实性声明提供可靠的源文档支持")
        
        if any('关联度过低' in issue for issue in issues):
            suggestions.append("确保生成内容与上下文主题保持一致")
        
        # 基于内容长度提供额外建议
        if len(content) < 50:
            suggestions.append("内容过于简短，建议提供更详细的说明")
        elif len(content) > 1000:
            suggestions.append("内容较长，建议检查是否包含冗余信息")
        
        return suggestions

    def batch_detect(self, contents: List[str], source_documents: List[Dict[str, Any]] = None) -> List[HallucinationResult]:
        """批量检测"""
        results = []
        
        for content in contents:
            result = self.detect_hallucination(content, source_documents)
            results.append(result)
        
        return results

    @staticmethod
    def generate_detection_report(results: List[HallucinationResult]) -> Dict[str, Any]:
        """生成检测报告"""
        total_count = len(results)
        hallucination_count = sum(1 for r in results if r.is_hallucination)
        
        avg_confidence = sum(r.confidence for r in results) / total_count if results else 0.0
        
        # 统计问题类型
        issue_types = {}
        for result in results:
            for issue in result.issues:
                issue_type = issue.split(':')[0] if ':' in issue else '其他'
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
        
        return {
            'total_count': total_count,
            'hallucination_count': hallucination_count,
            'hallucination_rate': hallucination_count / total_count if total_count > 0 else 0.0,
            'avg_confidence': avg_confidence,
            'issue_types': issue_types,
            'results': [
                {
                    'is_hallucination': r.is_hallucination,
                    'confidence': r.confidence,
                    'issues': r.issues,
                    'suggestions': r.suggestions
                }
                for r in results
            ]
        }


def create_hallucination_detector(similarity_threshold: float = 0.8, 
                                 confidence_threshold: float = 0.7) -> HallucinationDetector:
    """创建幻觉检测器实例"""
    return HallucinationDetector(similarity_threshold, confidence_threshold)
