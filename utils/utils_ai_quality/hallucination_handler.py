#!/usr/bin/env python3
"""
幻觉处理模块
用于处理检测到的幻觉问题，包括自动修正、重新生成、用户提示等功能
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass
from utils.utils_core.logger import get_logger
from utils.utils_ai_quality.hallucination_detector import HallucinationResult

logger = get_logger(__name__)


class HallucinationAction(Enum):
    """幻觉处理动作"""
    WARN_ONLY = "warn_only"           # 仅警告
    FILTER_OUT = "filter_out"         # 过滤掉
    REGENERATE = "regenerate"         # 重新生成
    MANUAL_REVIEW = "manual_review"   # 人工审核
    AUTO_CORRECT = "auto_correct"     # 自动修正


@dataclass
class HallucinationHandlingResult:
    """幻觉处理结果"""
    action_taken: HallucinationAction
    processed_content: str
    is_approved: bool
    warnings: List[str]
    suggestions: List[str]
    metadata: Dict[str, Any]


class HallucinationHandler:
    """幻觉处理器"""
    
    def __init__(self, 
                 warn_threshold: float = 0.3,
                 auto_correct_threshold: float = 0.5,
                 regenerate_threshold: float = 0.7,
                 filter_threshold: float = 0.9,
                 max_regenerate_attempts: int = 2):
        """
        初始化幻觉处理器
        
        Args:
            warn_threshold: 警告阈值 - 低于此值认为内容质量良好
            auto_correct_threshold: 自动修正阈值 - 轻微问题，可自动修正
            regenerate_threshold: 重新生成阈值 - 中等问题，需要重新生成
            filter_threshold: 过滤阈值 - 严重问题，直接过滤
            max_regenerate_attempts: 最大重新生成次数 - 防止死循环
        """
        self.warn_threshold = warn_threshold
        self.auto_correct_threshold = auto_correct_threshold
        self.regenerate_threshold = regenerate_threshold
        self.filter_threshold = filter_threshold
        self.max_regenerate_attempts = max_regenerate_attempts
    
    def handle_hallucination(self, 
                            content: str,
                            detection_result: HallucinationResult,
                            context: Optional[str] = None,
                            llm=None) -> HallucinationHandlingResult:
        """
        处理检测到的幻觉
        
        Args:
            content: 原始内容
            detection_result: 检测结果
            context: 上下文信息
            llm: 语言模型实例（用于重新生成）
            
        Returns:
            处理结果
        """
        try:
            # 确定处理策略
            action = self._determine_action(detection_result)
            
            # 执行处理
            if action == HallucinationAction.WARN_ONLY:
                return self._warn_only(content, detection_result)
            elif action == HallucinationAction.FILTER_OUT:
                return self._filter_out(content, detection_result)
            elif action == HallucinationAction.REGENERATE:
                return self._regenerate(content, detection_result, context, llm)
            elif action == HallucinationAction.AUTO_CORRECT:
                return self._auto_correct(content, detection_result)
            else:  # MANUAL_REVIEW
                return self._manual_review(content, detection_result)
                
        except Exception as e:
            logger.error(f"幻觉处理失败: {e}")
            return HallucinationHandlingResult(
                action_taken=HallucinationAction.WARN_ONLY,
                processed_content=content,
                is_approved=False,
                warnings=[f"处理失败: {str(e)}"],
                suggestions=["请手动检查内容"],
                metadata={"error": str(e)}
            )
    
    def _determine_action(self, detection_result: HallucinationResult) -> HallucinationAction:
        """
        确定处理策略
        
        科学的处理逻辑：
        - 置信度 < 0.3: 内容质量良好，仅警告
        - 置信度 0.3-0.5: 轻微问题，自动修正
        - 置信度 0.5-0.7: 中等问题，重新生成
        - 置信度 0.7-0.9: 严重问题，人工审核
        - 置信度 >= 0.9: 极严重问题，直接过滤
        """
        confidence = detection_result.confidence
        
        # 如果没有检测到问题，直接通过
        if not detection_result.is_hallucination:
            return HallucinationAction.WARN_ONLY
        
        # 根据置信度确定处理策略
        if confidence >= self.filter_threshold:
            return HallucinationAction.FILTER_OUT
        elif confidence >= self.regenerate_threshold:
            return HallucinationAction.MANUAL_REVIEW  # 严重问题需要人工审核
        elif confidence >= self.auto_correct_threshold:
            return HallucinationAction.REGENERATE
        elif confidence >= self.warn_threshold:
            return HallucinationAction.AUTO_CORRECT
        else:
            return HallucinationAction.WARN_ONLY
    
    @staticmethod
    def _warn_only(content: str, detection_result: HallucinationResult) -> HallucinationHandlingResult:
        """仅警告处理"""
        warnings = [
            f"检测到潜在幻觉（置信度: {detection_result.confidence:.2f}）",
            "建议人工审核以下问题："
        ]
        warnings.extend(detection_result.issues)
        
        return HallucinationHandlingResult(
            action_taken=HallucinationAction.WARN_ONLY,
            processed_content=content,
            is_approved=True,  # 仍然返回内容，但带警告
            warnings=warnings,
            suggestions=detection_result.suggestions,
            metadata={
                "confidence": detection_result.confidence,
                "issues_count": len(detection_result.issues)
            }
        )
    
    @staticmethod
    def _filter_out(content: str, detection_result: HallucinationResult) -> HallucinationHandlingResult:
        """过滤掉内容"""
        # 记录被过滤的内容长度，用于统计
        content_length = len(content) if content else 0
        
        return HallucinationHandlingResult(
            action_taken=HallucinationAction.FILTER_OUT,
            processed_content="",  # 清空内容
            is_approved=False,
            warnings=[
                f"内容因幻觉问题被过滤（置信度: {detection_result.confidence:.2f}）",
                f"原始内容长度: {content_length} 字符",
                "检测到的问题："
            ] + detection_result.issues,
            suggestions=[
                "建议重新生成内容",
                "检查源文档质量"
            ] + detection_result.suggestions,
            metadata={
                "confidence": detection_result.confidence,
                "filtered": True,
                "original_length": content_length
            }
        )
    
    def _regenerate(self, content: str, detection_result: HallucinationResult, 
                   context: Optional[str], llm, regenerate_count: int = 0) -> HallucinationHandlingResult:
        """
        重新生成内容（带重试限制）
        
        Args:
            content: 原始内容
            detection_result: 检测结果
            context: 上下文
            llm: 语言模型
            regenerate_count: 当前重试次数
        """
        if not llm:
            logger.warning("无法重新生成：LLM实例未提供")
            return self._warn_only(content, detection_result)
        
        # 检查重试次数限制
        if regenerate_count >= self.max_regenerate_attempts:
            logger.warning(f"重新生成次数已达上限({self.max_regenerate_attempts})，降级为警告处理")
            return self._warn_only(content, detection_result)
        
        try:
            # 构建重新生成的提示
            regenerate_prompt = self._build_regenerate_prompt(content, detection_result, context, regenerate_count)
            
            # 调用LLM重新生成
            response = llm.invoke([{"role": "user", "content": regenerate_prompt}])
            new_content = response.content if hasattr(response, 'content') else str(response)
            
            # 检查重新生成的内容是否为空或过短
            if not new_content or len(new_content.strip()) < 10:
                logger.warning("重新生成的内容为空或过短，降级为警告处理")
                return self._warn_only(content, detection_result)
            
            # 检查重新生成的内容是否与原始内容过于相似（避免无意义的重新生成）
            similarity = self._calculate_content_similarity(content, new_content)
            if similarity > 0.9:
                logger.warning(f"重新生成的内容与原始内容过于相似({similarity:.2f})，降级为警告处理")
                return self._warn_only(content, detection_result)
            
            return HallucinationHandlingResult(
                action_taken=HallucinationAction.REGENERATE,
                processed_content=new_content,
                is_approved=True,
                warnings=[
                    f"内容已重新生成（原置信度: {detection_result.confidence:.2f}，重试次数: {regenerate_count + 1}）"
                ],
                suggestions=[
                    "请检查重新生成的内容质量",
                    "如仍有问题，建议人工审核"
                ],
                metadata={
                    "original_confidence": detection_result.confidence,
                    "regenerated": True,
                    "regenerate_count": regenerate_count + 1,
                    "similarity": similarity
                }
            )
            
        except Exception as e:
            logger.error(f"重新生成失败: {e}")
            # 如果重试次数未达上限，可以尝试再次生成
            if regenerate_count < self.max_regenerate_attempts - 1:
                logger.info(f"重新生成失败，尝试第{regenerate_count + 2}次生成")
                return self._regenerate(content, detection_result, context, llm, regenerate_count + 1)
            else:
                logger.warning("重新生成失败次数过多，降级为警告处理")
                return self._warn_only(content, detection_result)
    
    def _auto_correct(self, content: str, detection_result: HallucinationResult) -> HallucinationHandlingResult:
        """自动修正内容"""
        corrected_content = content
        
        # 简单的自动修正规则
        for issue in detection_result.issues:
            if "幻觉模式" in issue:
                # 移除或替换幻觉模式
                corrected_content = self._remove_hallucination_patterns(corrected_content)
            elif "逻辑矛盾" in issue:
                # 尝试修正逻辑矛盾
                corrected_content = self._fix_logic_contradictions(corrected_content)
        
        return HallucinationHandlingResult(
            action_taken=HallucinationAction.AUTO_CORRECT,
            processed_content=corrected_content,
            is_approved=True,
            warnings=[
                f"内容已自动修正（原置信度: {detection_result.confidence:.2f}）"
            ],
            suggestions=[
                "请检查修正后的内容",
                "如不满意，建议人工编辑"
            ],
            metadata={
                "original_confidence": detection_result.confidence,
                "auto_corrected": True
            }
        )
    
    @staticmethod
    def _manual_review(content: str, detection_result: HallucinationResult) -> HallucinationHandlingResult:
        """标记为人工审核"""
        return HallucinationHandlingResult(
            action_taken=HallucinationAction.MANUAL_REVIEW,
            processed_content=content,
            is_approved=False,  # 需要人工审核
            warnings=[
                f"内容需要人工审核（置信度: {detection_result.confidence:.2f}）",
                "检测到的问题："
            ] + detection_result.issues,
            suggestions=[
                "请人工审核并修正内容",
                "建议参考以下改进建议："
            ] + detection_result.suggestions,
            metadata={
                "confidence": detection_result.confidence,
                "requires_manual_review": True
            }
        )
    
    @staticmethod
    def _build_regenerate_prompt(content: str, detection_result: HallucinationResult,
                                 context: Optional[str], regenerate_count: int = 0) -> str:
        """构建重新生成提示"""
        # 根据重试次数调整提示强度
        urgency_level = "轻微" if regenerate_count == 0 else "严重"
        attempt_info = f"（第{regenerate_count + 1}次尝试）" if regenerate_count > 0 else ""
        
        prompt = f"""
