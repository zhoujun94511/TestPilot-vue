"""
文档处理包 (utils_document_processing)
提供文档预处理、智能文档分块、内容相似度、文档解析等功能
"""

from .document_preprocessor import (
    DocumentPreprocessor
)

from .smart_document_chunking import (
    SmartDocumentChunker,
    ChunkingStrategy,
    ContentType,
    ChunkMetadata,
    DocumentChunk,
    ChunkingConfig,
    get_smart_document_chunker,
    create_chunking_config
)

from .content_similarity import (
    ContentSimilarityDetector,
    create_content_detector
)

from .parser import (
    file_loader
)

__all__ = [
    # document_preprocessor
    'DocumentPreprocessor',
    
    # smart_document_chunking
    'SmartDocumentChunker',
    'ChunkingStrategy',
    'ContentType',
    'ChunkMetadata',
    'DocumentChunk',
    'ChunkingConfig',
    'get_smart_document_chunker',
    'create_chunking_config',
    
    # content_similarity
    'ContentSimilarityDetector',
    'create_content_detector',
    
    # parser
    'file_loader'
]
