"""
智能检索包 (utils_intelligent_retrieval)
提供智能检索策略、RAG关键词配置等功能
"""

from .smart_retrieval_strategy import (
    SmartRetrievalStrategy,
    RetrievalStrategy,
    RetrievalResult,
    RetrievalConfig,
    get_smart_retrieval_strategy,
    create_retrieval_config
)

from .rag_keyword_config import (
    RAGKeywordConfig,
    get_rag_keyword_config
)

__all__ = [
    # smart_retrieval_strategy
    'SmartRetrievalStrategy',
    'RetrievalStrategy',
    'RetrievalResult',
    'RetrievalConfig',
    'get_smart_retrieval_strategy',
    'create_retrieval_config',
    
    # rag_keyword_config
    'RAGKeywordConfig',
    'get_rag_keyword_config'
]


