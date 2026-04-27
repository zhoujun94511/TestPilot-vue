#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
智能配置管理器
统一管理智能检索和文档分块的配置
"""
import json
from typing import Dict, Any, Optional
from pathlib import Path
from utils.utils_core.logger import get_logger
# 使用延迟导入避免循环导入
from config.settings import settings

logger = get_logger(__name__)


class SmartConfigManager:
    """智能配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化智能配置管理器
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认路径
        """
        if config_file is None:
            base_dir = Path(__file__).parent.parent
            config_file = base_dir / "config" / "smart_config.json"
        
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件 - 优先从 settings.py 读取，JSON 文件作为备用"""
        try:
            # 优先从 settings.py 读取配置
            config = self._load_from_settings()
            logger.info("成功从 settings.py 加载智能配置")
            return config
        except Exception as e:
            logger.warning(f"从 settings.py 加载配置失败: {e}，尝试从 JSON 文件加载")
            try:
                if self.config_file.exists():
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    logger.info(f"成功从 JSON 文件加载智能配置: {self.config_file}")
                    return config
                else:
                    logger.warning(f"智能配置文件不存在: {self.config_file}，使用默认配置")
                    return self._get_default_config()
            except Exception as e2:
                logger.error(f"加载智能配置文件失败: {e2}，使用默认配置")
                return self._get_default_config()
    
    @staticmethod
    def _load_from_settings() -> Dict[str, Any]:
        """从 settings.py 加载配置"""
        return {
            "retrieval": {
                "enabled": True,
                "strategy": getattr(settings, 'RAG_STRATEGY', 'auto'),
                "top_k": getattr(settings, 'RAG_TOP_K', 5),
                "score_threshold": getattr(settings, 'RAG_SCORE_THRESHOLD', 0.7),
                "enable_reranking": getattr(settings, 'RAG_ENABLE_RERANKING', True),
                "enable_query_expansion": getattr(settings, 'RAG_ENABLE_QUERY_EXPANSION', True),
                "enable_context_awareness": getattr(settings, 'RAG_ENABLE_CONTEXT_AWARENESS', True),
                "max_context_length": getattr(settings, 'RAG_MAX_CONTEXT_LENGTH', 2000),
                "similarity_threshold": getattr(settings, 'RAG_SIMILARITY_THRESHOLD', 0.8),
                "strategy_weights": {
                    "semantic": 0.6,
                    "keyword": 0.3,
                    "hybrid": 0.8,
                    "context_aware": 0.9
                }
            },
            "chunking": {
                "enabled": True,
                "strategy": getattr(settings, 'CHUNK_STRATEGY', 'adaptive'),
                "base_chunk_size": getattr(settings, 'CHUNK_BASE_SIZE', 1000),
                "min_chunk_size": getattr(settings, 'CHUNK_MIN_SIZE', 200),
                "max_chunk_size": getattr(settings, 'CHUNK_MAX_SIZE', 2000),
                "overlap_size": getattr(settings, 'CHUNK_OVERLAP_SIZE', 200),
                "enable_semantic_boundary": getattr(settings, 'CHUNK_ENABLE_SEMANTIC_BOUNDARY', True),
                "enable_content_type_detection": getattr(settings, 'CHUNK_ENABLE_CONTENT_TYPE_DETECTION', True),
                "enable_quality_assessment": getattr(settings, 'CHUNK_ENABLE_QUALITY_ASSESSMENT', True),
                "quality_threshold": getattr(settings, 'CHUNK_QUALITY_THRESHOLD', 0.7)
            },
            "performance": {
                "enable_monitoring": True,
                "enable_caching": True,
                "cache_size": getattr(settings, 'EMBEDDING_CACHE_SIZE', 1000),
                "enable_parallel_processing": True,
                "max_workers": getattr(settings, 'MAX_WORKERS', 3)
            },
            "integration": {
                "knowledge_service": {
                    "use_smart_retrieval": True,
                    "use_smart_chunking": True,
                    "fallback_to_traditional": True
                },
                "chat_service": {
                    "use_smart_retrieval": True,
                    "enable_context_awareness": True
                },
                "case_service": {
                    "use_smart_retrieval": True,
                    "enable_reranking": True
                }
            }
        }
    
    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "retrieval": {
                "enabled": True,
                "strategy": "auto",  # auto, semantic, keyword, hybrid, context_aware
                "top_k": 5,
                "score_threshold": 0.7,
                "enable_reranking": True,
                "enable_query_expansion": True,
                "enable_context_awareness": True,
                "max_context_length": 2000,
                "similarity_threshold": 0.8,
                "strategy_weights": {
                    "semantic": 0.6,
                    "keyword": 0.3,
                    "hybrid": 0.8,
                    "context_aware": 0.9
                }
            },
            "chunking": {
                "enabled": True,
                "strategy": "adaptive",  # fixed_size, semantic, adaptive, hierarchical
                "base_chunk_size": 1000,
                "min_chunk_size": 200,
                "max_chunk_size": 2000,
                "overlap_size": 200,
                "enable_semantic_boundary": True,
                "enable_content_type_detection": True,
                "enable_quality_assessment": True,
                "quality_threshold": 0.7
            },
            "performance": {
                "enable_monitoring": True,
                "enable_caching": True,
                "cache_size": 1000,
                "enable_parallel_processing": True,
                "max_workers": 3
            },
            "integration": {
                "knowledge_service": {
                    "use_smart_retrieval": True,
                    "use_smart_chunking": True,
                    "fallback_to_traditional": True
                },
                "chat_service": {
                    "use_smart_retrieval": True,
                    "enable_context_awareness": True
                },
                "case_service": {
                    "use_smart_retrieval": True,
                    "enable_reranking": True
                }
            }
        }
    
    def get_retrieval_config(self):
        """获取检索配置"""
        # 延迟导入避免循环导入
        from utils.utils_intelligent_retrieval.smart_retrieval_strategy import RetrievalConfig
        
        retrieval_config = self.config.get("retrieval", {})
        
        return RetrievalConfig(
            top_k=retrieval_config.get("top_k", 5),
            score_threshold=retrieval_config.get("score_threshold", 0.7),
            enable_reranking=retrieval_config.get("enable_reranking", True),
            enable_query_expansion=retrieval_config.get("enable_query_expansion", True),
            enable_context_awareness=retrieval_config.get("enable_context_awareness", True),
            max_context_length=retrieval_config.get("max_context_length", 2000),
            similarity_threshold=retrieval_config.get("similarity_threshold", 0.8)
        )
    
    def get_chunking_config(self):
        """获取分块配置"""
        # 延迟导入避免循环导入
        from utils.utils_document_processing.smart_document_chunking import ChunkingConfig
        
        chunking_config = self.config.get("chunking", {})
        
        # 转换策略字符串为枚举
        from utils.utils_document_processing.smart_document_chunking import ChunkingStrategy
        
        strategy_str = chunking_config.get("strategy", "adaptive")
        strategy_map = {
            "fixed_size": ChunkingStrategy.FIXED_SIZE,
            "semantic": ChunkingStrategy.SEMANTIC,
            "adaptive": ChunkingStrategy.ADAPTIVE,
            "hierarchical": ChunkingStrategy.HIERARCHICAL
        }
        strategy = strategy_map.get(strategy_str, ChunkingStrategy.ADAPTIVE)
        
        return ChunkingConfig(
            strategy=strategy,
            base_chunk_size=chunking_config.get("base_chunk_size", 1000),
            min_chunk_size=chunking_config.get("min_chunk_size", 200),
            max_chunk_size=chunking_config.get("max_chunk_size", 2000),
            overlap_size=chunking_config.get("overlap_size", 200),
            enable_semantic_boundary=chunking_config.get("enable_semantic_boundary", True),
            enable_content_type_detection=chunking_config.get("enable_content_type_detection", True),
            enable_quality_assessment=chunking_config.get("enable_quality_assessment", True),
            quality_threshold=chunking_config.get("quality_threshold", 0.7)
        )
    
    def get_retrieval_strategy(self):
        """获取检索策略"""
        # 延迟导入避免循环导入
        from utils.utils_intelligent_retrieval.smart_retrieval_strategy import RetrievalStrategy
        
        retrieval_config = self.config.get("retrieval", {})
        strategy_str = retrieval_config.get("strategy", "auto")
        
        if strategy_str == "auto":
            return None  # 自动选择
        
        strategy_map = {
            "semantic": RetrievalStrategy.SEMANTIC,
            "keyword": RetrievalStrategy.KEYWORD,
            "hybrid": RetrievalStrategy.HYBRID,
            "context_aware": RetrievalStrategy.CONTEXT_AWARE
        }
        
        return strategy_map.get(strategy_str, RetrievalStrategy.HYBRID)
    
    def is_retrieval_enabled(self) -> bool:
        """检查是否启用智能检索"""
        return self.config.get("retrieval", {}).get("enabled", True)
    
    def is_chunking_enabled(self) -> bool:
        """检查是否启用智能分块"""
        return self.config.get("chunking", {}).get("enabled", True)
    
    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """获取特定服务的配置"""
        return self.config.get("integration", {}).get(service_name, {})
    
    def get_performance_config(self) -> Dict[str, Any]:
        """获取性能配置"""
        return self.config.get("performance", {})
    
    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        self.config.update(new_config)
        self._save_config()
    
    def update_retrieval_config(self, retrieval_config: Dict[str, Any]):
        """更新检索配置"""
        if "retrieval" not in self.config:
            self.config["retrieval"] = {}
        self.config["retrieval"].update(retrieval_config)
        self._save_config()
    
    def update_chunking_config(self, chunking_config: Dict[str, Any]):
        """更新分块配置"""
        if "chunking" not in self.config:
            self.config["chunking"] = {}
        self.config["chunking"].update(chunking_config)
        self._save_config()
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            # 确保配置目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置已保存到: {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def reset_to_default(self):
        """重置为默认配置"""
        self.config = self._get_default_config()
        self._save_config()
        logger.info("配置已重置为默认值")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        return {
            "retrieval_enabled": self.is_retrieval_enabled(),
            "chunking_enabled": self.is_chunking_enabled(),
            "retrieval_strategy": self.config.get("retrieval", {}).get("strategy", "auto"),
            "chunking_strategy": self.config.get("chunking", {}).get("strategy", "adaptive"),
            "performance_monitoring": self.config.get("performance", {}).get("enable_monitoring", True),
            "config_file": str(self.config_file)
        }
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置有效性"""
        errors = []
        warnings = []
        
        # 验证检索配置
        retrieval_config = self.config.get("retrieval", {})
        if retrieval_config.get("top_k", 0) <= 0:
            errors.append("检索top_k必须大于0")
        
        if not 0 <= retrieval_config.get("score_threshold", 0) <= 1:
            errors.append("检索score_threshold必须在0-1之间")
        
        # 验证分块配置
        chunking_config = self.config.get("chunking", {})
        if chunking_config.get("min_chunk_size", 0) >= chunking_config.get("max_chunk_size", 0):
            errors.append("分块min_chunk_size必须小于max_chunk_size")
        
        if chunking_config.get("overlap_size", 0) >= chunking_config.get("min_chunk_size", 0):
            warnings.append("分块overlap_size建议小于min_chunk_size")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


# 全局实例
_smart_config_manager: Optional[SmartConfigManager] = None


def get_smart_config_manager(config_file: Optional[str] = None) -> SmartConfigManager:
    """获取智能配置管理器实例（单例模式）"""
    global _smart_config_manager
    if _smart_config_manager is None:
        _smart_config_manager = SmartConfigManager(config_file)
    return _smart_config_manager


def create_smart_config_file():
    """创建默认的智能配置文件"""
    config_manager = SmartConfigManager()
    # 使用公共方法保存配置
    config_manager.update_config({})
    logger.info("已创建默认智能配置文件")
    return config_manager.config_file