请重新生成以下内容，避免幻觉问题{attempt_info}：

原始内容：
{content}

检测到的问题（{urgency_level}）：
{chr(10).join(detection_result.issues)}

改进建议：
{chr(10).join(detection_result.suggestions)}
"""
        
        if context:
            prompt += f"\n上下文信息：\n{context}"
        
        # 根据重试次数调整提示内容
        if regenerate_count == 0:
            prompt += "\n\n请生成准确、具体、有依据的内容，避免模糊表述和逻辑矛盾。"
        else:
            prompt += f"\n\n⚠️ 这是第{regenerate_count + 1}次重新生成，请务必生成高质量、准确的内容。避免使用模糊表述、逻辑矛盾或缺乏依据的声明。"
        
        return prompt
    
    @staticmethod
    def _remove_hallucination_patterns(content: str) -> str:
        """移除幻觉模式"""
        import re
        
        # 移除常见的幻觉模式
        patterns = [
            r'根据.*?研究表明',
            r'专家.*?认为',
            r'众所周知',
            r'一般来说',
            r'通常情况下',
            r'大多数.*?都',
            r'经过.*?验证'
        ]
        
        for pattern in patterns:
            content = re.sub(pattern, '', content)
        
        return content.strip()
    
    @staticmethod
    def _fix_logic_contradictions(content: str) -> str:
        """修正逻辑矛盾"""
        # 简单的逻辑矛盾修正
        contradictions = [
            ('必须', '不能'),
            ('总是', '从不'),
            ('所有', '没有'),
            ('完全', '部分'),
            ('绝对', '可能')
        ]
        
        for positive, negative in contradictions:
            if positive in content and negative in content:
                # 保留更具体的表述，移除模糊的
                if len(positive) > len(negative):
                    content = content.replace(negative, '')
                else:
                    content = content.replace(positive, '')
        
        return content.strip()
    
    @staticmethod
    def _calculate_content_similarity(content1: str, content2: str) -> float:
        """计算两个内容的相似度"""
        try:
            from difflib import SequenceMatcher
            return SequenceMatcher(None, content1, content2).ratio()
        except Exception as erc:
            logger.error(f"计算内容相似度时出错：{erc}")
            # 如果计算失败，返回0（认为不相似）
            return 0.0
    
    def batch_handle(self, contents: List[str], detection_results: List[HallucinationResult],
                    context: Optional[str] = None, llm=None) -> List[HallucinationHandlingResult]:
        """批量处理幻觉"""
        results = []
        
        for content, detection_result in zip(contents, detection_results):
            result = self.handle_hallucination(content, detection_result, context, llm)
            results.append(result)
        
        return results


def create_hallucination_handler(warn_threshold: float = 0.3,
                                auto_correct_threshold: float = 0.5,
                                regenerate_threshold: float = 0.7,
                                filter_threshold: float = 0.9,
                                max_regenerate_attempts: int = 2) -> HallucinationHandler:
    """创建幻觉处理器实例"""
    return HallucinationHandler(warn_threshold, auto_correct_threshold, regenerate_threshold, filter_threshold, max_regenerate_attempts)
