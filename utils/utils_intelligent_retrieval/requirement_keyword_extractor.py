#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
需求关键词提取器
从需求文本中智能提取核心关键词和实体，不依赖配置文件
"""
import re
from typing import List, Set, Dict, Any
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)

# 尝试导入 jieba，如果不可用则使用简单分词
try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    jieba = None  # 在 except 块中定义
    JIEBA_AVAILABLE = False
    logger.warning("jieba 未安装，将使用简单分词模式")


class RequirementKeywordExtractor:
    """需求关键词提取器
    
    与 rag_keyword_config.py 配合使用：
    - rag_keyword_config: 提供配置化的关键词（从 filter_keywords.json）
    - requirement_keyword_extractor: 直接从需求文本提取关键词（补充配置）
    """
    
    # 默认中文停用词（作为后备，如果配置加载失败时使用）
    _DEFAULT_STOP_WORDS = {
        '的', '了', '和', '是', '就', '都', '而', '及', '与', '或', '在', '有', '为', '被', '让', 
        '请', '生成', '关于', '测试', '用例', '一个', '这个', '那个', '怎么', '如何', '什么',
        '哪些', '可以', '应该', '需要', '要求', '功能', '系统', '应用', '软件'
    }
    
    # 默认技术术语（作为后备，如果配置加载失败时使用）
    _DEFAULT_TECH_TERMS = {
        'ai', '人工智能', '机器学习', '深度学习', '神经网络',
        '清洗', '规则', '算法', '模型', '数据', '处理',
        'api', '接口', '服务', '数据库', '缓存',
        '测试', '用例', '验证', '检查', '验证'
    }
    
    def __init__(self, keyword_config=None):
        """
        初始化关键词提取器
        
        Args:
            keyword_config: RAGKeywordConfig 实例（可选），用于加载配置的关键词
        """
        self.keyword_config = keyword_config
        
        # 初始化默认值（从配置加载失败时的后备值）
        self.CHINESE_STOP_WORDS = set(self._DEFAULT_STOP_WORDS)
        self.TECH_TERMS = set(self._DEFAULT_TECH_TERMS)
        self.BUSINESS_WORDS = set()  # 业务词汇（不过滤，但降低权重）
        self.min_keyword_length = 2
        self.max_keywords = 10
        self.enable_tech_term_bonus = True
        self.tech_term_bonus_score = 0.5
        
        if keyword_config:
            # 从配置中加载停用词、技术术语和设置
            self._load_stop_words_from_config()
            self._load_tech_terms_from_config()
            self._load_extraction_settings_from_config()
    
    def _load_stop_words_from_config(self):
        """从配置中加载停用词"""
        try:
            if self.keyword_config:
                stop_words_config = self.keyword_config.get_stop_words()
                
                # 合并 true_stop_words 和 query_verbs
                true_stop_words = stop_words_config.get('true_stop_words', [])
                query_verbs = stop_words_config.get('query_verbs', [])
                self.CHINESE_STOP_WORDS = set(true_stop_words + query_verbs)
                
                # 获取业务词汇（不过滤）
                business_words = stop_words_config.get('business_words', [])
                self.BUSINESS_WORDS = set(business_words)

        except Exception as e:
            logger.warning(f"从配置加载停用词失败，使用默认值: {e}")
            self.CHINESE_STOP_WORDS = set(self._DEFAULT_STOP_WORDS)
            self.BUSINESS_WORDS = set()
    
    def _load_tech_terms_from_config(self):
        """从配置中加载技术术语"""
        try:
            if self.keyword_config:
                # 获取技术术语配置
                tech_terms_config = self.keyword_config.get_keyword_extraction_tech_terms()
                
                # 清空当前技术术语（从配置重新加载）
                self.TECH_TERMS = set()
                
                # 从 technical_keywords 继承（如果启用）
                if tech_terms_config.get('inherit_from_technical_keywords', True):
                    technical_keywords = self.keyword_config.get_technical_keywords()
                    if 'items' in technical_keywords:
                        for item in technical_keywords['items']:
                            if 'keywords' in item:
                                self.TECH_TERMS.update(item['keywords'])
                
                # 添加额外的技术术语
                additional_terms = tech_terms_config.get('additional_terms', [])
                self.TECH_TERMS.update(additional_terms)

        except Exception as e:
            logger.warning(f"从配置加载技术术语失败，使用默认值: {e}")
            self.TECH_TERMS = set(self._DEFAULT_TECH_TERMS)
    
    def _load_extraction_settings_from_config(self):
        """从配置中加载提取设置"""
        try:
            if self.keyword_config:
                settings = self.keyword_config.get_extraction_settings()
                self.min_keyword_length = settings.get('min_keyword_length', 2)
                self.max_keywords = settings.get('max_keywords', 10)
                self.enable_tech_term_bonus = settings.get('enable_tech_term_bonus', True)
                self.tech_term_bonus_score = settings.get('tech_term_bonus_score', 0.5)

        except Exception as e:
            logger.warning(f"从配置加载提取设置失败，使用默认值: {e}")
    
    def extract_keywords(self, requirement_text: str, 
                        config_keywords: List[str] = None) -> Set[str]:
        """
        从需求文本中提取关键词（结合配置和直接提取）
        
        Args:
            requirement_text: 需求文本
            config_keywords: 配置文件中的关键词（从 rag_keyword_config 获取）
            
        Returns:
            提取的关键词集合
        """
        if not requirement_text:
            return set()
        
        keywords = set()
        
        # 1. 从配置关键词中匹配（与 rag_keyword_config 配合）
        if config_keywords:
            requirement_lower = requirement_text.lower()
            for keyword in config_keywords:
                if keyword.lower() in requirement_lower:
                    keywords.add(keyword.lower())
        
        # 2. 直接提取需求文本中的核心概念（新增功能）
        extracted_keywords = self._extract_from_text(requirement_text)
        keywords.update(extracted_keywords)
        
        # 3. 提取技术术语和实体（可能包含配置中的技术术语）
        tech_keywords = self._extract_tech_terms(requirement_text)
        keywords.update(tech_keywords)
        
        # 4. 提取名词短语（组合词）
        noun_phrases = self._extract_noun_phrases(requirement_text)
        keywords.update(noun_phrases)
        
        # 过滤停用词和过短的关键词（业务词汇不过滤，保留）
        keywords = {kw for kw in keywords 
                   if len(kw) >= self.min_keyword_length 
                   and kw not in self.CHINESE_STOP_WORDS}  # 业务词汇保留，但会在排序时降低权重
        
        # 限制数量，保留最重要的
        if len(keywords) > self.max_keywords:
            keywords = self._rank_keywords(keywords, requirement_text)
        
        logger.debug(f"提取的关键词: {keywords}")
        return keywords
    
    def _extract_from_text(self, text: str) -> Set[str]:
        """从文本中提取关键词（基于词频和重要性）"""
        keywords = set()
        
        # 提取英文单词
        english_words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
        keywords.update(english_words)
        
        # 提取中文词汇
        if JIEBA_AVAILABLE:
            # 使用 jieba 分词，避免语义截断
            try:
                # 精确模式分词
                words = jieba.cut(text, cut_all=False)
                chinese_words = []
                for word in words:
                    # 只保留中文字符（2-6个字），过滤单字和过长词
                    if re.match(r'^[\u4e00-\u9fa5]{2,6}$', word):
                        chinese_words.append(word)
                keywords.update(chinese_words)
            except Exception as e:
                logger.warning(f"jieba 分词失败，回退到简单模式: {e}")
                # 回退到简单模式
                chinese_words = self._simple_chinese_extract(text)
                keywords.update(chinese_words)
        else:
            # 简单分词模式（改进版）
            chinese_words = self._simple_chinese_extract(text)
            keywords.update(chinese_words)
        
        # 过滤停用词和过短的关键词
        keywords = {kw for kw in keywords 
                   if len(kw) >= self.min_keyword_length 
                   and kw not in self.CHINESE_STOP_WORDS}
        
        return keywords
    
    def _simple_chinese_extract(self, text: str) -> List[str]:
        """简单的中文分词（当 jieba 不可用时使用）"""
        # 先匹配已知的技术术语和短语（避免截断）
        found_terms = []
        for term in self.TECH_TERMS:
            if term in text.lower():
                found_terms.append(term)
        
        # 使用改进的正则：非贪婪匹配，优先匹配完整词汇
        # 匹配2-6个连续汉字，但避免在已知术语中截断
        chinese_words = []
        # 先移除已匹配的术语，避免重复匹配
        text_remaining = text
        for term in found_terms:
            if term in text_remaining.lower():
                text_remaining = text_remaining.replace(term, ' ', 1)
        
        # 在剩余文本中匹配
        matches = re.finditer(r'[\u4e00-\u9fa5]{2,6}', text_remaining)
        for match in matches:
            word = match.group()
            # 过滤停用词
            if word not in self.CHINESE_STOP_WORDS:
                chinese_words.append(word)
        
        # 添加已找到的技术术语
        chinese_words.extend(found_terms)
        
        return chinese_words
    
    def _extract_tech_terms(self, text: str) -> Set[str]:
        """提取技术术语"""
        text_lower = text.lower()
        found_terms = set()
        
        for term in self.TECH_TERMS:
            if term in text_lower:
                found_terms.add(term)
        
        return found_terms
    
    def _extract_noun_phrases(self, text: str) -> Set[str]:
        """提取名词短语（如"AI清洗规则"、"数据库查询"）"""
        phrases = set()
        
        # 1. 匹配英文+中文组合（如 "AI清洗规则"）
        pattern1 = re.findall(r'([A-Z][a-z]+|[A-Z]{2,})\s*([\u4e00-\u9fa5]{2,8})', text)
        for eng, chn in pattern1:
            phrase = f"{eng.lower()} {chn.lower()}".strip()
            if not any(phrase.startswith(stop) for stop in self.CHINESE_STOP_WORDS):
                phrases.add(phrase)
        
        # 2. 提取中文名词短语（使用更智能的方法）
        if JIEBA_AVAILABLE:
            try:
                # 使用 jieba 提取名词短语
                words = jieba.cut(text, cut_all=False)
                word_list = list(words)
                # 识别连续的中文词汇组合（4-10个字）
                for i in range(len(word_list)):
                    phrase = ''
                    for j in range(i, min(i + 5, len(word_list))):  # 最多5个词组合
                        word = word_list[j]
                        if re.match(r'^[\u4e00-\u9fa5]+$', word):
                            phrase += word
                            if 4 <= len(phrase) <= 10:  # 4-10个字的短语
                                if not any(phrase.startswith(stop) for stop in self.CHINESE_STOP_WORDS):
                                    phrases.add(phrase.lower())
            except (AttributeError, TypeError, ValueError) as e:
                # 回退到简单模式
                logger.debug(f"jieba 分词失败，回退到简单模式: {e}")
                chinese_phrases = re.findall(r'[\u4e00-\u9fa5]{4,10}', text)
                for phrase in chinese_phrases:
                    if not any(phrase.startswith(stop) for stop in self.CHINESE_STOP_WORDS):
                        phrases.add(phrase.lower())
        else:
            # 简单模式：匹配4-10个连续汉字
            chinese_phrases = re.findall(r'[\u4e00-\u9fa5]{4,10}', text)
            for phrase in chinese_phrases:
                if not any(phrase.startswith(stop) for stop in self.CHINESE_STOP_WORDS):
                    phrases.add(phrase.lower())
        
        return phrases
    
    def _rank_keywords(self, keywords: Set[str], context: str) -> Set[str]:
        """对关键词进行排序，返回最重要的关键词"""
        # 简单的排序策略：基于词频和长度
        context_lower = context.lower()
        
        keyword_scores = {}
        for keyword in keywords:
            # 计算得分：词频 + 长度权重
            freq = context_lower.count(keyword)
            length_weight = len(keyword) * 0.1
            
            # 技术术语加分（如果启用）
            if self.enable_tech_term_bonus and keyword in self.TECH_TERMS:
                tech_bonus = self.tech_term_bonus_score
            else:
                tech_bonus = 0
            
            # 业务词汇降低权重（如果不在技术术语中）
            if keyword in self.BUSINESS_WORDS and keyword not in self.TECH_TERMS:
                tech_bonus = -0.2  # 轻微降低权重
            
            score = freq + length_weight + tech_bonus
            keyword_scores[keyword] = score
        
        # 按得分排序，返回前N个
        sorted_keywords = sorted(keyword_scores.items(), 
                               key=lambda x: x[1], 
                               reverse=True)
        
        return {kw for kw, score in sorted_keywords[:self.max_keywords]}
    
    def extract_core_concepts(self, requirement_text: str) -> Dict[str, Any]:
        """
        提取需求的核心概念
        
        Returns:
            {
                'keywords': Set[str], # 关键词集合
                'entities': Set[str], # 实体集合
                'phrases': Set[str], # 短语集合
                'tech_terms': Set[str] # 技术术语
            }
        """
        if not requirement_text:
            return {
                'keywords': set(),
                'entities': set(),
                'phrases': set(),
                'tech_terms': set()
            }
        
        keywords = self._extract_from_text(requirement_text)
        tech_terms = self._extract_tech_terms(requirement_text)
        phrases = self._extract_noun_phrases(requirement_text)
        
        # 实体识别（改进版：识别完整短语，避免截断）
        entities = set()
        
        # 1. 匹配英文实体（如：AI, API）
        english_entities = re.findall(r'\b[A-Z][a-z]+|\b[A-Z]{2,}\b', requirement_text)
        entities.update(m.lower() for m in english_entities if len(m) >= 2)
        
        # 2. 匹配中文实体（使用更智能的模式，避免截断）
        if JIEBA_AVAILABLE:
            try:
                # 使用 jieba 提取名词短语
                words = jieba.cut(requirement_text, cut_all=False)
                word_list = list(words)
                # 识别连续的中文词汇组合（2-8个字）
                for i in range(len(word_list)):
                    phrase = ''
                    for j in range(i, min(i + 4, len(word_list))):  # 最多4个词组合
                        word = word_list[j]
                        if re.match(r'^[\u4e00-\u9fa5]+$', word):
                            phrase += word
                            if 4 <= len(phrase) <= 8:  # 4-8个字的短语
                                entities.add(phrase.lower())
            except (AttributeError, TypeError, ValueError) as e:
                # 回退到简单模式
                logger.debug(f"jieba 实体提取失败，回退到简单模式: {e}")
                chinese_entities = re.findall(r'[\u4e00-\u9fa5]{4,8}', requirement_text)
                entities.update(m.lower() for m in chinese_entities)
        else:
            # 简单模式：匹配4-8个连续汉字
            chinese_entities = re.findall(r'[\u4e00-\u9fa5]{4,8}', requirement_text)
            entities.update(m.lower() for m in chinese_entities)
        
        # 3. 过滤停用词开头的实体
        entities = {e for e in entities 
                   if not any(e.startswith(stop) for stop in self.CHINESE_STOP_WORDS)}
        
        return {
            'keywords': keywords,
            'entities': entities,
            'phrases': phrases,
            'tech_terms': tech_terms
        }


# 全局实例
_extractor_instance = None


def get_requirement_keyword_extractor(keyword_config=None) -> RequirementKeywordExtractor:
    """
    获取全局关键词提取器实例（与 rag_keyword_config 整合）
    
    Args:
        keyword_config: RAGKeywordConfig 实例（可选），如果提供则整合配置
        
    Returns:
        RequirementKeywordExtractor 实例
    """
    global _extractor_instance
    if _extractor_instance is None:
        # 如果没有提供配置，尝试从全局获取
        if keyword_config is None:
            try:
                from utils.utils_intelligent_retrieval.rag_keyword_config import get_rag_keyword_config
                keyword_config = get_rag_keyword_config()
            except Exception as e:
                logger.debug(f"无法获取 rag_keyword_config，使用独立模式: {e}")
                keyword_config = None
        _extractor_instance = RequirementKeywordExtractor(keyword_config)
    return _extractor_instance

