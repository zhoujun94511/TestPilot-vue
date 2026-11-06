#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import json
import re
import time
import pandas as pd
from typing import List, Dict, Any, Union
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.case_count import clamp_cases_per_requirement
from utils.utils_core.common_utils import generate_id
from utils.utils_performance_monitoring.performance_monitor import get_performance_monitor
from utils.utils_core.logger import get_logger
from utils.utils_ai_quality.hallucination_detector import create_hallucination_detector
from utils.utils_ai_quality.hallucination_handler import create_hallucination_handler
from utils.utils_ai_quality.faithfulness_checker import (
    assess_quantified_claims,
    case_allows_unmentioned,
    contradiction_issue,
    expected_sentences,
    join_source_text,
    judge_sentences,
)
from utils.utils_core.api_error_handler import build_model_error_result, normalize_provider_error
from utils.utils_core import error_codes as ec
from utils.utils_business_logic.case_id_generator import safe_case_id_segment
from utils.utils_performance_monitoring.token_monitor import (
    ensure_session_budget,
    record_message_usage,
    track_session_usage,
)
from utils.utils_performance_monitoring.token_session import TokenSessionLimitExceeded
from config.settings import settings

logger = get_logger(__name__)

_NON_RETRYABLE_STATUS = {400, 401, 402, 403, 404, 422}


def is_retryable_model_error(error: Exception) -> bool:
    """鉴权、余额、参数类错误重试也不会成功，只会多花钱。"""
    if isinstance(error, TokenSessionLimitExceeded):
        return False
    normalized = normalize_provider_error(getattr(settings, 'DEFAULT_COMPANY', 'OPENAI'), error)
    return int(normalized.get('status_code') or 500) not in _NON_RETRYABLE_STATUS


