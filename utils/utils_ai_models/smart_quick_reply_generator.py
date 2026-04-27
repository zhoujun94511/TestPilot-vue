"""
智能快速回复生成器
基于AI和上下文分析生成个性化的快速回复建议
"""

import time
from typing import List, Dict, Any
from dataclasses import dataclass
from utils.utils_core.logger import get_logger
from utils.utils_ai_models.get_llm import get_llm_instance
from config.settings import settings

logger = get_logger(__name__)


@dataclass
class QuickReplySuggestion:
    """快速回复建议数据结构"""
    text: str
    confidence: float
    category: str
    context_relevance: float
    user_preference_score: float = 0.0


class SmartQuickReplyGenerator:
    """智能快速回复生成器"""
    
    def __init__(self, llm=None):
        self.llm = llm or get_llm_instance()
        self.logger = logger
        
        # 从配置中获取token限制并计算各部分的token分配
        self._calculate_token_limits()
        
        # 预定义的建议模板和规则
        self.suggestion_templates = {
            'test_case': {
                'keywords': ['测试用例', '用例', '测试场景', '测试方案'],
                'templates': [
                    "如何优化这些测试用例？",
                    "能否提供更多测试场景？",
                    "这些用例的执行顺序如何安排？",
                    "如何提高测试用例的覆盖率？",
                    "这些用例的优先级如何划分？"
                ]
            },
            'test_strategy': {
                'keywords': ['测试策略', '测试计划', '测试方法', '测试流程'],
                'templates': [
                    "这个策略适用于哪些项目类型？",
                    "如何评估测试策略的效果？",
                    "有什么风险需要注意？",
                    "如何调整测试策略以适应变化？",
                    "测试策略的成本效益如何？"
                ]
            },
            'automation': {
                'keywords': ['自动化', '脚本', '工具', 'CI/CD'],
                'templates': [
                    "推荐哪些自动化测试工具？",
                    "自动化测试的投入产出比如何？",
                    "如何维护自动化测试脚本？",
                    "自动化测试的最佳实践有哪些？",
                    "如何选择合适的自动化框架？"
                ]
            },
            'bug_analysis': {
                'keywords': ['缺陷', '错误', 'bug', '问题', '故障'],
                'templates': [
                    "如何预防类似问题？",
                    "这类缺陷的根本原因是什么？",
                    "有什么最佳实践可以分享？",
                    "如何建立有效的缺陷跟踪机制？",
                    "缺陷分析报告应该包含哪些内容？"
                ]
            },
            'performance': {
                'keywords': ['性能', '效率', '优化', '负载', '压力'],
                'templates': [
                    "性能测试的关键指标有哪些？",
                    "如何进行负载测试？",
                    "性能优化的常见方法？",
                    "如何建立性能基准？",
                    "性能监控的最佳实践？"
                ]
            },
            'requirement': {
                'keywords': ['需求', '规格', '功能', '业务'],
                'templates': [
                    "如何分析需求的完整性？",
                    "需求变更对测试的影响？",
                    "如何验证需求的可行性？",
                    "需求文档应该包含哪些要素？",
                    "如何管理需求变更？"
                ]
            }
        }
        
        # 通用建议模板
        self.generic_templates = [
            "能否详细说明一下？",
            "有具体的例子吗？",
            "还有其他相关问题吗？",
            "这个方案的优缺点是什么？",
            "如何实施这个建议？"
        ]
        
        # 用户行为统计（可以持久化到数据库）
        self.user_preferences = {}
    
    def _calculate_token_limits(self):
        """从配置中读取并计算token限制，使用百分比分配"""
        try:
            # 从配置读取最大token数
            base_max_tokens = getattr(settings, 'MAX_TOKENS', 4000)
            
            # 确保是有效的正整数
            if not isinstance(base_max_tokens, int) or base_max_tokens <= 0:
                self.logger.warning(f"无效的MAX_TOKENS配置: {base_max_tokens}，使用默认值4000")
                base_max_tokens = 4000
            
            # Token分配策略（百分比）
            safety_margin_ratio = 0.75      # 安全余量：使用75%的总token（为响应和系统提示预留25%）
            ai_response_ratio = 0.67        # AI回复占可用token的67%
            context_ratio = 0.17            # 对话上下文占可用token的17%
            # 剩余16%用于系统提示词和格式化文本
            
            # 最小保底值
            min_total_tokens = 500
            min_ai_response_tokens = 200
            min_context_tokens = 100
            
            # 计算实际token限制
            self.max_total_tokens = max(
                int(base_max_tokens * safety_margin_ratio),
                min_total_tokens
            )
            
            self.max_ai_response_tokens = max(
                int(self.max_total_tokens * ai_response_ratio),
                min_ai_response_tokens
            )
            
            self.max_context_tokens = max(
                int(self.max_total_tokens * context_ratio),
                min_context_tokens
            )
            
            # 记录配置信息
            self.logger.debug(
                f"Token限制配置: 基础={base_max_tokens}, "
                f"总计={self.max_total_tokens}, "
                f"AI回复={self.max_ai_response_tokens}, "
                f"上下文={self.max_context_tokens}"
            )
            
        except Exception as e:
            # 容错：使用安全的默认值
            self.logger.error(f"计算token限制失败: {e}，使用默认值")
            self.max_total_tokens = 3000
            self.max_ai_response_tokens = 2000
            self.max_context_tokens = 500
        
    def generate_suggestions(self, 
                           ai_response: str, 
                           conversation_context: List[Dict[str, str]] = None,
                           user_id: str = None,
                           knowledge_context: Dict[str, Any] = None,
                           max_suggestions: int = 3) -> List[QuickReplySuggestion]:
        """
        生成智能快速回复建议
        
        Args:
            ai_response: AI的回复内容
            conversation_context: 对话上下文
            user_id: 用户ID（用于个性化）
            knowledge_context: 知识库上下文数据
            max_suggestions: 最大建议数量
            
        Returns:
            List[QuickReplySuggestion]: 建议列表
        """
        try:
            start_time = time.time()
            
            # 记录AI回复内容用于调试
            self.logger.debug(f"AI回复内容: {ai_response[:100]}...")
            self.logger.debug(f"对话上下文长度: {len(conversation_context or [])}")
            
            # 1. 分析AI回复内容
            content_analysis = self._analyze_content(ai_response)
            
            # 2. 分析对话上下文
            context_analysis = self._analyze_context(conversation_context or [])
            
            # 3. 生成基础建议
            base_suggestions = self._generate_base_suggestions(content_analysis, context_analysis)
            
            # 4. AI增强建议（优先使用AI生成）
            if self.llm:
                try:
                    # 优先使用AI生成建议，如果失败则使用基础建议
                    ai_enhanced = self._generate_ai_enhanced_suggestions(
                        ai_response, conversation_context, max_suggestions
                    )
                    if ai_enhanced:
                        base_suggestions = ai_enhanced  # 使用AI生成的建议
                        self.logger.debug("使用AI增强建议")
                    else:
                        self.logger.debug("AI增强建议生成失败，使用基础建议")
                except Exception as e:
                    self.logger.warning(f"AI增强建议生成异常: {e}")
                    # 继续使用基础建议
            
            # 4.5. 知识库增强建议（可选）
            if knowledge_context and len(base_suggestions) < max_suggestions:
                knowledge_enhanced = self._generate_knowledge_enhanced_suggestions(
                    ai_response, knowledge_context
                )
                base_suggestions.extend(knowledge_enhanced)
            
            # 5. 个性化调整
            personalized_suggestions = self._personalize_suggestions(
                base_suggestions, user_id, content_analysis
            )
            
            # 6. 排序和筛选
            final_suggestions = self._rank_and_filter_suggestions(
                personalized_suggestions, max_suggestions
            )
            
            duration = time.time() - start_time
            self.logger.debug(f"生成快速回复建议耗时: {duration:.3f}秒，生成{len(final_suggestions)}个建议")
            
            return final_suggestions
            
        except Exception as e:
            self.logger.error(f"生成快速回复建议失败: {str(e)}")
            # 返回默认建议
            return self._get_fallback_suggestions(max_suggestions)
    
    def _analyze_content(self, content: str) -> Dict[str, Any]:
        """分析AI回复内容"""
        analysis = {
            'categories': [],
            'keywords': [],
            'sentiment': 'neutral',
            'complexity': 'medium',
            'has_examples': False,
            'has_recommendations': False
        }
        
        # 检测类别
        for category, config in self.suggestion_templates.items():
            for keyword in config['keywords']:
                if keyword in content:
                    analysis['categories'].append(category)
                    break
        
        # 检测关键词
        for category, config in self.suggestion_templates.items():
            analysis['keywords'].extend(config['keywords'])
        
        # 检测情感倾向
        positive_words = ['好', '优秀', '推荐', '建议', '有效', '成功']
        negative_words = ['问题', '错误', '失败', '风险', '注意']
        
        positive_count = sum(1 for word in positive_words if word in content)
        negative_count = sum(1 for word in negative_words if word in content)
        
        if positive_count > negative_count:
            analysis['sentiment'] = 'positive'
        elif negative_count > positive_count:
            analysis['sentiment'] = 'negative'
        
        # 检测复杂度
        if len(content) < 100:
            analysis['complexity'] = 'simple'
        elif len(content) > 500:
            analysis['complexity'] = 'complex'
        
        # 检测是否包含示例
        analysis['has_examples'] = any(word in content for word in ['例如', '比如', '举例', '示例'])
        
        # 检测是否包含建议
        analysis['has_recommendations'] = any(word in content for word in ['建议', '推荐', '应该', '可以'])
        
        return analysis
    
    @staticmethod
    def _analyze_context(context: List[Dict[str, str]]) -> Dict[str, Any]:
        """分析对话上下文"""
        analysis = {
            'topic_continuity': 0.0,
            'question_count': 0,
            'user_expertise_level': 'intermediate',
            'conversation_length': len(context)
        }
        
        if not context:
            return analysis
        
        # 统计问题数量
        analysis['question_count'] = sum(1 for msg in context if '?' in msg.get('content', ''))
        
        # 评估用户专业水平（基于问题复杂度）
        complex_terms = ['架构', '性能', '自动化', 'CI/CD', '微服务', '容器化']
        simple_terms = ['怎么', '什么', '如何', '为什么']
        
        complex_count = sum(1 for msg in context 
                          for term in complex_terms 
                          if term in msg.get('content', ''))
        simple_count = sum(1 for msg in context 
                         for term in simple_terms 
                         if term in msg.get('content', ''))
        
        if complex_count > simple_count:
            analysis['user_expertise_level'] = 'expert'
        elif simple_count > complex_count:
            analysis['user_expertise_level'] = 'beginner'
        
        return analysis
    
    def _generate_base_suggestions(self, 
                                 content_analysis: Dict[str, Any], 
                                 context_analysis: Dict[str, Any]) -> List[QuickReplySuggestion]:
        """生成基础建议"""
        suggestions = []
        
        # 记录上下文分析结果用于调试
        logger.debug(f"上下文分析: 对话长度={context_analysis.get('conversation_length', 0)}, 用户专业水平={context_analysis.get('user_expertise_level', 'unknown')}")
        
        # 基于内容类别生成建议
        for category in content_analysis['categories']:
            if category in self.suggestion_templates:
                templates = self.suggestion_templates[category]['templates']
                for template in templates[:2]:  # 每个类别最多2个建议
                    suggestion = QuickReplySuggestion(
                        text=template,
                        confidence=0.8,
                        category=category,
                        context_relevance=0.9
                    )
                    suggestions.append(suggestion)
        
        # 如果没有匹配的类别，使用通用建议
        if not suggestions:
            for template in self.generic_templates[:3]:
                suggestion = QuickReplySuggestion(
                    text=template,
                    confidence=0.6,
                    category='generic',
                    context_relevance=0.5
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_ai_enhanced_suggestions(self, 
                                       ai_response: str, 
                                       context: List[Dict[str, str]],
                                       count: int) -> List[QuickReplySuggestion]:
        """使用AI生成增强建议"""
        try:
            if not self.llm:
                return []
            
            # 使用动态计算的token限制
            # 截断AI回复（如果太长）
            truncated_ai_response = self._truncate_text(ai_response, self.max_ai_response_tokens)
            if len(truncated_ai_response) < len(ai_response):
                self.logger.debug(
                    f"AI回复被截断: 原长度={len(ai_response)}, "
                    f"截断后={len(truncated_ai_response)}, "
                    f"限制={self.max_ai_response_tokens} tokens"
                )
            
            # 构建并截断对话上下文
            context_text = ""
            if context:
                # 从最新的开始，逐条添加直到达到token限制
                context_messages = []
                max_context_messages = min(5, len(context))  # 最多考虑最近5条
                
                for msg in reversed(context[-max_context_messages:]):
                    msg_text = f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                    context_messages.insert(0, msg_text)
                    temp_context = "\n".join(context_messages)
                    
                    if self._estimate_tokens(temp_context) > self.max_context_tokens:
                        context_messages.pop(0)  # 移除最早的消息
                        break
                
                context_text = "\n".join(context_messages)
                
                if context_messages:
                    self.logger.debug(
                        f"对话上下文: 保留{len(context_messages)}条消息, "
                        f"约{self._estimate_tokens(context_text)} tokens"
                    )
            
            prompt = f"""
你是一个专业的测试助手，专门帮助用户进行软件测试相关的工作。

基于以下AI回复和对话上下文，生成{count}个相关的后续问题建议。

AI回复：
{truncated_ai_response}

对话上下文：
{context_text}

请生成{count}个简洁、相关、实用的后续问题建议，每个建议不超过20个字。
建议应该：
1. 与AI回复内容直接相关
2. 帮助用户深入理解或继续讨论
3. 简洁明了，易于理解
4. 符合中文表达习惯
5. 如果是问候或闲聊，生成友好的回应建议
6. 如果是技术问题，生成深入的技术问题建议

请直接返回建议列表，每行一个建议，不要添加编号或其他格式：
"""
            
            response = self.llm.invoke(prompt)
            suggestions_text = response.content if hasattr(response, 'content') else str(response)
            
            # 解析AI生成的建议
            ai_suggestions = []
            for line in suggestions_text.strip().split('\n'):
                line = line.strip()
                if line and len(line) <= 50:  # 限制长度
                    suggestion = QuickReplySuggestion(
                        text=line,
                        confidence=0.7,
                        category='ai_generated',
                        context_relevance=0.8
                    )
                    ai_suggestions.append(suggestion)
            
            return ai_suggestions[:count]
            
        except Exception as e:
            self.logger.error(f"AI增强建议生成失败: {str(e)}")
            return []
    
    def _personalize_suggestions(self, 
                              suggestions: List[QuickReplySuggestion], 
                              user_id: str,
                              content_analysis: Dict[str, Any]) -> List[QuickReplySuggestion]:
        """个性化建议"""
        if not user_id or user_id not in self.user_preferences:
            return suggestions
        
        user_prefs = self.user_preferences[user_id]
        
        # 记录内容分析结果用于调试
        logger.debug(f"个性化建议: 内容类别={content_analysis.get('categories', [])}, 情感倾向={content_analysis.get('sentiment', 'unknown')}")
        
        # 根据用户偏好调整建议
        for suggestion in suggestions:
            # 基于用户历史偏好调整置信度
            if suggestion.category in user_prefs.get('preferred_categories', []):
                suggestion.user_preference_score += 0.2
            
            # 基于用户专业水平调整
            user_level = user_prefs.get('expertise_level', 'intermediate')
            if user_level == 'expert' and suggestion.category in ['automation', 'performance']:
                suggestion.user_preference_score += 0.1
            elif user_level == 'beginner' and suggestion.category in ['test_case', 'requirement']:
                suggestion.user_preference_score += 0.1
        
        return suggestions
    
    def _rank_and_filter_suggestions(self, 
                                   suggestions: List[QuickReplySuggestion], 
                                   max_count: int) -> List[QuickReplySuggestion]:
        """排序和筛选建议"""
        # 计算综合得分
        for suggestion in suggestions:
            total_score = (
                suggestion.confidence * 0.4 +
                suggestion.context_relevance * 0.4 +
                suggestion.user_preference_score * 0.2
            )
            suggestion.confidence = total_score
        
        # 按得分排序
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        
        # 去重（基于文本相似度）
        unique_suggestions = []
        for suggestion in suggestions:
            is_duplicate = False
            for existing in unique_suggestions:
                if self._calculate_similarity(suggestion.text, existing.text) > 0.8:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:max_count]
    
    def _generate_knowledge_enhanced_suggestions(self, 
                                              ai_response: str,
                                              knowledge_context: Dict[str, Any] = None) -> List[QuickReplySuggestion]:
        """基于知识库和测试用例数据生成增强建议"""
        try:
            suggestions = []
            
            if not knowledge_context:
                return suggestions
            
            # 基于知识库内容生成建议
            if knowledge_context.get('knowledge_docs'):
                suggestions.extend(self._generate_knowledge_based_suggestions(
                    ai_response, knowledge_context['knowledge_docs']
                ))
            
            # 基于测试用例数据生成建议
            if knowledge_context.get('test_cases'):
                suggestions.extend(self._generate_test_case_suggestions(
                    ai_response, knowledge_context['test_cases']
                ))
            
            # 基于需求文档生成建议
            if knowledge_context.get('requirements'):
                suggestions.extend(self._generate_requirement_suggestions(
                    ai_response, knowledge_context['requirements']
                ))
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"知识库增强建议生成失败: {str(e)}")
            return []
    
    @staticmethod
    def _generate_knowledge_based_suggestions(ai_response: str,
                                              knowledge_docs: List[Dict[str, Any]]) -> List[QuickReplySuggestion]:
        """基于知识库文档生成建议"""
        suggestions = []
        
        # 记录AI回复内容用于调试
        logger.debug(f"知识库建议生成: AI回复长度={len(ai_response)}, 文档数量={len(knowledge_docs)}")
        
        # 分析知识库文档类型
        doc_types = set()
        for doc in knowledge_docs:
            if 'metadata' in doc and 'category' in doc['metadata']:
                doc_types.add(doc['metadata']['category'])
        
        # 根据文档类型生成相关建议
        if '测试策略' in doc_types or any('策略' in doc.get('content', '') for doc in knowledge_docs):
            suggestions.append(QuickReplySuggestion(
                text="这个策略在实际项目中如何应用？",
                confidence=0.8,
                category='knowledge_strategy',
                context_relevance=0.9
            ))
        
        if '自动化' in doc_types or any('自动化' in doc.get('content', '') for doc in knowledge_docs):
            suggestions.append(QuickReplySuggestion(
                text="自动化实施过程中有哪些注意事项？",
                confidence=0.8,
                category='knowledge_automation',
                context_relevance=0.9
            ))
        
        if '性能' in doc_types or any('性能' in doc.get('content', '') for doc in knowledge_docs):
            suggestions.append(QuickReplySuggestion(
                text="性能测试的常见瓶颈有哪些？",
                confidence=0.8,
                category='knowledge_performance',
                context_relevance=0.9
            ))
        
        return suggestions
    
    @staticmethod
    def _generate_test_case_suggestions(ai_response: str,
                                        test_cases: List[Dict[str, Any]]) -> List[QuickReplySuggestion]:
        """基于测试用例数据生成建议"""
        suggestions = []
        
        # 记录AI回复内容用于调试
        logger.debug(f"测试用例建议生成: AI回复长度={len(ai_response)}, 用例数量={len(test_cases)}")
        
        if not test_cases:
            return suggestions
        
        # 分析测试用例特征
        case_types = set()
        priorities = set()
        
        for case in test_cases:
            if 'type' in case:
                case_types.add(case['type'])
            if 'priority' in case:
                priorities.add(case['priority'])
        
        # 根据测试用例特征生成建议
        if '功能测试' in case_types:
            suggestions.append(QuickReplySuggestion(
                text="如何设计更全面的功能测试用例？",
                confidence=0.8,
                category='test_case_functional',
                context_relevance=0.9
            ))
        
        if '性能测试' in case_types:
            suggestions.append(QuickReplySuggestion(
                text="性能测试用例的执行顺序如何安排？",
                confidence=0.8,
                category='test_case_performance',
                context_relevance=0.9
            ))
        
        if '高' in priorities:
            suggestions.append(QuickReplySuggestion(
                text="高优先级用例的测试策略是什么？",
                confidence=0.8,
                category='test_case_priority',
                context_relevance=0.9
            ))
        
        return suggestions
    
    @staticmethod
    def _generate_requirement_suggestions(ai_response: str,
                                          requirements: List[Dict[str, Any]]) -> List[QuickReplySuggestion]:
        """基于需求文档生成建议"""
        suggestions = []
        
        # 记录AI回复内容用于调试
        logger.debug(f"需求文档建议生成: AI回复长度={len(ai_response)}, 需求数量={len(requirements)}")
        
        if not requirements:
            return suggestions
        
        # 分析需求特征
        req_types = set()
        complexities = set()
        
        for req in requirements:
            if 'type' in req:
                req_types.add(req['type'])
            if 'complexity' in req:
                complexities.add(req['complexity'])
        
        # 根据需求特征生成建议
        if '功能需求' in req_types:
            suggestions.append(QuickReplySuggestion(
                text="如何验证功能需求的完整性？",
                confidence=0.8,
                category='requirement_functional',
                context_relevance=0.9
            ))
        
        if '非功能需求' in req_types:
            suggestions.append(QuickReplySuggestion(
                text="非功能需求的测试方法有哪些？",
                confidence=0.8,
                category='requirement_non_functional',
                context_relevance=0.9
            ))
        
        if '高' in complexities:
            suggestions.append(QuickReplySuggestion(
                text="复杂需求的测试策略如何制定？",
                confidence=0.8,
                category='requirement_complex',
                context_relevance=0.9
            ))
        
        return suggestions
    
    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """估算文本的token数量（简单估算：中文约1.5字符/token，英文约4字符/token）"""
        if not text:
            return 0
        
        # 简单估算：中文字符较多时按1.5计算，英文较多时按4计算
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        total_chars = len(text)
        
        if chinese_chars > total_chars * 0.5:
            # 中文为主
            return int(total_chars / 1.5)
        else:
            # 英文为主
            return int(total_chars / 4)
    
    @staticmethod
    def _truncate_text(text: str, max_tokens: int) -> str:
        """根据token限制截断文本"""
        if not text:
            return text
        
        # 估算当前token数
        current_tokens = SmartQuickReplyGenerator._estimate_tokens(text)
        
        if current_tokens <= max_tokens:
            return text
        
        # 需要截断：按比例计算应保留的字符数
        ratio = max_tokens / current_tokens
        target_length = int(len(text) * ratio * 0.9)  # 留10%安全余量
        
        if target_length < 100:
            # 至少保留100字符
            target_length = min(100, len(text))
        
        # 截断文本，尝试在句子边界截断
        truncated = text[:target_length]
        
        # 尝试在最后的句号、问号或感叹号处截断
        for delimiter in ['。', '！', '？', '\n\n', '\n']:
            last_pos = truncated.rfind(delimiter)
            if last_pos > target_length * 0.7:  # 至少保留70%
                return truncated[:last_pos + 1] + "..."
        
        # 如果找不到合适的分隔符，直接截断
        return truncated + "..."
    
    @staticmethod
    def _calculate_similarity(text1: str, text2: str) -> float:
        """计算文本相似度"""
        # 简单的基于字符重叠的相似度计算
        words1 = set(text1)
        words2 = set(text2)
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union) if union else 0
    
    @staticmethod
    def _get_fallback_suggestions(count: int) -> List[QuickReplySuggestion]:
        """获取备用建议"""
        fallback_texts = [
            "能否详细说明一下？",
            "有具体的例子吗？",
            "还有其他相关问题吗？"
        ]
        
        suggestions = []
        for i, text in enumerate(fallback_texts[:count]):
            suggestion = QuickReplySuggestion(
                text=text,
                confidence=0.5,
                category='fallback',
                context_relevance=0.3
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def update_user_preferences(self, user_id: str, suggestion_text: str, was_clicked: bool):
        """更新用户偏好（当用户点击建议时调用）"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {
                'preferred_categories': [],
                'clicked_suggestions': [],
                'expertise_level': 'intermediate'
            }
        
        user_prefs = self.user_preferences[user_id]
        
        if was_clicked:
            user_prefs['clicked_suggestions'].append(suggestion_text)
            
            # 分析建议类别
            for category, config in self.suggestion_templates.items():
                if any(keyword in suggestion_text for keyword in config['keywords']):
                    if category not in user_prefs['preferred_categories']:
                        user_prefs['preferred_categories'].append(category)
        
        self.logger.debug(f"更新用户{user_id}偏好: {user_prefs}")
    
    def get_suggestion_statistics(self) -> Dict[str, Any]:
        """获取建议统计信息"""
        total_users = len(self.user_preferences)
        total_clicks = sum(len(prefs.get('clicked_suggestions', [])) 
                          for prefs in self.user_preferences.values())
        
        category_stats = {}
        for prefs in self.user_preferences.values():
            for category in prefs.get('preferred_categories', []):
                category_stats[category] = category_stats.get(category, 0) + 1
        
        return {
            'total_users': total_users,
            'total_clicks': total_clicks,
            'category_preferences': category_stats,
            'avg_clicks_per_user': total_clicks / total_users if total_users > 0 else 0
        }
