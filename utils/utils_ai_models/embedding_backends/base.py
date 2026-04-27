#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Embedding Backend 抽象基类
定义所有 embedding 后端必须实现的接口

 向量类型约定（工程稳定性要求）：
    逻辑类型：List[float] / List[List[float]]（Python 原生类型）
    物理约定：float32 语义（值在 float32 范围内，Python float 容器）
    
     架构决策（sqlite-vec 集成阶段）：
        - Embedding 层职责：返回语义向量（List[float]）
        - VectorStore 层职责：处理物理存储格式（float32 buffer 转换）
        - 转换逻辑应放在 VectorStore Adapter 层（如 utils/vectorstore/sqlite_vec/serializer.py）
        - 不在 Embedding 层实现 prepare_for_vector_store()，保持职责分离
"""
from abc import ABC, abstractmethod
from typing import List


class EmbeddingBackend(ABC):
    """
    Embedding 后端抽象接口
    
     类型约定：
        - embed_documents() 返回 List[List[float]]（逻辑类型）
        - embed_query() 返回 List[float]（逻辑类型）
        - 物理约定：所有 float 值在 float32 范围内
        -  架构：float32 buffer 转换应在 VectorStore 层实现，不在本层
    """
    
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        编码文档列表为向量
        
         空输入语义：encode_documents([]) → []（返回空列表）
        
        Args:
            texts: 文本列表（允许空列表）
            
        Returns:
            向量列表，每个向量是 List[float]
            
         类型约定：
            - 逻辑类型：List[List[float]]
            - 物理约定：float32 语义（值在 float32 范围内）
            -  架构：float32 buffer 转换应在 VectorStore 层实现
        """
        pass
    
    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """
        编码查询文本为向量
        
         空输入语义：encode_query("") → 抛出 ValueError（不允许空字符串）
        
        Args:
            text: 单个文本（不允许空字符串）
            
        Returns:
            向量，List[float]
            
        Raises:
            ValueError: 如果输入为空字符串
            
         类型约定：
            - 逻辑类型：List[float]
            - 物理约定：float32 语义（值在 float32 范围内）
            -  架构：float32 buffer 转换应在 VectorStore 层实现
        """
        pass
    
    @abstractmethod
    def dimension(self) -> int:
        """
        返回 embedding 维度
        
        Returns:
            embedding 维度（整数）
        """
        pass
    
    @abstractmethod
    def model_name(self) -> str:
        """
        返回模型名称
        
        Returns:
            模型名称字符串
        """
        pass