class CaseService:
    """测试用例生成服务"""

    def __init__(self):
        self.performance_monitor = get_performance_monitor()
        # 初始化智能检索策略（统一检索架构）
        # 提前导入 settings，避免在 try 块外引用
        from config.settings import settings
        try:
            from utils.utils_intelligent_retrieval.smart_retrieval_strategy import get_smart_retrieval_strategy
            from utils.utils_intelligent_retrieval.smart_retrieval_strategy import RetrievalConfig
            
            # 使用 settings 中的配置创建检索配置
            retrieval_config = RetrievalConfig(
                top_k=settings.RAG_TOP_K * 2,  # 检索更多结果，后续过滤
                score_threshold=settings.RAG_SCORE_THRESHOLD,
                enable_reranking=settings.RAG_ENABLE_RERANKING,
                enable_query_expansion=settings.RAG_ENABLE_QUERY_EXPANSION,
                enable_context_awareness=settings.RAG_ENABLE_CONTEXT_AWARENESS,
                max_context_length=settings.RAG_MAX_CONTEXT_LENGTH,
                similarity_threshold=settings.RAG_SIMILARITY_THRESHOLD
            )
            self.smart_retrieval = get_smart_retrieval_strategy(retrieval_config)
            self._use_smart_retrieval = True
        except Exception as e:
            logger.warning(f"初始化智能检索策略失败，将使用传统检索方式: {e}")
            self.smart_retrieval = None
            self._use_smart_retrieval = False
        
        self.hallucination_detector = create_hallucination_detector()
        self.hallucination_handler = create_hallucination_handler(
            warn_threshold=getattr(settings, 'HALLUCINATION_WARN_THRESHOLD', 0.3),
            auto_correct_threshold=getattr(settings, 'HALLUCINATION_AUTO_CORRECT_THRESHOLD', 0.5),
            regenerate_threshold=getattr(settings, 'HALLUCINATION_REGENERATE_THRESHOLD', 0.7),
            filter_threshold=getattr(settings, 'HALLUCINATION_FILTER_THRESHOLD', 0.9),
            max_regenerate_attempts=getattr(settings, 'HALLUCINATION_MAX_REGENERATE_ATTEMPTS', 2)
        )

    @staticmethod
    def _localize_recommendation_values(values: List[str], output_language: str | None, value_kind: str) -> List[str]:
        """根据目标语言归一推荐项，避免英文场景继续注入中文提示词。"""
        if output_language != 'en':
            return values

        test_type_map = {
            '功能测试': 'Functional Testing',
            '性能测试': 'Performance Testing',
            '安全测试': 'Security Testing',
            '兼容性测试': 'Compatibility Testing',
            '可用性测试': 'Usability Testing',
            '可访问性测试': 'Accessibility Testing',
            '易用性测试': 'Usability Testing',
            '集成测试': 'Integration Testing',
            '回归测试': 'Regression Testing',
            '接口测试': 'API Testing',
            '自动化测试': 'Automation Testing'
        }
        method_map = {
            '等价类划分法': 'Equivalence Partitioning',
            '边界值分析法': 'Boundary Value Analysis',
            '因果图法': 'Cause-Effect Graphing',
            '判定表法': 'Decision Table Testing',
            '正交试验法': 'Orthogonal Array Testing',
            '状态迁移测试': 'State Transition Testing',
            '探索性测试': 'Exploratory Testing',
            '基于风险的测试': 'Risk-based Testing'
        }

        mapper = test_type_map if value_kind == 'test_type' else method_map
        return [mapper.get(str(item), str(item)) for item in values]


    def generate_cases(
            self,
            requirement_text: str,
            use_rag: bool = False,
            case_count: int = 5,
            category: str = 'functional',
            output_language: str = None,
            llm=None,
            vector_db=None,
            start_monitoring: bool = True
    ) -> Dict[str, Any]:
        """
        生成测试用例

        Args:
            requirement_text: 需求文本
            use_rag: 是否使用RAG增强
            case_count: 生成用例数量
            category: 用例分类
            output_language: 输出语言（zh/en），为空时自动推断
            llm: 语言模型实例
            vector_db: 向量数据库实例
            start_monitoring: 是否启动性能监控

        Returns:
            生成结果字典
        """
        try:
            case_count = clamp_cases_per_requirement(case_count, 5)
            if not llm:
                return {
                    'success': False,
                    'message': 'LLM实例未初始化',
                    'error': ec.MODEL_NOT_INITIALIZED,
                    'error_code': ec.MODEL_NOT_INITIALIZED,
                    'status_code': 503,
                    'retryable': False
                }

            # 开始性能监控（仅在需要时）
            if start_monitoring:
                self.performance_monitor.start_monitoring()

            # RAG增强（如果启用）
            enhanced_context = ""
            if use_rag and vector_db:
                try:
                    # 搜索相关历史用例（使用SmartRetrievalStrategy统一检索架构）
                    start_time = time.time()
                    
                    # 初始化 search_results（确保在所有分支中都有定义）
                    search_results = []

                    from services.knowledge_vector_scope import merged_vector_search_kwargs

                    scope_kwargs = merged_vector_search_kwargs()

                    # 使用智能检索策略（如果可用）
                    if self._use_smart_retrieval and self.smart_retrieval:
                        try:
                            # 使用SmartRetrievalStrategy进行检索（内置查询扩展、多策略检索、重排序）
                            smart_results = self.smart_retrieval.retrieve(
                                query=requirement_text,
                                vector_db=vector_db,
                                context=None,
                                vector_search_kwargs=scope_kwargs,
                            )
                            
                            # 转换为文档格式（兼容现有代码）
                            for result in smart_results:
                                # 创建文档对象
                                class DocWrapper:
                                    def __init__(self, content, metadata, score_value):
                                        self.page_content = content
                                        self.metadata = metadata or {}
                                        self.metadata['similarity_score'] = float(score_value)
                                
                                search_results.append(DocWrapper(
                                    result.content,
                                    result.metadata,
                                    result.score
                                ))
                            
                        except Exception as e:
                            logger.warning(f"智能检索失败，降级到传统检索: {e}")
                            # 降级到传统检索方式
                            self._use_smart_retrieval = False
                    
                    # 传统检索方式（降级或未启用智能检索时使用）
                    if not self._use_smart_retrieval or not self.smart_retrieval:
                        # 如果智能检索未返回结果，使用传统检索方式
                        if not search_results:
                            # 优化：使用查询扩展提升检索效果
                            enhanced_query = self._enhance_search_query(requirement_text)
                            
                            # 性能优化：直接使用 similarity_search_with_score 一次获取结果和得分
                            try:
                                search_with_scores = vector_db.similarity_search_with_score(
                                    enhanced_query,
                                    k=settings.RAG_TOP_K * 2,  # 检索更多结果，后续过滤
                                    **scope_kwargs,
                                )
                                # 转换为文档列表并添加相似度得分
                                search_results = []
                                for doc, similarity_score_val in search_with_scores:
                                    if not hasattr(doc, 'metadata'):
                                        doc.metadata = {}
                                    doc.metadata['similarity_score'] = float(similarity_score_val)
                                    search_results.append(doc)
                            except Exception as e:
                                logger.warning(f"相似度搜索失败，尝试使用不带得分的搜索: {e}")
                                # 降级：如果带得分的搜索失败，使用不带得分的搜索
                                search_results = vector_db.similarity_search(
                                    enhanced_query,
                                    k=settings.RAG_TOP_K * 2,
                                    **scope_kwargs,
                                )

                    from services.data_scope import filter_scoped_retrieval_items

                    search_results = filter_scoped_retrieval_items(search_results)

                    search_duration = time.time() - start_time
                    
                    # 记录embedding性能指标
                    try:
                        from utils.utils_ai_models.embedding_monitor import get_embedding_monitor
                        embedding_monitor = get_embedding_monitor()
                        embedding_monitor.record_call(
                            tokens=len(requirement_text.split()),
                            duration=search_duration,
                            success=True,
                            cache_hit=False,
                            model_name="sentence-transformers",
                            device="auto"
                        )
                    except Exception as monitor_error:
                        logger.debug(f"记录embedding性能指标失败: {monitor_error}")
                    
                    # 相关性判断：过滤低相关度的内容
                    if search_results:
                        # 从配置中心获取RAG阈值（统一配置优先级：配置中心 > settings.py > 默认值）
                        from services.config_center_service import config_center_service
                        try:
                            # 配置优先级：配置中心 > settings.py > 默认值 0.7
                            rag_threshold = config_center_service.get_config_value(
                                'RAG_SCORE_THRESHOLD', 
                                settings.RAG_SCORE_THRESHOLD  # 统一使用settings中的默认值
                            )
                            min_relevance_score = float(rag_threshold)
                        except Exception as e:
                            logger.warning(f"获取配置中心RAG阈值失败，使用settings默认值: {e}")
                            min_relevance_score = settings.RAG_SCORE_THRESHOLD  # 统一使用settings中的默认值
                        
                        filtered_results = self._filter_relevant_content(
                            search_results, 
                            requirement_text,
                            min_relevance_score=min_relevance_score
                        )
                        
                        if filtered_results:
                            enhanced_context = "\n".join([doc.page_content for doc in filtered_results])
                            logger.info(f"RAG增强：找到{len(filtered_results)}个相关文档，总长度{len(enhanced_context)}字符")
                        else:
                            logger.info("RAG增强：未找到相关度足够高的文档，跳过知识库增强")
                            enhanced_context = ""
                except Exception as e:
                    # RAG失败不影响主流程
                    logger.warning(f"RAG搜索失败: {e}")

            # 生成测试用例
            generation_result = self._generate_function_cases(
                llm=llm,
                requirement_text=requirement_text,
                enhanced_context=enhanced_context,
                case_count=case_count,
                output_language=output_language
            )

            if not isinstance(generation_result, list):
                return {
                    'success': False,
                    'message': '用例生成失败，返回结果格式错误',
                    'error': ec.MODEL_UNKNOWN_ERROR,
                    'error_code': ec.MODEL_UNKNOWN_ERROR,
                    'status_code': 502,
                    'retryable': False
                }

            # 处理生成的用例
            processed_cases = []
            for i, case_data in enumerate(generation_result):
                try:
                    # 确保必要字段存在
                    if not isinstance(case_data, dict):
                        case_data = {'title': str(case_data), 'steps': []}

                    # 生成唯一用例ID（双重ID系统：内部ID + 显示ID）
                    base_timestamp = int(time.time() * 1000)  # 基础时间戳
                    
                    # 生成显示ID（简洁格式）
                    if case_data.get('display_id') or case_data.get('case_id'):
                        display_id = str(case_data.get('display_id') or case_data.get('case_id'))
                    else:
                        # 生成新的显示ID
                        display_id = f"TC-{generate_id(case_data.get('title', f'测试用例_{i + 1}'))}-{i + 1:02d}"
                    display_id = safe_case_id_segment(display_id)
                    
                    # 生成内部ID（带时间戳，确保数据库唯一性）
                    internal_id = f"{display_id}-{base_timestamp + i}"

                    # 标准化用例数据
                    processed_case = {
                        'case_id': internal_id,  # 数据库存储使用内部ID
                        'display_id': display_id,  # 界面显示使用显示ID
                        'title': case_data.get('title', f'测试用例_{i + 1}'),
                        'precondition': case_data.get('precondition', ''),
                        'steps': case_data.get('steps', []),
                        'expected_result': case_data.get('expected_result', ''),
                        'priority': self._normalize_priority(case_data.get('priority', 'P2')),  # 使用AI返回的优先级，默认为P2
                        'category': case_data.get('category', category),
                        'test_method': case_data.get('test_method', ''),
                        'module': case_data.get('module', ''),
                        'tags': case_data.get('tags', [])
                    }

                    processed_cases.append(processed_case)

                except Exception as e:
                    logger.error(f"处理用例数据失败: {e}")
                    continue

            # 更新处理计数
            self.performance_monitor.update_processed_count(len(processed_cases))

            processed_cases_final, hallucination_results = self._apply_hallucination_guard(
                processed_cases,
                requirement_text,
                enhanced_context,
                llm
            )

            # 停止性能监控并获取统计信息
            self.performance_monitor.stop_monitoring()
            performance_stats = self.performance_monitor.get_performance_stats()

            if not processed_cases_final:
                return {
                    'success': False,
                    'message': '没有生成可用的测试用例，请补充需求描述后重试',
                    'error': ec.EMPTY_CONTENT,
                    'error_code': ec.EMPTY_CONTENT,
                    'status_code': 422,
                    'retryable': True,
                }

            result = {
                'success': True,
                'message': f'成功生成{len(processed_cases_final)}个测试用例',
                'cases': processed_cases_final,
                'total': len(processed_cases_final),
                'generation_time': performance_stats['elapsed_time'],
                'processing_rate': performance_stats['processing_rate'],
                'use_rag': use_rag,
                'enhanced_context_length': len(enhanced_context) if enhanced_context else 0,
                'performance_stats': performance_stats
            }
            
            # 添加幻觉检测结果
            if hallucination_results:
                result['hallucination_detection'] = hallucination_results

            return result

        except Exception as e:
            # 确保停止监控
            self.performance_monitor.stop_monitoring()
            return build_model_error_result(
                getattr(settings, 'DEFAULT_COMPANY', 'OPENAI'),
                e,
                fallback_message='测试用例生成失败'
            )

    def _detect_hallucination_in_cases(self, cases: List[Dict[str, Any]], 
                                     requirement_text: str, 
                                     enhanced_context: str = None,
                                     llm=None) -> Dict[str, Any]:
        """
        检测测试用例中的幻觉
        
        Args:
            cases: 测试用例列表
            requirement_text: 原始需求文本
            enhanced_context: 增强的上下文
            
        Returns:
            幻觉检测结果
        """
        try:
            # 准备源文档
            source_documents = []
            if enhanced_context:
                source_documents.append({
                    'content': enhanced_context,
                    'source': 'rag_enhanced',
                    'quality_score': 0.8
                })
            
            # 将需求文本作为源文档
            source_documents.append({
                'content': requirement_text,
                'source': 'requirement',
                'quality_score': 1.0
            })
            
            # 提取用例内容进行检测
            case_contents = []
            for case in cases:
                # 组合用例的关键信息
                case_content = f"标题: {case.get('title', '')}\n"
                case_content += f"步骤: {'; '.join(case.get('steps', []))}\n"
                case_content += f"预期结果: {case.get('expected_result', '')}\n"
                case_content += f"前置条件: {case.get('precondition', '')}"
                case_contents.append(case_content)
            
            detection_results = []
            for case, case_content in zip(cases, case_contents):
                allow_unmentioned = case_allows_unmentioned(case)
                result = self.hallucination_detector.detect_hallucination(
                    case_content,
                    source_documents,
                    context=requirement_text,
                    allow_unmentioned=allow_unmentioned,
                )
                if llm is not None and not allow_unmentioned:
                    source_text = join_source_text(source_documents, requirement_text)
                    judged = judge_sentences(llm, source_text, expected_sentences(case.get('expected_result')))
                    for item in judged:
                        result.source_verification.setdefault('claims', []).append(item)
                        if item.get('verdict') == 'contradicted':
                            result.issues.append(f"互相矛盾: 「{item.get('text', '')}」与原文相反")
                            result.is_hallucination = True
                            result.confidence = 0.6
                            if "只改写互相矛盾的句子，保留其余步骤和预期结果" not in result.suggestions:
                                result.suggestions.append("只改写互相矛盾的句子，保留其余步骤和预期结果")
                detection_results.append(result)
            
            # 生成检测报告
            report = self.hallucination_detector.generate_detection_report(detection_results)
            
            # 为每个用例添加检测结果
            enhanced_cases = []
            for i, case in enumerate(cases):
                if i < len(detection_results):
                    result = detection_results[i]
                    case['hallucination_detection'] = {
                        'is_hallucination': result.is_hallucination,
                        'confidence': result.confidence,
                        'issues': result.issues,
                        'suggestions': result.suggestions,
                        'hints': result.source_verification.get('hints', []),
                        'claims': result.source_verification.get('claims', []),
                    }
                enhanced_cases.append(case)
            
            return {
                'hallucination_count': report['hallucination_count'],
                'hallucination_rate': report['hallucination_rate'],
                'avg_confidence': report['avg_confidence'],
                'issue_types': report['issue_types'],
                'cases_with_detection': enhanced_cases,
                'detection_summary': {
                    'total_cases': len(cases),
                    'problematic_cases': report['hallucination_count'],
                    'quality_score': 1.0 - report['hallucination_rate']
                }
            }
            
        except Exception as e:
            logger.error(f"幻觉检测失败: {e}")
            return {
                'hallucination_count': 0,
                'hallucination_rate': 0.0,
                'avg_confidence': 0.0,
                'issue_types': {},
                'cases_with_detection': cases,
                'detection_summary': {
                    'total_cases': len(cases),
                    'problematic_cases': 0,
                    'quality_score': 1.0,
                    'error': 'internal_error'
                }
            }

    def _generate_function_cases(self, llm, requirement_text: str, enhanced_context: str, case_count: int, output_language: str = None):
        """生成功能测试用例 - 基于现有代码结构优化"""
        try:
            def infer_language_instruction(text: str, forced_language: str = None) -> str:
                if forced_language == 'zh':
                    return "测试用例内容必须使用简体中文（字段名保持英文）。"
                if forced_language == 'en':
                    return "Test case content must be in English (field names remain in English)."
                zh_count = len(re.findall(r'[\u4e00-\u9fff]', text or ''))
                en_count = len(re.findall(r'[A-Za-z]', text or ''))
                if zh_count > en_count:
                    return "测试用例内容必须使用简体中文（字段名保持英文）。"
                if en_count > zh_count:
                    return "Test case content must be in English (field names remain in English)."
                return "请跟随用户输入主体语言输出测试用例内容（字段名保持英文）。"

            # 1. 从 utils/complexity_scorer.py 获取复杂度分析
            from utils.utils_business_logic.complexity_scorer import ComplexityScorer
            complexity_scorer = ComplexityScorer.from_knowledge_base()

            # 分析需求复杂度 - 添加重试机制
            modules = [{"name": "需求分析", "description": requirement_text}]
            _complexity_analysis = "复杂度等级: medium, 得分: 0"  # 默认值

            try:
                complexity_result = complexity_scorer.assess(modules, case_count, requirement_text, return_details=True)

                # 正确处理ComplexityResult对象
                if hasattr(complexity_result, 'label') and hasattr(complexity_result, 'score'):
                    complexity_analysis = f"复杂度等级: {complexity_result.label}, 得分: {complexity_result.score}"
                elif isinstance(complexity_result, dict):
                    complexity_analysis = f"复杂度等级: {complexity_result.get('label', 'medium')}, 得分: {complexity_result.get('score', 0)}"
                else:
                    complexity_analysis = f"复杂度等级: medium, 得分: 0"
            except Exception as e:
                logger.warning(f"复杂度分析失败，使用默认值: {e}")
                complexity_analysis = "复杂度等级: medium, 得分: 0"

            # 2. 从 config/knowledge_base.json 获取测试类型和方法
            try:
                from utils.utils_business_logic.complexity_scorer import ComplexityScorer
                complexity_scorer = ComplexityScorer.from_knowledge_base()
                
                # 进行风险分析
                risk_analysis = complexity_scorer.analyze_requirement_risks(requirement_text)
                overall_risk = risk_analysis.get("overall_risk", "medium")
                
                # 根据风险等级获取推荐的测试类型和方法
                suggested_test_types = ComplexityScorer.get_risk_based_test_types(overall_risk)
                suggested_methods = ComplexityScorer.get_risk_based_test_methods(overall_risk)
                
                # 如果获取不到，使用fallback
                if not suggested_test_types:
                    suggested_test_types = ["功能测试", "性能测试", "安全测试", "兼容性测试", "可用性测试"]
                if not suggested_methods:
                    suggested_methods = ["等价类划分法", "边界值分析法", "因果图法", "判定表法", "正交试验法"]
                    
            except Exception as e:
                logger.warning(f"获取测试类型和方法失败: {e}")
                suggested_test_types = ["功能测试", "性能测试", "安全测试", "兼容性测试", "可用性测试"]
                suggested_methods = ["等价类划分法", "边界值分析法", "因果图法", "判定表法", "正交试验法"]

            suggested_test_types = self._localize_recommendation_values(suggested_test_types, output_language, 'test_type')
            suggested_methods = self._localize_recommendation_values(suggested_methods, output_language, 'test_method')

            # 3. 从 pilotAgent.py 获取 format_instructions
            language_instruction = infer_language_instruction(requirement_text, output_language)
            format_instructions = (
                "请严格返回 JSON 格式，字段名必须是英文(case_id, module, title, preconditions, steps, expected, priority)。"
                f"{language_instruction}"
            )

            # 4. 使用settings中定义的FUNCTION_PROMPT
            if enhanced_context:
                # 使用RAG版本
                prompt_template = settings.FUNCTION_PROMPT_RAG
                prompt = prompt_template.format(
                    max_case_nums=case_count,
                    context=enhanced_context,
                    requirement=requirement_text,
                    complexity_analysis=complexity_analysis,
                    suggested_test_types=', '.join(suggested_test_types),
                    suggested_methods=', '.join(suggested_methods),
                    format_instructions=format_instructions
                )
            else:
                # 使用普通版本
                prompt_template = settings.FUNCTION_PROMPT
                prompt = prompt_template.format(
                    max_case_nums=case_count,
                    requirement=requirement_text,
                    complexity_analysis=complexity_analysis,
                    suggested_test_types=', '.join(suggested_test_types),
                    suggested_methods=', '.join(suggested_methods),
                    format_instructions=format_instructions
                )

            # 调用LLM生成用例 - 添加重试机制
            max_retries = 3
            response = None
            for attempt in range(max_retries):
                ensure_session_budget()
                try:
                    response = llm.invoke(prompt)
                    break
                except Exception as e:
                    track_session_usage()
                    if attempt == max_retries - 1 or not is_retryable_model_error(e):
                        logger.error(f"LLM调用失败: {e}")
                        raise
                    logger.warning(f"LLM调用失败，重试 {attempt + 1}/{max_retries}: {e}")
                    time.sleep(2 ** attempt)  # 指数退避
            record_message_usage(response, source='case_generation')

            # 解析LLM响应
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)

            target_language = output_language or CaseService._infer_target_language(requirement_text)
            content = CaseService._rewrite_json_to_target_language_if_needed(llm, content, target_language, "cases")

            # 尝试解析JSON响应
            try:
                json_match = re.search(r'\{.*"cases".*}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    result = json.loads(json_str)
                    cases = result.get('cases', [])
                else:
                    # 如果没有找到标准格式，尝试解析简单数组格式
                    json_match = re.search(r'\[.*]', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        cases = json.loads(json_str)
                    else:
                        cases = self._parse_text_cases(content, case_count)
            except (json.JSONDecodeError, AttributeError):
                # JSON解析失败，使用文本解析
                cases = self._parse_text_cases(content, case_count)
            if not isinstance(cases, list):
                cases = []
            cases = [item for item in cases if isinstance(item, dict)][:case_count]

            # 标准化用例数据 - 完全按照prompt格式处理
            base_timestamp = int(time.time() * 1000)  # 基础时间戳
            processed_cases = []
            for i, case_data in enumerate(cases):
                try:
                    # 生成唯一用例ID（双重ID系统：内部ID + 显示ID）
                    module = str(case_data.get('module') or 'DEFAULT')
                    
                    # 生成显示ID（简洁格式）
                    if case_data.get('case_id'):
                        display_id = str(case_data.get('case_id'))  # 使用AI提供的ID
                    else:
                        # 生成新的显示ID
                        display_id = f"TC-{module}-{i + 1:02d}"
                    display_id = safe_case_id_segment(display_id)
                    
                    # 生成内部ID（带时间戳，确保数据库唯一性）
                    internal_id = f"{display_id}-{base_timestamp + i}"

                    # 标准化用例数据，完全按照prompt格式
                    processed_case = {
                        'case_id': internal_id,  # 数据库存储使用内部ID
                        'display_id': display_id,  # 界面显示使用显示ID
                        'title': case_data.get('title', f'{"Test Case" if output_language == "en" else "测试用例"}_{i + 1}'),
                        'precondition': case_data.get('preconditions', case_data.get('precondition', '')),
                        'steps': case_data.get('steps', []),
                        'expected_result': CaseService._process_expected_result(case_data.get('expected', case_data.get('expected_result', []))),
                        'priority': self._normalize_priority(case_data.get('priority', 'P1')),
                        'category': case_data.get('category', case_data.get('test_type', 'functional')),
                        'test_method': case_data.get('test_method', ''),
                        'module': case_data.get('module', ''),
                        'tags': case_data.get('tags', [])
                    }

                    processed_cases.append(processed_case)

                except Exception as e:
                    logger.error(f"处理用例数据失败: {e}")
                    continue

            if not processed_cases:
                raise ValueError('模型返回的内容里没有可用的测试用例')
            return processed_cases

        except Exception as e:
            logger.error(f"生成用例失败: {e}")
            raise

    @staticmethod
    def _infer_target_language(text: str) -> str:
        zh_count = len(re.findall(r'[\u4e00-\u9fff]', text or ''))
        en_count = len(re.findall(r'[A-Za-z]', text or ''))
        if zh_count > en_count:
            return 'zh'
        if en_count > zh_count:
            return 'en'
        return 'auto'

    @staticmethod
    def _needs_language_rewrite(text: str, target_language: str) -> bool:
        if not text or target_language == 'auto':
            return False
        zh_count = len(re.findall(r'[\u4e00-\u9fff]', text))
        en_count = len(re.findall(r'[A-Za-z]', text))
        if target_language == 'zh':
            return en_count > max(zh_count * 2, 30)
        return zh_count > max(en_count * 2, 15)

    @staticmethod
    def _rewrite_json_to_target_language_if_needed(llm, raw_content: str, target_language: str, root_key: str) -> str:
        if not CaseService._needs_language_rewrite(raw_content, target_language):
            return raw_content

        if target_language == 'zh':
            language_rule = "请将 JSON 中所有可读文本字段改写为简体中文。"
        else:
            language_rule = "Please rewrite all human-readable text fields in the JSON into English."

        rewrite_prompt = f"""
你将收到一段 JSON 文本，请在不改变 JSON 结构、字段名、层级和数量的前提下，仅改写字段值语言。
{language_rule}
保留编号、标识符、字段名、数组结构与顺序，不要新增解释。
返回必须是完整 JSON，且根键仍为 "{root_key}"。

JSON:
{raw_content}
"""
        try:
            ensure_session_budget()
            rewritten = llm.invoke(rewrite_prompt)
            record_message_usage(rewritten, source='case_generation')
            rewritten_text = rewritten.content if hasattr(rewritten, 'content') else str(rewritten)

            # 兼容模型返回 markdown code block 或包裹文本
            fence_match = re.search(r'```(?:json)?\s*(\{.*})\s*```', rewritten_text, re.DOTALL | re.IGNORECASE)
            candidate = fence_match.group(1) if fence_match else rewritten_text

            # 优先提取包含 root_key 的 JSON 对象
            json_match = re.search(r'\{.*}', candidate, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict) and root_key in parsed:
                        return json_str
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

            if f'"{root_key}"' in candidate:
                return candidate
            return raw_content
        except Exception as rewrite_error:
            logger.warning(f"语言兜底改写失败，使用原始输出: {rewrite_error}")
            return raw_content

    @staticmethod
    def _process_expected_result(expected_data):
        """处理expected_result字段，支持字符串和数组格式"""
        if isinstance(expected_data, str):
            try:
                # 如果是字符串，尝试解析为JSON
                return json.loads(expected_data)
            except (json.JSONDecodeError, TypeError):
                # 解析失败，返回空数组
                return []
        elif isinstance(expected_data, list):
            # 如果已经是数组，直接返回
            return expected_data
        else:
            # 其他情况返回空数组
            return []

    @staticmethod
    def _normalize_priority(priority):
        """标准化优先级格式 - 使用P0-P4格式"""
        from services.case_field_filters import normalize_priority

        return normalize_priority(priority)
    
    @staticmethod
    def _generate_unique_case_id(display_id: str, index: int, base_timestamp: int) -> str:
        """生成唯一用例ID（用于测试）"""
        return f"{display_id}-{base_timestamp + index}"

    @staticmethod
    def _parse_text_cases(content: str, case_count: int) -> List[Dict[str, Any]]:
        """解析文本格式的用例"""
        cases = []
        lines = content.split('\n')
        current_case = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 识别用例标题
            if line.startswith('用例') or line.startswith('测试用例') or line.startswith('Case'):
                if current_case:
                    cases.append(current_case)
                current_case = {
                    'title': line,
                    'precondition': '',
                    'steps': [],
                    'expected_result': [],
                    'priority': 'P1',
                    'category': 'functional',
                    'test_method': '',
                    'module': '',
                    'tags': []
                }
            # 识别步骤
            elif line.startswith('步骤') or line.startswith('Step'):
                if current_case:
                    current_case['steps'].append(line)
            # 识别预期结果
            elif line.startswith('预期') or line.startswith('Expected'):
                if current_case:
                    current_case['expected_result'].append(line)
            # 识别前置条件
            elif line.startswith('前置') or line.startswith('Precondition'):
                if current_case:
                    current_case['precondition'] = line

        # 添加最后一个用例
        if current_case:
            cases.append(current_case)

        # 限制返回的用例数量
        if len(cases) > case_count:
            cases = cases[:case_count]

        return cases

    def _filter_relevant_content(self, search_results, requirement_text: str, min_relevance_score: float = 0.7):
        """
        过滤相关度低的内容，避免不相关的知识库内容影响生成
        
        Args:
            search_results: 搜索结果列表
            requirement_text: 用户需求文本
            min_relevance_score: 最低相关性阈值
            
        Returns:
            过滤后的相关文档列表
        """
        try:
            if not search_results:
                return []
            
            # 使用配置化的RAG关键词管理器
            from utils.utils_intelligent_retrieval.rag_keyword_config import get_rag_keyword_config
            keyword_config = get_rag_keyword_config()
            
            # 提取需求关键词（优化版：结合配置和直接提取）
            requirement_keywords = set()
            requirement_lower = requirement_text.lower()
            
            # 方法1：从配置文件获取所有关键词（保留原有逻辑）
            all_keywords = []
            
            # 从平台关键词中提取
            platform_keywords = keyword_config.config.get("platform_keywords", {})
            if "items" in platform_keywords:
                for item in platform_keywords["items"]:
                    if "keywords" in item:
                        all_keywords.extend(item["keywords"])
            
            # 从应用关键词中提取
            application_keywords = keyword_config.config.get("application_keywords", {})
            if "items" in application_keywords:
                for app_type, app_config in application_keywords["items"].items():
                    if "keywords" in app_config:
                        all_keywords.extend(app_config["keywords"])
            
            # 从功能关键词中提取
            functional_keywords = keyword_config.config.get("functional_keywords", {})
            if "items" in functional_keywords:
                for item in functional_keywords["items"]:
                    if "keywords" in item:
                        all_keywords.extend(item["keywords"])
            
            # 从技术关键词中提取
            technical_keywords = keyword_config.config.get("technical_keywords", {})
            if "items" in technical_keywords:
                for item in technical_keywords["items"]:
                    if "keywords" in item:
                        all_keywords.extend(item["keywords"])
            
            # 从领域特征中提取
            domain_features = keyword_config.config.get("domain_features", {})
            if "features" in domain_features:
                for feature_name, feature_config in domain_features["features"].items():
                    if "keywords" in feature_config:
                        all_keywords.extend(feature_config["keywords"])
            
            # 根据需求文本提取关键词（配置匹配）
            for keyword in all_keywords:
                if keyword.lower() in requirement_lower:
                    requirement_keywords.add(keyword.lower())
            
            # 方法2：直接从需求文本中提取核心概念（与 rag_keyword_config 配合使用）
            try:
                from utils.utils_intelligent_retrieval.requirement_keyword_extractor import get_requirement_keyword_extractor
                # 传入 keyword_config 实例，实现整合
                keyword_extractor = get_requirement_keyword_extractor(keyword_config)
                
                # 提取核心概念（结合配置和直接提取）
                core_concepts = keyword_extractor.extract_core_concepts(requirement_text)
                
                # 合并关键词（配置关键词已在方法1中提取，这里补充直接提取的）
                requirement_keywords.update(core_concepts['keywords'])
                requirement_keywords.update(core_concepts['entities'])
                requirement_keywords.update(core_concepts['tech_terms'])
                
                # 短语作为补充（如果长度合适）
                for phrase in core_concepts['phrases']:
                    if 2 <= len(phrase) <= 8:  # 限制短语长度
                        requirement_keywords.add(phrase)
                
            except Exception as e:
                logger.warning(f"智能关键词提取失败，使用传统方法: {e}")
                # 如果智能提取失败，继续使用原有逻辑
            
            filtered_results = []
            
            for doc in search_results:
                try:
                    # 获取文档内容
                    content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
                    content_lower = content.lower()
                    
                    # 计算相关性得分
                    relevance_score = 0.0
                    
                    # 获取评分权重配置
                    weights = keyword_config.get_scoring_weights()
                    thresholds = keyword_config.get_thresholds()
                    
                    # 从配置中心获取RAG阈值（统一配置优先级：配置中心 > settings.py > 默认值）
                    from services.config_center_service import config_center_service
                    from config.settings import settings
                    try:
                        # 配置优先级：配置中心 > settings.py > 默认值 0.7
                        rag_threshold = config_center_service.get_config_value(
                            'RAG_SCORE_THRESHOLD', 
                            settings.RAG_SCORE_THRESHOLD  # 统一使用settings中的默认值
                        )
                        thresholds['min_relevance_score'] = float(rag_threshold)
                    except Exception as e:
                        logger.warning(f"获取配置中心RAG阈值失败，使用settings默认值: {e}")
                        # 使用配置文件中的默认值
                        thresholds['min_relevance_score'] = settings.RAG_SCORE_THRESHOLD
                    
                    # 1. 关键词匹配得分（优化版：加权匹配）- 提高核心概念权重
                    keyword_matches = 0
                    matched_keywords = []
                    keyword_weights = {}  # 关键词权重
                    
                    # 为不同类型的关键词设置权重
                    for keyword in requirement_keywords:
                        # 核心概念（长短语、技术术语）权重更高
                        if len(keyword) >= 6:  # 长关键词（如"植物识别"、"数据清洗"）权重最高
                            keyword_weights[keyword] = 2.5
                        elif len(keyword) >= 4:  # 中等长度关键词权重较高
                            keyword_weights[keyword] = 1.8
                        elif len(keyword) >= 3:  # 短关键词权重正常
                            keyword_weights[keyword] = 1.2
                        else:
                            keyword_weights[keyword] = 0.8  # 超短关键词（如"ai"、"数据"）权重降低
                    
                    # 计算加权匹配得分
                    weighted_matches = 0.0
                    total_weight = sum(keyword_weights.values()) if keyword_weights else 1.0
                    
                    for keyword, weight in keyword_weights.items():
                        if keyword in content_lower:
                            keyword_matches += 1
                            matched_keywords.append(keyword)
                            weighted_matches += weight
                    
                    if requirement_keywords:
                        # 使用加权得分
                        keyword_score = weighted_matches / total_weight if total_weight > 0 else 0
                        keyword_contribution = keyword_score * weights["keyword_match"]
                        relevance_score += keyword_contribution
                    
                    # 1.5. 语义相似度得分（新增：基于embedding的相似度）- 提高权重，确保准确性
                    semantic_score = 0.0
                    try:
                        # 如果文档有相似度得分（从vector_db返回），使用它
                        if hasattr(doc, 'metadata') and doc.metadata and 'similarity_score' in doc.metadata:
                            semantic_score = doc.metadata.get('similarity_score', 0)
                            # 将相似度得分归一化到0-1范围（如果原始得分不在这个范围）
                            if semantic_score > 1.0:
                                semantic_score = min(semantic_score / 2.0, 1.0)  # 假设得分在0-2范围
                    except Exception as e:
                        logger.debug(f"获取语义相似度失败: {e}")
                    
                    # 提高语义相似度权重，确保内容主题匹配
                    semantic_contribution = semantic_score * 0.35  # 提高到35%权重（原15%）
                    relevance_score += semantic_contribution
                    
                    # 核心实体/主题匹配检查（关键改进）
                    core_entities = set()
                    # 提取核心实体（长短语、技术术语，通常是核心概念）
                    for keyword in requirement_keywords:
                        if len(keyword) >= 4:  # 长关键词通常是核心概念（如"植物识别"、"数据清洗"）
                            core_entities.add(keyword.lower())
                    
                    # 检查核心实体是否在文档中出现
                    core_entity_matches = sum(1 for entity in core_entities if entity in content_lower)
                    core_entity_match_ratio = core_entity_matches / len(core_entities) if core_entities else 0.0
                    
                    # 如果核心实体完全不匹配，大幅降分
                    if core_entities and core_entity_match_ratio == 0:
                        # 核心实体完全不匹配，说明主题不一致
                        relevance_score *= 0.3  # 降分70%
                    elif core_entities and core_entity_match_ratio < 0.3:
                        # 核心实体匹配率低，适度降分
                        relevance_score *= 0.6  # 降分40%
                    
                    # 2. 内容长度得分（避免过短内容）- 降低权重，避免长度影响准确性判断
                    content_length_threshold = thresholds.get("content_length_threshold", 100)
                    content_length_score = min(len(content) / content_length_threshold, 1.0)
                    content_length_contribution = content_length_score * (weights["content_length"] * 0.5)  # 降低50%权重
                    relevance_score += content_length_contribution
                    
                    # 3. 领域相关性得分（基于内容特征）
                    domain_score = 0.0
                    
                    # 从配置文件获取领域特征
                    domain_features = keyword_config.config.get("domain_features", {})
                    if "features" in domain_features:
                        for domain_name, feature_config in domain_features["features"].items():
                            if "keywords" in feature_config:
                                features = feature_config["keywords"]
                                matches = sum(1 for feature in features if feature in content_lower)
                                if matches > 0:
                                    domain_score += min(matches / len(features), 1.0) * 0.3
                    
                    domain_contribution = domain_score * weights["domain_relevance"]
                    relevance_score += domain_contribution
                    
                    # 4. 排除明显不相关的内容（但不要过度惩罚）
                    exclude_keywords = keyword_config.get_exclude_keywords()
                    has_exclude_keywords = any(keyword in content_lower for keyword in exclude_keywords)
                    
                    if has_exclude_keywords:
                        # 检查是否同时包含相关关键词，如果有则不进行惩罚
                        relevant_keywords = ["测试", "用例", "需求", "功能", "应用", "系统", "开发", "技术", "软件"]
                        has_relevant_keywords = any(keyword in content_lower for keyword in relevant_keywords)
                        
                        if has_relevant_keywords:
                            # 如果包含相关关键词，只轻微降分
                            relevance_score *= 0.9
                            logger.debug(f"包含排除关键词但有关键词，轻微降分: {relevance_score:.3f}")
                        else:
                            # 如果不包含相关关键词，适度降分
                            relevance_score *= 0.3
                    
                    # 智能阈值调整：必须同时满足关键词匹配和语义相似度要求
                    adjusted_threshold = min_relevance_score
                    if keyword_matches > 0 and len(requirement_keywords) > 0:
                        keyword_match_ratio = keyword_matches / len(requirement_keywords)
                        
                        # 更严格的调整条件：必须同时满足关键词匹配和语义相似度
                        # 语义相似度必须 >= 0.5 才考虑降低阈值
                        if semantic_score >= 0.5:
                            if keyword_match_ratio >= 0.5:  # 关键词匹配率 >= 50%
                                # 根据匹配率动态调整，但更保守
                                if keyword_match_ratio >= 0.7 and semantic_score >= 0.6:  # 高匹配率+高语义相似度
                                    adjusted_threshold = min_relevance_score * 0.85  # 只降低15%
                                elif keyword_match_ratio >= 0.5 and semantic_score >= 0.55:  # 中等匹配率+中等语义相似度
                                    adjusted_threshold = min_relevance_score * 0.9  # 只降低10%
                    
                    # 保存相关性得分到文档对象（无论是否通过，用于二次降级）
                    if not hasattr(doc, 'metadata') or doc.metadata is None:
                        doc.metadata = {}
                    doc.metadata['relevance_score'] = relevance_score
                    
                    # 判断是否通过阈值
                    if relevance_score >= adjusted_threshold:
                        filtered_results.append(doc)
                        
                except Exception as e:
                    logger.warning(f"处理文档时出错: {e}")
                    continue
            
            # 按相关性得分排序
            filtered_results.sort(key=lambda x: getattr(x, 'metadata', {}).get('relevance_score', 0), reverse=True)

            # 去重处理：移除相似度过高的重复内容
            deduplicated_results = self._deduplicate_documents(filtered_results)

            # 二次降级机制：如果第一次过滤后结果为空，降低阈值重试
            if len(deduplicated_results) == 0 and len(search_results) > 0:
                logger.info(f"RAG增强：第一次过滤后无结果，启用二次降级机制（降低阈值）")
                # 计算所有文档的最高得分（所有文档的得分已在第一次过滤时保存）
                max_score = 0.0
                for doc in search_results:
                    try:
                        if hasattr(doc, 'metadata') and doc.metadata and 'relevance_score' in doc.metadata:
                            max_score = max(max_score, doc.metadata['relevance_score'])
                    except (AttributeError, KeyError, TypeError, ValueError) as e:
                        # 忽略单个文档的元数据访问错误，继续处理其他文档
                        logger.debug(f"获取文档得分失败: {e}")
                        pass
                
                # 如果最高得分接近阈值（在阈值的70%-100%范围内），进一步降低阈值
                if max_score > 0 and max_score >= min_relevance_score * 0.7:
                    # 降低阈值到最高得分的95%（给一点缓冲，但不要降太低）
                    fallback_threshold = max_score * 0.95
                    logger.info(f"二次降级：最高得分 {max_score:.3f}，降低阈值到 {fallback_threshold:.3f} (原始阈值: {min_relevance_score:.3f})")
                    
                    # 使用降低后的阈值重新过滤
                    for doc in search_results:
                        try:
                            if hasattr(doc, 'metadata') and doc.metadata and 'relevance_score' in doc.metadata:
                                score = doc.metadata['relevance_score']
                                if score >= fallback_threshold:
                                    deduplicated_results.append(doc)
                                    logger.debug(f"二次过滤通过：得分 {score:.3f} >= 阈值 {fallback_threshold:.3f}")
                        except (AttributeError, KeyError, TypeError, ValueError) as e:
                            # 忽略单个文档的元数据访问错误，继续处理其他文档
                            logger.debug(f"二次过滤处理文档失败: {e}")
                    
                    # 重新排序和去重
                    deduplicated_results.sort(key=lambda x: getattr(x, 'metadata', {}).get('relevance_score', 0), reverse=True)
                    deduplicated_results = self._deduplicate_documents(deduplicated_results)
                    
                    if len(deduplicated_results) > 0:
                        logger.info(f"二次降级成功：找到 {len(deduplicated_results)} 个相关文档")
                    else:
                        logger.info(f"二次降级后仍无结果，跳过知识库增强")
                else:
                    logger.info(f"二次降级：最高得分 {max_score:.3f} 过低（< {min_relevance_score * 0.7:.3f}），跳过降级")

            logger.info(f"RAG增强：找到{len(filtered_results)}个相关文档，去重后剩余{len(deduplicated_results)}个文档")

            return deduplicated_results
            
        except Exception as e:
            logger.error(f"相关性过滤失败: {e}")
            return search_results  # 出错时返回原始结果
    
    @staticmethod
    def _enhance_search_query(requirement_text: str) -> str:
        """
        增强搜索查询（查询扩展）
        
        注意：如果使用 SmartRetrievalStrategy，查询扩展已内置，此方法仅用于降级场景
        
        Args:
            requirement_text: 原始需求文本
            
        Returns:
            增强后的查询文本
        """
        try:
            # 提取核心概念（与 rag_keyword_config 整合）
            from utils.utils_intelligent_retrieval.requirement_keyword_extractor import get_requirement_keyword_extractor
            from utils.utils_intelligent_retrieval.rag_keyword_config import get_rag_keyword_config
            
            keyword_config = get_rag_keyword_config()
            keyword_extractor = get_requirement_keyword_extractor(keyword_config)
            core_concepts = keyword_extractor.extract_core_concepts(requirement_text)
            
            # 构建增强查询：原始文本 + 核心关键词
            enhanced_parts = [requirement_text]
            
            # 添加技术术语和实体
            if core_concepts['tech_terms']:
                enhanced_parts.append(' '.join(core_concepts['tech_terms']))
            
            if core_concepts['entities']:
                enhanced_parts.append(' '.join(core_concepts['entities']))
            
            # 添加重要短语
            important_phrases = [p for p in core_concepts['phrases'] if len(p) >= 4]
            if important_phrases:
                enhanced_parts.append(' '.join(important_phrases[:3]))  # 最多3个短语
            
            enhanced_query = ' '.join(enhanced_parts)
            logger.debug(f"查询扩展（降级模式）: {requirement_text[:50]}... -> {enhanced_query[:100]}...")
            
            return enhanced_query
            
        except Exception as e:
            logger.warning(f"查询扩展失败，使用原始查询: {e}")
            return requirement_text

    @staticmethod
    def _deduplicate_documents(documents):
        """
        对文档进行去重处理，移除相似度过高的重复内容

        Args:
            documents: 文档列表

        Returns:
            去重后的文档列表
        """
        if not documents:
            return documents

        # 计算文本相似度的简单方法：基于杰卡德相似度
        def calculate_similarity(text1, text2):
            """计算两个文本的杰卡德相似度系数（Jaccard Similarity）"""
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

        # 获取文档内容
        def get_content(document):
            return document.page_content if hasattr(document, 'page_content') else str(document)

        deduplicated = []

        for doc in documents:
            current_content = get_content(doc)
            is_duplicate = False

            # 检查是否与已有文档过于相似
            for existing_doc in deduplicated:
                existing_content = get_content(existing_doc)
                similarity = calculate_similarity(current_content, existing_content)

                # 如果相似度超过阈值，认为重复
                if similarity > 0.8:  # 相似度阈值80%
                    is_duplicate = True
                    logger.debug(f"发现重复文档，相似度: {similarity:.3f}")
                    break

            if not is_duplicate:
                deduplicated.append(doc)

        return deduplicated

    def batch_generate_cases(
            self,
            requirements: List[Union[str, Dict[str, Any]]],
            use_rag: bool = False,
            case_count_per_req: int = 3,
            process_mode: str = 'sequential',
            output_language: str = None,
            llm=None,
            vector_db=None
    ) -> Dict[str, Any]:
        """
        批量生成测试用例

        Args:
            requirements: 需求列表
            use_rag: 是否使用RAG增强
            case_count_per_req: 每个需求生成的用例数量
            process_mode: 处理模式 ('sequential' 或 'parallel')
            output_language: 输出语言（zh/en），为空时自动推断
            llm: 语言模型实例
            vector_db: 向量数据库实例

        Returns:
            批量生成结果
        """
        try:
            case_count_per_req = clamp_cases_per_requirement(case_count_per_req, 3)
            if not requirements:
                return {
                    'success': False,
                    'message': '需求列表为空',
                    'error': ec.VALIDATION_FAILED,
                    'error_code': ec.VALIDATION_FAILED,
                    'status_code': 400,
                    'retryable': False
                }

            # 检查总用例数限制
            max_case_num = getattr(settings, 'MAX_CASE_NUM', 50)
            total_expected_cases = len(requirements) * case_count_per_req
            
            if total_expected_cases > max_case_num:
                return {
                    'success': False,
                    'message': f'批量生成用例数({total_expected_cases})超过最大限制({max_case_num})，请减少需求数量或每个需求的生成数量',
                    'error': ec.VALIDATION_FAILED,
                    'error_code': ec.VALIDATION_FAILED,
                    'status_code': 400,
                    'retryable': False,
                    'max_case_num': max_case_num,
                    'requested_cases': total_expected_cases
                }

            # 开始性能监控
            self.performance_monitor.start_monitoring()

            results = []
            total_cases = 0
            success_count = 0

            # 根据处理模式选择处理方式
            if process_mode == 'parallel':
                # 并行处理
                results, total_cases, success_count = self._process_requirements_parallel(
                    requirements, use_rag, case_count_per_req, output_language, llm, vector_db
                )
                # 并行处理时统一更新计数
                self.performance_monitor.update_processed_count(total_cases)
            else:
                # 顺序处理（原有逻辑）
                if len(requirements) > settings.CHUNK_SIZE:
                    processor = self._get_streaming_processor()

                    for chunk in processor.process_requirements_streaming(requirements):
                        chunk_results = self._process_requirements_chunk(
                            chunk, use_rag, case_count_per_req, output_language, llm, vector_db
                        )
                        results.extend(chunk_results['results'])
                        total_cases += chunk_results['total_cases']
                        success_count += chunk_results['success_count']
                else:
                    # 直接处理小批量需求
                    chunk_results = self._process_requirements_chunk(
                        requirements, use_rag, case_count_per_req, output_language, llm, vector_db
                    )
                    results = chunk_results['results']
                    total_cases = chunk_results['total_cases']
                    success_count = chunk_results['success_count']

            # 更新处理计数（只在非并行模式下更新，避免重复计数）
            # 注意：顺序处理时，每个generate_cases调用已经更新了计数，这里不需要重复更新
            # if process_mode != 'parallel':
            #     self.performance_monitor.update_processed_count(total_cases)

            # 停止性能监控并获取统计信息
            self.performance_monitor.stop_monitoring()
            performance_stats = self.performance_monitor.get_performance_stats()

            # 记录性能摘要
            self.performance_monitor.log_performance_summary()

            return {
                'success': True,
                'message': f'批量生成完成，处理{len(requirements)}个需求，生成{total_cases}个用例',
                'results': results,
                'summary': {
                    'total_requirements': len(requirements),
                    'success_requirements': success_count,
                    'total_cases': total_cases,
                    'generation_time': performance_stats['elapsed_time'],
                    'processing_rate': performance_stats['processing_rate'],
                    'use_rag': use_rag,
                    'performance_stats': performance_stats
                }
            }

        except Exception as e:
            # 确保停止监控
            self.performance_monitor.stop_monitoring()
            return build_model_error_result(
                getattr(settings, 'DEFAULT_COMPANY', 'OPENAI'),
                e,
                fallback_message='批量生成失败'
            )

    def _get_streaming_processor(self):
        """获取流式处理器"""

        class StreamingCaseProcessor:
            def __init__(self, chunk_size, max_memory_mb):
                self.chunk_size = chunk_size
                self.max_memory_mb = max_memory_mb

            def process_requirements_streaming(self, requirements):
                # 简单的分块处理
                for i in range(0, len(requirements), self.chunk_size):
                    yield requirements[i:i + self.chunk_size]

        return StreamingCaseProcessor(
            chunk_size=settings.CHUNK_SIZE,
            max_memory_mb=settings.MAX_MEMORY_MB
        )

    def _process_requirements_chunk(
            self,
            requirements: List[Union[str, Dict[str, Any]]],
            use_rag: bool,
            case_count_per_req: int,
            output_language: str,
            llm,
            vector_db,
            batch_size: int = 5  # 每批处理的需求数量
    ) -> Dict[str, Any]:
        """处理需求块 - 支持批量生成（多个需求合并到一个LLM请求）"""
        results = []
        total_cases = 0
        success_count = 0
        
        total_requirements = len(requirements)
        total_batches = (total_requirements + batch_size - 1) // batch_size  # 向上取整
        
        logger.info(f"📋 批量生成任务：共{total_requirements}个需求，每个需求{case_count_per_req}个用例")
        logger.info(f"📦 智能分批：将分为{total_batches}批处理（每批最多{batch_size}个需求）")

        # 将需求分批处理
        for batch_index, batch_start in enumerate(range(0, len(requirements), batch_size), 1):
            batch = requirements[batch_start:batch_start + batch_size]
            batch_size_actual = len(batch)
            
            logger.info(f"🔄 正在处理第{batch_index}/{total_batches}批：{batch_size_actual}个需求")
            
            # 如果只有1个需求，使用原来的单个生成方式（保持兼容性）
            if len(batch) == 1:
                req = batch[0]
                req_id = f'req_{batch_start + 1}'
                
                try:
                    if isinstance(req, str):
                        req_text = req
                    else:
                        req_text = req.get('content') or req.get('text', '')
                        req_id = req.get('id', f'req_{batch_start + 1}')
                    
                    if not req_text:
                        results.append({
                            'requirement_id': req_id,
                            'success': False,
                            'message': '需求内容为空',
                            'cases': []
                        })
                        continue

                    result = self.generate_cases(
                        requirement_text=req_text,
                        use_rag=use_rag,
                        case_count=case_count_per_req,
                        category='functional',
                        output_language=output_language,
                        llm=llm,
                        vector_db=vector_db,
                        start_monitoring=False
                    )

                    if result['success']:
                        success_count += 1
                        total_cases += len(result['cases'])

                    results.append({
                        'requirement_id': req_id,
                        'success': result['success'],
                        'message': result.get('message', ''),
                        'cases': result.get('cases', [])
                    })
                except Exception as e:
                    logger.error(f"处理需求 {req_id} 失败: {e}")
                    results.append({
                        'requirement_id': req_id,
                        'success': False,
                        'message': '处理失败',
                        'cases': []
                    })
            else:
                # 多个需求批量生成
                try:
                    batch_result = self._generate_cases_batch(
                        requirements_batch=batch,
                        batch_start_index=batch_start,
                        use_rag=use_rag,
                        case_count_per_req=case_count_per_req,
                        output_language=output_language,
                        llm=llm,
                        vector_db=vector_db
                    )
                    
                    # 将批量结果添加到results
                    for req_result in batch_result['results']:
                        if req_result['success']:
                            success_count += 1
                            total_cases += len(req_result['cases'])
                        results.append(req_result)
                        
                except TokenSessionLimitExceeded:
                    raise
                except Exception as e:
                    logger.error(f"批量处理需求失败: {e}，降级为逐个生成")
                    # 批量失败时，降级为逐个生成
                    for i, req in enumerate(batch):
                        req_id = f'req_{batch_start + i + 1}'
                        req_text = req if isinstance(req, str) else req.get('content') or req.get('text', '')
                        
                        if isinstance(req, dict):
                            req_id = req.get('id', req_id)
                        
                        if not req_text:
                            results.append({
                                'requirement_id': req_id,
                                'success': False,
                                'message': '需求内容为空',
                                'cases': []
                            })
                            continue
                        
                        try:
                            logger.info(f"单独生成需求 {req_id}")
                            result = self.generate_cases(
                                requirement_text=req_text,
                                use_rag=use_rag,
                                case_count=case_count_per_req,
                                output_language=output_language,
                                llm=llm,
                                vector_db=vector_db,
                                start_monitoring=False
                            )
                            
                            if result['success']:
                                success_count += 1
                                total_cases += len(result.get('cases', []))
                            
                            results.append({
                                'requirement_id': req_id,
                                'success': result['success'],
                                'message': result.get('message', ''),
                                'cases': result.get('cases', [])
                            })
                        except Exception as single_err:
                            logger.error(f"单独生成需求 {req_id} 失败: {single_err}")
                            results.append({
                                'requirement_id': req_id,
                                'success': False,
                                'message': '生成失败',
                                'cases': []
                            })

        return {
            'results': results,
            'total_cases': total_cases,
            'success_count': success_count
        }

    def _generate_cases_batch(  # noqa: PLR0913
            self,
            requirements_batch: List[Union[str, Dict[str, Any]]],
            batch_start_index: int,
            use_rag: bool,  # noqa: ARG001
            case_count_per_req: int,
            output_language: str,
            llm,
            vector_db  # noqa: ARG001
    ) -> Dict[str, Any]:
        """批量生成用例（多个需求合并到一个LLM请求）
        
        Args:
            requirements_batch: 需求批次列表
            batch_start_index: 批次起始索引
            use_rag: 是否使用RAG增强（暂未实现，保留用于将来扩展）
            case_count_per_req: 每个需求生成的用例数量
            output_language: 输出语言（zh/en）
            llm: 语言模型实例
            vector_db: 向量数据库实例（暂未实现，保留用于将来扩展）
        """
        from config.settings import settings
        
        # 抑制未使用参数的警告（保留用于将来扩展）
        _ = use_rag, vector_db
        
        # 准备需求列表
        requirements_list = []
        req_id_mapping = {}  # 映射 req_id -> 原始需求
        
        for i, req in enumerate(requirements_batch):
            req_id = f'req_{batch_start_index + i + 1}'
            
            if isinstance(req, str):
                req_text = req
            else:
                req_text = req.get('content') or req.get('text', '')
                req_id = str(req.get('id') or req.get('req_id') or req_id)
            
            if not req_text:
                continue
                
            requirements_list.append(f"{i+1}. [需求ID: {req_id}] {req_text}")
            req_id_mapping[req_id] = req
        
        if not requirements_list:
            return {
                'results': [],
                'total_cases': 0,
                'success_count': 0
            }
        
        req_count = len(requirements_list)
        total_expected_cases = req_count * case_count_per_req
        
        # 构建批量prompt
        requirements_text = '\n'.join(requirements_list)
        
        # 复杂度分析和建议（批量生成时使用通用值）
        complexity_analysis = "复杂度等级: medium, 得分: 5"  # 简化处理
        suggested_test_types = "功能测试, 回归测试, 接口测试"
        suggested_methods = "等价类划分法, 边界值分析法, 判定表法"
        
        if output_language == 'en':
            format_instructions = "Return strict JSON with English field names, and all test case content must be in English."
        else:
            format_instructions = "请严格返回 JSON 格式，字段名必须是英文，但所有测试用例内容必须使用中文"
        
        # 使用批量prompt模板
        prompt = settings.BATCH_FUNCTION_PROMPT.format(
            max_case_nums=case_count_per_req,
            requirements_list=requirements_text,
            complexity_analysis=complexity_analysis,
            suggested_test_types=suggested_test_types,
            suggested_methods=suggested_methods,
            format_instructions=format_instructions
        )
        
        logger.info(f"  ├─ 本批{req_count}个需求，每个需求{case_count_per_req}个用例，预期生成{total_expected_cases}个用例")
        
        # 调用LLM
        ensure_session_budget()
        try:
            try:
                response = llm.invoke(prompt)
            except Exception:
                track_session_usage()
                raise
            record_message_usage(response, source='case_generation')
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # 提取JSON部分 - 使用栈匹配找到完整的JSON对象
            def extract_json(text):
                """从文本中提取完整的JSON对象"""
                # 先尝试找到第一个{
                start = text.find('{')
                if start == -1:
                    return None
                
                # 使用栈来匹配完整的JSON
                stack = []
                in_string = False
                escape_next = False
                
                for idx in range(start, len(text)):
                    char = text[idx]
                    
                    # 处理字符串内的字符
                    if escape_next:
                        escape_next = False
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        continue
                    
                    if char == '"':
                        in_string = not in_string
                        continue
                    
                    if in_string:
                        continue
                    
                    # 处理括号
                    if char in '{[':
                        stack.append(char)
                    elif char == '}':
                        if stack and stack[-1] == '{':
                            stack.pop()
                            if not stack:  # 栈为空，找到完整JSON
                                return text[start:idx+1]
                    elif char == ']':
                        if stack and stack[-1] == '[':
                            stack.pop()
                
                return None
            
            json_str = extract_json(response_text)
            if json_str:
                # 记录JSON字符串的长度和前500字符用于调试
                logger.debug(f"提取的JSON长度: {len(json_str)}, 前500字符: {json_str[:500]}")
                
                try:
                    response_data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON解析失败，尝试修复: {e}")
                    logger.debug(f"问题位置附近的内容: {json_str[max(0, e.pos-50):e.pos+50]}")
                    
                    # 尝试修复常见的JSON错误
                    json_str_fixed = json_str
                    
                    # 1. 修复缺少逗号的情况（在}后面接"应该有逗号）
                    json_str_fixed = re.sub(r'}\s*"', '},\n"', json_str_fixed)
                    # 2. 修复缺少逗号的情况（在]后面接"应该有逗号）
                    json_str_fixed = re.sub(r']\s*"', '],\n"', json_str_fixed)
                    # 3. 修复缺少冒号的情况（在"key" "value"之间应该有冒号）
                    json_str_fixed = re.sub(r'"\s+"', '": "', json_str_fixed)
                    # 4. 修复多余的逗号（对象或数组的最后一个元素后面）
                    json_str_fixed = re.sub(r',(\s*[}\]])', r'\1', json_str_fixed)
                    
                    try:
                        response_data = json.loads(json_str_fixed)
                        logger.info("JSON修复成功")
                    except Exception as fix_err:
                        logger.error(f"JSON修复失败: {fix_err}")
                        # 记录修复后的JSON用于调试
                        logger.debug(f"修复后的JSON前500字符: {json_str_fixed[:500]}")
                        raise e
            else:
                logger.warning("未能提取JSON对象，尝试直接解析")
                response_data = json.loads(response_text)
            
            # 按requirement_id分组用例
            cases_by_req = {}
            total_returned_cases = len(response_data.get('cases', []))
            logger.info(f"LLM返回了{total_returned_cases}个用例")
            
            for case in response_data.get('cases', []):
                if not isinstance(case, dict):
                    continue
                req_id = str(case.pop('requirement_id', '') or '')
                bucket = cases_by_req.setdefault(req_id, [])
                if len(bucket) < case_count_per_req:
                    bucket.append(case)
            
            # 记录每个需求的用例数量
            for req_id, cases in cases_by_req.items():
                logger.info(f"  - {req_id}: {len(cases)}个用例")
            
            # 构建结果，合批路径补上与单次生成相同的幻觉检测
            results = []
            for req_id, req in req_id_mapping.items():
                cases = cases_by_req.get(req_id, [])
                if len(cases) == 0:
                    logger.warning(f"需求 {req_id} 未生成任何用例")
                req_text = req if isinstance(req, str) else (req.get('content') or req.get('text') or '')
                detection = None
                if cases:
                    cases, detection = self._apply_hallucination_guard(cases, req_text, '', llm)
                item = {
                    'requirement_id': req_id,
                    'success': len(cases) > 0,
                    'message': f'成功生成{len(cases)}个用例' if cases else '未生成用例',
                    'cases': cases
                }
                if detection:
                    item['hallucination_detection'] = detection
                results.append(item)
            
            return {
                'results': results,
                'total_cases': sum(len(item['cases']) for item in results),
                'success_count': len([r for r in results if r['success']])
            }
            
        except TokenSessionLimitExceeded:
            raise
        except Exception as e:
            logger.error(f"批量生成用例失败: {e}")
            message = build_model_error_result(
                getattr(settings, 'DEFAULT_COMPANY', 'OPENAI'), e, fallback_message='批量生成失败'
            )['message']
            results = []
            for req_id in req_id_mapping.keys():
                results.append({
                    'requirement_id': req_id,
                    'success': False,
                    'message': message,
                    'cases': []
                })
            return {
                'results': results,
                'total_cases': 0,
                'success_count': 0
            }

    def _process_requirements_parallel(
            self,
            requirements: List[Union[str, Dict[str, Any]]],
            use_rag: bool,
            case_count_per_req: int,
            output_language: str,
            llm,
            vector_db
    ) -> tuple:
        """并行处理需求列表"""
        import concurrent.futures
        
        results = []
        total_cases = 0
        success_count = 0
        
        # 使用线程池并行处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # 提交所有任务
            future_to_req = {}
            for i, req in enumerate(requirements):
                # 初始化变量
                req_id = f'req_{i+1}'
                
                if isinstance(req, str):
                    req_text = req
                else:
                    req_text = req.get('content') or req.get('text', '')
                    req_id = req.get('id', f'req_{i+1}')
                
                if req_text:
                    future = executor.submit(
                        self._process_single_requirement,
                        req_text, req_id, use_rag, case_count_per_req, output_language, llm, vector_db
                    )
                    future_to_req[future] = req_id
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_req):
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['success']:
                        success_count += 1
                        total_cases += result['case_count']
                        
                except (KeyError, TypeError, ValueError, RuntimeError) as exc:
                    logger.error(f"并行处理需求失败: {exc}")
                    req_id = future_to_req[future]
                    results.append({
                        'requirement_id': req_id,
                        'success': False,
                        'message': '并行处理失败',
                        'cases': [],
                        'case_count': 0
                    })
        
        return results, total_cases, success_count
    
    def _process_single_requirement(
            self,
            req_text: str,
            req_id: str,
            use_rag: bool,
            case_count_per_req: int,
            output_language: str,
            llm,
            vector_db
    ) -> Dict[str, Any]:
        """处理单个需求（用于并行处理）"""
        try:
            result = self.generate_cases(
                requirement_text=req_text,
                use_rag=use_rag,
                case_count=case_count_per_req,
                category='functional',
                output_language=output_language,
                llm=llm,
                vector_db=vector_db,
                start_monitoring=False  # 并行处理时不启动性能监控
            )
            
            return {
                'requirement_id': req_id,
                'success': result['success'],
                'message': result['message'],
                'cases': result.get('cases', []),
                'case_count': len(result.get('cases', []))
            }
            
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            logger.error(f"处理需求失败: {exc}")
            return {
                'requirement_id': req_id,
                'success': False,
                'message': '处理需求失败',
                'cases': [],
                'case_count': 0
            }

    @staticmethod
    def optimize_cases(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        优化测试用例（去重、分类、排序等）

        Args:
            cases: 原始用例列表

        Returns:
            优化后的用例列表
        """
        try:
            if not cases:
                return cases

            # 转换为DataFrame进行处理
            df = pd.DataFrame(cases)

            # 去重（基于标题和步骤）
            df = df.drop_duplicates(subset=['title', 'steps'], keep='first')

            # 按优先级排序
            priority_order = {'P0': 1, 'P1': 2, 'P2': 3, 'P3': 4, 'P4': 5}
            df['priority_order'] = df['priority'].map(priority_order).fillna(2)
            df = df.sort_values(['priority_order', 'title'])
            df = df.drop('priority_order', axis=1)

            # 重新分配用例编号
            for i, (index, row) in enumerate(df.iterrows()):
                title = row.get('title', f'优化用例_{i + 1}')
                df.at[index, 'case_id'] = f"TC-{generate_id(title)}-{i + 1:02d}"

            return df.to_dict('records')

        except Exception as e:
            logger.warning(f"用例优化失败: {e}")
            return cases

    @staticmethod
    def validate_cases(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证测试用例的完整性和有效性

        Args:
            cases: 用例列表

        Returns:
            验证结果
        """
        try:
            validation_results = {
                'valid_cases': [],
                'invalid_cases': [],
                'warnings': [],
                'statistics': {
                    'total': len(cases),
                    'valid': 0,
                    'invalid': 0
                }
            }

            required_fields = ['case_id', 'title', 'steps']

            for i, case in enumerate(cases):
                issues = []

                # 检查必需字段
                for field in required_fields:
                    if not case.get(field):
                        issues.append(f"缺少必需字段: {field}")

                # 检查步骤格式
                steps = case.get('steps', [])
                if not isinstance(steps, list) or len(steps) == 0:
                    issues.append("测试步骤不能为空")

                # 检查标题长度
                title = case.get('title', '')
                if len(title) > 200:
                    issues.append("标题过长（超过200字符）")
                elif len(title) < 5:
                    issues.append("标题过短（少于5字符）")

                if issues:
                    validation_results['invalid_cases'].append({
                        'index': i,
                        'case_id': case.get('case_id', 'unknown'),
                        'issues': issues
                    })
                    validation_results['statistics']['invalid'] += 1
                else:
                    validation_results['valid_cases'].append(case)
                    validation_results['statistics']['valid'] += 1

            return validation_results

        except (TypeError, KeyError, ValueError, AttributeError) as exc:
            logger.warning(f"验证过程出错: {exc}")
            return {
                'valid_cases': cases,
                'invalid_cases': [],
                'warnings': ["验证过程出错"],
                'statistics': {
                    'total': len(cases),
                    'valid': len(cases),
                    'invalid': 0
                }
            }

    def _apply_hallucination_guard(self, cases, requirement_text, context, llm):
        """对一批用例做幻觉检测，并把可处理的结果写回用例。"""
        if not cases or not getattr(settings, 'ENABLE_HALLUCINATION_DETECTION', True):
            return cases, None
        try:
            detection = self._detect_hallucination_in_cases(cases, requirement_text, context or '', llm)
            logger.info(f"幻觉检测完成，检测到{detection.get('hallucination_count', 0)}个潜在问题")
            final_cases = cases
            if detection.get('hallucination_count', 0) > 0:
                final_cases = self._handle_hallucination_in_cases(
                    cases,
                    detection,
                    requirement_text,
                    llm
                )
                logger.info(f"幻觉处理完成，最终返回{len(final_cases)}个用例")
            return final_cases, detection
        except (TypeError, ValueError, KeyError, RuntimeError, AttributeError, OSError) as exc:
            logger.warning(f"幻觉检测失败: {exc}")
            return cases, None

    @staticmethod
    def _apply_labeled_case_text(case: Dict[str, Any], text: str) -> bool:
        """把“标题/步骤/预期结果/前置条件”标签文本写回结构化用例。"""
        if not isinstance(text, str) or not text.strip() or not isinstance(case, dict):
            return False
        labels = {
            '标题': 'title',
            '步骤': 'steps',
            '预期结果': 'expected_result',
            '前置条件': 'precondition',
            'Title': 'title',
            'Steps': 'steps',
            'Expected': 'expected_result',
            'Precondition': 'precondition',
        }
        buckets = {key: [] for key in ('title', 'steps', 'expected_result', 'precondition')}
        current_key = None
        found = False
        for raw_line in text.splitlines():
            line = raw_line.strip()
            matched = None
            value = ''
            for label, key in labels.items():
                for sep in (':', '：'):
                    prefix = f'{label}{sep}'
                    if line.startswith(prefix):
                        matched = key
                        value = line[len(prefix):].strip()
                        break
                if matched:
                    break
            if matched:
                found = True
                current_key = matched
                if value:
                    buckets[matched].append(value)
                continue
            if current_key and line:
                buckets[current_key].append(line)
        if not found:
            return False

        def split_items(parts):
            items = []
            for part in parts:
                items.extend(item.strip() for item in re.split(r'[;；]', part) if item.strip())
            return items

        if buckets['title']:
            case['title'] = ' '.join(buckets['title']).strip()
        if buckets['precondition']:
            case['precondition'] = '\n'.join(buckets['precondition']).strip()
        steps = split_items(buckets['steps'])
        if steps:
            case['steps'] = steps
        expected = split_items(buckets['expected_result'])
        if expected:
            case['expected_result'] = expected
        return True

    def _handle_hallucination_in_cases(self, cases: List[Dict[str, Any]], 
                                     hallucination_results: Dict[str, Any],
                                     requirement_text: str,
                                     llm) -> List[Dict[str, Any]]:
        """
        处理测试用例中的幻觉
        
        Args:
            cases: 原始用例列表
            hallucination_results: 幻觉检测结果
            requirement_text: 需求文本
            llm: 语言模型实例
            
        Returns:
            处理后的用例列表
        """
        try:
            processed_cases = []
            handling_results = []
            
            # 获取检测结果
            cases_with_detection = hallucination_results.get('cases_with_detection', cases)
            
            for i, case in enumerate(cases_with_detection):
                # 检查是否有幻觉检测结果
                detection_info = case.get('hallucination_detection')
                if detection_info and detection_info.get('is_hallucination', False):
                    snapshot = {
                        key: list(case.get(key)) if isinstance(case.get(key), list) else case.get(key)
                        for key in ('title', 'steps', 'expected_result', 'precondition')
                    }
                    # 创建检测结果对象
                    from utils.utils_ai_quality.hallucination_detector import HallucinationResult
                    detection_result = HallucinationResult(
                        is_hallucination=detection_info['is_hallucination'],
                        confidence=detection_info['confidence'],
                        issues=detection_info['issues'],
                        suggestions=detection_info['suggestions'],
                        source_verification={}
                    )
                    
                    # 处理幻觉
                    case_content = f"标题: {case.get('title', '')}\n"
                    case_content += f"步骤: {'; '.join(case.get('steps', []))}\n"
                    case_content += f"预期结果: {case.get('expected_result', '')}\n"
                    case_content += f"前置条件: {case.get('precondition', '')}"
                    
                    handling_result = self.hallucination_handler.handle_hallucination(
                        case_content, 
                        detection_result, 
                        requirement_text, 
                        llm
                    )
                    
                    handling_results.append(handling_result)
                    
                    # 根据处理结果决定是否保留用例，并把可解析的修正写回字段
                    if handling_result.is_approved and handling_result.processed_content:
                        applied = self._apply_labeled_case_text(case, handling_result.processed_content)
                        case['hallucination_handled'] = True
                        case['handling_action'] = handling_result.action_taken.value
                        warnings = list(handling_result.warnings or [])
                        if not applied and handling_result.action_taken.value in ('auto_correct', 'regenerate'):
                            warnings.append('修正内容未能解析回结构化用例，已保留原文')
                        if applied and handling_result.action_taken.value == 'regenerate':
                            recheck_content = (
                                f"标题: {case.get('title', '')}\n"
                                f"步骤: {'; '.join(case.get('steps', []) if isinstance(case.get('steps'), list) else [str(case.get('steps') or '')])}\n"
                                f"预期结果: {case.get('expected_result', '')}\n"
                                f"前置条件: {case.get('precondition', '')}"
                            )
                            still_bad = [
                                claim for claim in assess_quantified_claims(
                                    recheck_content,
                                    requirement_text,
                                    case_allows_unmentioned(case),
                                )
                                if claim.get('verdict') == 'contradicted'
                            ]
                            if still_bad:
                                case.update(snapshot)
                                warnings.append(
                                    '重写后数量和单位仍与原文不一致，已保留原用例：'
                                    + contradiction_issue(still_bad[0])
                                )
                        case['handling_warnings'] = warnings
                        processed_cases.append(case)
                    else:
                        # 用例被过滤掉
                        logger.info(f"用例 {case.get('case_id', i)} 因幻觉问题被过滤")
                else:
                    # 没有幻觉问题，直接保留
                    processed_cases.append(case)
            
            # 记录处理统计
            total_handled = len(handling_results)
            approved_count = sum(1 for r in handling_results if r.is_approved)
            filtered_count = total_handled - approved_count
            
            logger.info(f"幻觉处理统计: 处理{total_handled}个，通过{approved_count}个，过滤{filtered_count}个")
            
            return processed_cases
            
        except Exception as e:
            logger.error(f"幻觉处理失败: {e}")
            # 处理失败时返回原始用例
            return cases