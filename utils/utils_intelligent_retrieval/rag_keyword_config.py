#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
关键词配置管理器
用于管理内容过滤的关键词配置
"""
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


class RAGKeywordConfig:
    """RAG关键词配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化关键词配置管理器
        
        Args:
            config_path: 配置文件路径，默认为 config/filter_keywords.json
        """
        if config_path is None:
            # 默认配置文件路径
            base_dir = Path(__file__).parent.parent.parent
            config_path = base_dir / "config" / "filter_keywords.json"
        
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 验证配置结构
            if not isinstance(config, dict):
                logger.warning("配置文件格式不正确，使用默认配置")
                return self._get_default_config()
            
            # 验证必要的配置项（支持新旧版本）
            required_keys_v1 = ['keyword_categories', 'exclude_keywords', 'scoring_weights']
            required_keys_v2 = ['platform_keywords', 'application_keywords', 'functional_keywords', 'exclude_keywords', 'scoring_weights']
            
            # 检查是v1还是v2格式
            is_v1_format = all(key in config for key in required_keys_v1)
            is_v2_format = all(key in config for key in required_keys_v2)
            
            if not is_v1_format and not is_v2_format:
                logger.warning("配置文件格式不兼容，使用默认配置")
                return self._get_default_config()

            return config
            
        except FileNotFoundError:
            logger.warning(f"RAG关键词配置文件不存在: {self.config_path}")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"解析RAG关键词配置文件失败: {e}")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"加载RAG关键词配置文件出错: {e}")
            return self._get_default_config()
    
    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "keyword_categories": {
                "game_keywords": {
                    "keywords": ["游戏", "测试", "功能"]
                },
                "tech_keywords": {
                    "keywords": ["测试", "功能", "性能"]
                },
                "business_keywords": {
                    "keywords": ["用户", "登录", "支付"]
                }
            },
            "exclude_keywords": {
                "keywords": ["针织", "编织", "毛线"]
            },
            "scoring_weights": {
                "weights": {
                    "keyword_match": 0.6,
                    "content_length": 0.2,
                    "domain_relevance": 0.2
                },
                "thresholds": {
                    "min_relevance_score": 0.7,
                    "content_length_threshold": 100
                }
            }
        }
    
    def get_keywords_by_category(self, category: str) -> List[str]:
        """
        获取指定类别的关键词
        
        Args:
            category: 关键词类别名称
            
        Returns:
            关键词列表
        """
        categories = self.config.get("keyword_categories", {})
        category_config = categories.get(category, {})
        return category_config.get("keywords", [])
    
    def get_all_keywords(self) -> List[str]:
        """获取所有关键词"""
        all_keywords = []
        categories = self.config.get("keyword_categories", {})
        
        for category_config in categories.values():
            keywords = category_config.get("keywords", [])
            all_keywords.extend(keywords)
        
        return list(set(all_keywords))  # 去重
    
    def get_exclude_keywords(self) -> List[str]:
        """获取排除关键词列表"""
        exclude_config = self.config.get('exclude_keywords', {})
        
        # 支持v2格式的分类排除关键词
        if 'categories' in exclude_config:
            all_exclude_keywords = []
            for category_name, category_config in exclude_config['categories'].items():
                keywords = category_config.get('keywords', [])
                all_exclude_keywords.extend(keywords)
            return all_exclude_keywords
        
        # 支持v1格式的直接关键词列表
        return exclude_config.get('keywords', [])
    
    def get_scoring_weights(self) -> Dict[str, float]:
        """获取评分权重配置"""
        scoring_config = self.config.get("scoring_weights", {})
        return scoring_config.get("weights", {
            "keyword_match": 0.6,
            "content_length": 0.2,
            "domain_relevance": 0.2
        })
    
    def get_thresholds(self) -> Dict[str, Any]:
        """获取阈值配置"""
        scoring_config = self.config.get("scoring_weights", {})
        return scoring_config.get("thresholds", {
            "min_relevance_score": 0.7,
            "content_length_threshold": 100
        })
    
    def get_domain_features(self, domain: str) -> List[str]:
        """
        获取指定领域的特征关键词
        
        Args:
            domain: 领域名称 (game_features, test_features, business_features)
            
        Returns:
            特征关键词列表
        """
        domain_config = self.config.get("domain_features", {})
        return domain_config.get(domain, [])
    
    def reload_config(self):
        """重新加载配置文件"""
        self.config = self._load_config()
    
    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息"""
        return {
            "config_path": str(self.config_path),
            "categories_count": len(self.config.get("keyword_categories", {})),
            "total_keywords": len(self.get_all_keywords()),
            "exclude_keywords_count": len(self.get_exclude_keywords()),
            "weights": self.get_scoring_weights(),
            "thresholds": self.get_thresholds()
        }
    
    def get_platform_keywords(self) -> Dict[str, Any]:
        """获取平台关键词配置"""
        return self.config.get('platform_keywords', {})
    
    def get_application_keywords(self) -> Dict[str, Any]:
        """获取应用类型关键词配置"""
        return self.config.get('application_keywords', {})
    
    def get_functional_keywords(self) -> Dict[str, Any]:
        """获取功能模块关键词配置"""
        return self.config.get('functional_keywords', {})
    
    def get_technical_keywords(self) -> Dict[str, Any]:
        """获取技术关键词配置"""
        return self.config.get('technical_keywords', {})
    
    def get_advanced_filters(self) -> Dict[str, Any]:
        """获取高级过滤配置"""
        return self.config.get('advanced_filters', {})
    
    def get_integration_config(self) -> Dict[str, Any]:
        """获取集成配置"""
        return self.config.get('integration_config', {})
    
    def get_risk_multipliers(self) -> Dict[str, float]:
        """获取风险权重倍数"""
        scoring_weights = self.config.get('scoring_weights', {})
        return scoring_weights.get('risk_multipliers', {
            'low': 1.0,
            'medium': 1.2,
            'high': 1.5,
            'critical': 2.0
        })
    
    def get_quality_indicators(self) -> Dict[str, Any]:
        """获取内容质量指标配置"""
        advanced_filters = self.get_advanced_filters()
        return advanced_filters.get('quality_indicators', {})
    
    def is_context_awareness_enabled(self) -> bool:
        """检查是否启用上下文感知"""
        advanced_filters = self.get_advanced_filters()
        context_awareness = advanced_filters.get('context_awareness', {})
        return context_awareness.get('enabled', False)
    
    def is_dynamic_weighting_enabled(self) -> bool:
        """检查是否启用动态权重"""
        advanced_filters = self.get_advanced_filters()
        dynamic_weighting = advanced_filters.get('dynamic_weighting', {})
        return dynamic_weighting.get('enabled', False)
    
    def get_stop_words(self) -> Dict[str, Any]:
        """
        获取停用词配置（用于关键词提取）
        
        Returns:
            停用词配置字典，包含：
            - true_stop_words: 真正的停用词列表
            - query_verbs: 查询指令词列表
            - business_words: 业务词汇配置
        """
        extraction_config = self.config.get('keyword_extraction', {})
        stop_words_config = extraction_config.get('stop_words', {})
        
        return {
            'true_stop_words': stop_words_config.get('true_stop_words', []),
            'query_verbs': stop_words_config.get('query_verbs', []),
            'business_words': stop_words_config.get('business_words', {}).get('keywords', [])
        }
    
    def get_keyword_extraction_tech_terms(self) -> Dict[str, Any]:
        """
        获取关键词提取的技术术语配置
        
        Returns:
            技术术语配置字典，包含：
            - inherit_from_technical_keywords: 是否从 technical_keywords 继承
            - additional_terms: 额外的技术术语列表
        """
        extraction_config = self.config.get('keyword_extraction', {})
        tech_terms_config = extraction_config.get('tech_terms', {})
        
        return {
            'inherit_from_technical_keywords': tech_terms_config.get('inherit_from_technical_keywords', True),
            'additional_terms': tech_terms_config.get('additional_terms', [])
        }
    
    def get_extraction_settings(self) -> Dict[str, Any]:
        """
        获取关键词提取设置
        
        Returns:
            提取设置字典，包含：
            - min_keyword_length: 最小关键词长度
            - max_keywords: 最多提取的关键词数量
            - enable_tech_term_bonus: 是否启用技术术语加分
            - tech_term_bonus_score: 技术术语加分值
        """
        extraction_config = self.config.get('keyword_extraction', {})
        settings = extraction_config.get('extraction_settings', {})
        
        return {
            'min_keyword_length': settings.get('min_keyword_length', 2),
            'max_keywords': settings.get('max_keywords', 10),
            'enable_tech_term_bonus': settings.get('enable_tech_term_bonus', True),
            'tech_term_bonus_score': settings.get('tech_term_bonus_score', 0.5)
        }
    
    def get_all_stop_words(self) -> List[str]:
        """
        获取所有停用词（合并 true_stop_words 和 query_verbs）
        
        Returns:
            停用词列表
        """
        stop_words_config = self.get_stop_words()
        true_stop_words = stop_words_config.get('true_stop_words', [])
        query_verbs = stop_words_config.get('query_verbs', [])
        return list(set(true_stop_words + query_verbs))
    
    def get_all_tech_terms_for_extraction(self) -> List[str]:
        """
        获取所有技术术语（用于关键词提取）
        
        Returns:
            技术术语列表（包含从 technical_keywords 继承的 + 额外的）
        """
        tech_terms_config = self.get_keyword_extraction_tech_terms()
        all_terms = set()
        
        # 从 technical_keywords 继承
        if tech_terms_config.get('inherit_from_technical_keywords', True):
            technical_keywords = self.get_technical_keywords()
            if 'items' in technical_keywords:
                for item in technical_keywords['items']:
                    if 'keywords' in item:
                        all_terms.update(item['keywords'])
        
        # 添加额外的技术术语
        additional_terms = tech_terms_config.get('additional_terms', [])
        all_terms.update(additional_terms)
        
        return list(all_terms)


# 全局配置实例
_rag_keyword_config: Optional[RAGKeywordConfig] = None


def get_rag_keyword_config() -> RAGKeywordConfig:
    """获取RAG关键词配置实例（单例模式）"""
    global _rag_keyword_config
    if _rag_keyword_config is None:
        _rag_keyword_config = RAGKeywordConfig()
    return _rag_keyword_config


def reload_rag_keyword_config():
    """重新加载RAG关键词配置"""
    global _rag_keyword_config
    if _rag_keyword_config is not None:
        _rag_keyword_config.reload_config()
