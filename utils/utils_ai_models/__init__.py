"""
AI模型包 (utils_ai_models)
提供向量嵌入、嵌入管理器、嵌入监控、LLM获取等功能
"""

from .embeddings import (
    get_embeddings,
    clear_vector_db,
    create_vector_db,
    create_vector_db_from_texts,
    create_vector_db_from_docs
)

from .embedding_manager import (
    EmbeddingManager,
    EmbeddingCache,
    get_embedding_manager,
    get_embedding_cache,
    encode_texts
)

from .embedding_backends import (
    EmbeddingBackend,
    FastEmbedBackend
)

from .embedding_monitor import (
    EmbeddingMonitor,
    get_embedding_monitor
)

from .get_llm import get_llm, get_llm_instance

__all__ = [
    # embeddings
    'get_embeddings',
    'clear_vector_db',
    'create_vector_db',
    'create_vector_db_from_texts',
    'create_vector_db_from_docs',
    
    # embedding_manager
    'EmbeddingManager',
    'EmbeddingCache',
    'get_embedding_manager',
    'get_embedding_cache',
    'encode_texts',
    
    # embedding_backends
    'EmbeddingBackend',
    'FastEmbedBackend',
    
    # embedding_monitor
    'EmbeddingMonitor',
    'get_embedding_monitor',
    
    # get_llm
    'get_llm',
    'get_llm_instance'
]


