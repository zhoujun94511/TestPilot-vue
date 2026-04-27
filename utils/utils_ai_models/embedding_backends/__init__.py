"""
Embedding Backends
提供轻量级 embedding 后端实现，不依赖 PyTorch
"""
from .base import EmbeddingBackend
from .fastembed_backend import FastEmbedBackend

__all__ = [
    'EmbeddingBackend',
    'FastEmbedBackend',
]








