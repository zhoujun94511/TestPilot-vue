#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
FastEmbed Backend
使用 fastembed 库（ONNX / CPU），轻量级、无需 PyTorch

⚠️ 工程约定：
- embedding 维度必须与配置 EMBEDDING_DIM 严格一致
- 不允许自动选择模型（维度必须固定）
- 向量类型：List[float]（逻辑类型），float32 语义（物理约定）
"""
import os
import sys
from pathlib import Path
from typing import List, Optional
from utils.utils_core.logger import get_logger
from config.settings import settings
from .base import EmbeddingBackend

logger = get_logger(__name__)


class FastEmbedBackend(EmbeddingBackend):
    """
    FastEmbed 后端实现（ONNX / CPU）
    
    ⚠️ 重要约束：
    - 模型名称和维度必须通过配置明确指定
    - 维度一旦确定，不允许再变更（sqlite-vec 要求）
    - 若实际维度与配置不一致，启动时直接抛出异常
    """
    
    def __init__(self, model_name: Optional[str] = None, expected_dim: Optional[int] = None):
        """
        初始化 FastEmbed 后端
        
        Args:
            model_name: 模型名称，如果为 None 则从配置读取
            expected_dim: 期望的维度，如果为 None 则从配置读取
        
        Raises:
            ValueError: 如果实际维度与配置不一致
        """
        # 从配置读取模型名称和维度（不允许自动选择）
        self._model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self._expected_dim = expected_dim or settings.EMBEDDING_DIM
        self._model = None
        self._dimension = None
        
        # 记录缓存目录
        # 优先使用配置的目录，否则尝试从打包目录加载
        cache_dir = settings.FASTEMBED_CACHE_DIR
        if not cache_dir:
            # 检查是否是打包后的环境（PyInstaller）
            if getattr(sys, 'frozen', False):
                # 打包后的环境，使用 PyInstaller 的临时解压目录
                # sys._MEIPASS 是 PyInstaller 在运行时解压数据文件的临时目录
                if hasattr(sys, '_MEIPASS'):
                    # onefile 模式：数据文件在临时目录
                    base_path = Path(getattr(sys, '_MEIPASS'))
                    logger.info(f"检测到 PyInstaller onefile 模式")
                else:
                    # onedir 模式：数据文件在 exe 所在目录
                    base_path = Path(sys.executable).parent
                    logger.info(f"检测到 PyInstaller onedir 模式")
                
                bundled_cache = base_path / 'fastembed_cache'
                
                # 详细日志用于调试
                logger.info(f"打包环境检测:")
                logger.info(f"  sys.executable: {sys.executable}")
                logger.info(f"  sys._MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")
                logger.info(f"  base_path: {base_path}")
                logger.info(f"  bundled_cache: {bundled_cache}")
                logger.info(f"  bundled_cache.exists(): {bundled_cache.exists()}")
                
                if bundled_cache.exists():
                    # 检查目录内容
                    items = list(bundled_cache.iterdir())
                    logger.info(f"  bundled_cache 包含 {len(items)} 个项目")
                    for item in items[:5]:  # 只显示前5个
                        logger.info(f"    - {item.name} ({'目录' if item.is_dir() else '文件'})")
                    
                    # 检查 hub 子目录
                    hf_cache = bundled_cache / 'hub'
                    logger.info(f"  hub 目录存在: {hf_cache.exists()}")
                    
                    if hf_cache.exists():
                        hub_items = list(hf_cache.iterdir())
                        logger.info(f"  hub 目录包含 {len(hub_items)} 个项目")
                        for item in hub_items[:3]:  # 只显示前3个
                            logger.info(f"    - {item.name}")
                    
                    # 设置 HuggingFace 缓存目录指向打包的模型目录
                    # fastembed 使用 HuggingFace Hub，需要设置 HF_HOME 或 HUGGINGFACE_HUB_CACHE
                    if hf_cache.exists() and any(hf_cache.iterdir()):
                        # 设置 HuggingFace 缓存环境变量
                        os.environ['HF_HOME'] = str(bundled_cache)
                        os.environ['HUGGINGFACE_HUB_CACHE'] = str(hf_cache)
                        cache_dir = str(bundled_cache)
                        logger.info(f"✅ 检测到打包环境，使用打包的模型目录: {cache_dir}")
                        logger.info(f"✅ 设置 HuggingFace 缓存: {hf_cache}")
                    elif bundled_cache.exists() and any(bundled_cache.iterdir()):
                        # 即使没有 hub 目录，也尝试使用（可能目录结构不同）
                        os.environ['HF_HOME'] = str(bundled_cache)
                        cache_dir = str(bundled_cache)
                        logger.info(f"✅ 检测到打包环境，使用打包的模型目录: {cache_dir}")
                        logger.warning(f"⚠️ hub 目录不存在，但模型目录存在，尝试使用")
                    else:
                        # 目录存在但为空
                        default_cache = os.path.expanduser('~/.cache/huggingface')
                        cache_dir = default_cache
                        logger.warning(f"⚠️ 打包的模型目录存在但为空: {bundled_cache}")
                        logger.warning(f"⚠️ 回退到默认 HuggingFace 缓存目录: {cache_dir}")
                        logger.warning("提示：打包前请运行 'USE_PROJECT_MODELS=true python scripts/preload_fastembed_models.py' 下载模型")
                else:
                    # 回退到默认缓存目录
                    default_cache = os.path.expanduser('~/.cache/huggingface')
                    cache_dir = default_cache
                    logger.warning(f"⚠️ 打包的模型目录不存在: {bundled_cache}")
                    logger.warning(f"⚠️ 回退到默认 HuggingFace 缓存目录: {cache_dir}")
                    logger.warning("提示：打包前请运行 'USE_PROJECT_MODELS=true python scripts/preload_fastembed_models.py' 下载模型")
                    logger.warning("提示：确保 build.spec 中正确配置了 datas 项")
            else:
                # 开发环境，使用默认 HuggingFace 缓存目录
                default_cache = os.path.expanduser('~/.cache/huggingface')
                cache_dir = default_cache
                logger.info(f"使用默认 HuggingFace 缓存目录: {cache_dir}")
        
        # 注意：fastembed 使用 HuggingFace Hub，所以设置 HF_HOME 而不是 FASTEMBED_CACHE_DIR
        if not os.getenv('HF_HOME'):
            os.environ['HF_HOME'] = cache_dir
        if not os.getenv('HUGGINGFACE_HUB_CACHE'):
            hf_cache = Path(cache_dir) / 'hub'
            if hf_cache.exists():
                os.environ['HUGGINGFACE_HUB_CACHE'] = str(hf_cache)
        
        logger.info(f"FastEmbed/HuggingFace 缓存目录: {cache_dir}")
        
        self._initialize_model()
    
    def _initialize_model(self):
        """
        初始化 FastEmbed 模型并严格校验维度
        
        Raises:
            ValueError: 如果实际维度与配置不一致
        """
        try:
            from fastembed import TextEmbedding
            
            logger.info(f"正在加载 FastEmbed 模型: {self._model_name}")
            logger.info(f"配置的期望维度: {self._expected_dim}")
            
            # 初始化模型（如果未下载会自动下载，生产环境应提前预下载）
            self._model = TextEmbedding(model_name=self._model_name)
            
            # 获取实际维度：通过编码一个测试文本
            test_embedding = list(self._model.embed(["test"]))
            if not test_embedding:
                raise RuntimeError(f"模型 {self._model_name} 测试编码返回空结果")
            
            actual_dim = len(test_embedding[0])
            self._dimension = actual_dim
            
            # ⚠️ 严格校验维度一致性（P0 约束）
            if actual_dim != self._expected_dim:
                error_msg = (
                    f"❌ 维度不匹配！\n"
                    f"   配置维度 (EMBEDDING_DIM): {self._expected_dim}\n"
                    f"   实际模型维度: {actual_dim}\n"
                    f"   模型名称: {self._model_name}\n"
                    f"\n"
                    f"⚠️ 修复方法：\n"
                    f"   1. 修改环境变量 EMBEDDING_DIM={actual_dim}，或\n"
                    f"   2. 使用维度为 {self._expected_dim} 的模型\n"
                    f"\n"
                    f"⚠️ 注意：embedding 维度一旦确定，不允许再变更（sqlite-vec 要求）"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            logger.info(f"✅ FastEmbed 模型加载成功: {self._model_name}")
            logger.info(f"   维度: {self._dimension} (与配置一致)")
            
        except ImportError:
            logger.error("fastembed 未安装，请运行: pip install fastembed")
            raise
        except ValueError:
            # 重新抛出维度不匹配错误
            raise
        except Exception as e:
            logger.error(f"FastEmbed 模型加载失败: {e}", exc_info=True)
            raise
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        编码文档列表为向量
        
        Args:
            texts: 文本列表（不允许为空列表，空列表返回 []）
            
        Returns:
            向量列表，每个向量是 List[float]
            
        ⚠️ 类型约定：
            - 逻辑类型：List[List[float]]
            - 物理约定：float32 语义（Python float 容器，值在 float32 范围内）
            - ⚠️ 架构：float32 buffer 转换应在 VectorStore 层实现（不在 Embedding 层）
        """
        if not texts:
            # 空输入约定：返回空列表
            return []
        
        try:
            # FastEmbed 的 embed 方法返回迭代器，每个元素是 numpy array
            # 需要转换为 List[List[float]]
            embeddings = []
            for embedding in self._model.embed(texts):
                # 转换为 Python list（值在 float32 范围内）
                # ⚠️ 架构：float32 buffer 转换应在 VectorStore 层实现
                embedding_list = [float(x) for x in embedding]
                embeddings.append(embedding_list)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"FastEmbed 文档编码失败: {e}", exc_info=True)
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """
        编码查询文本为向量
        
        Args:
            text: 单个文本（不允许为空字符串，空字符串抛出 ValueError）
            
        Returns:
            向量，List[float]
            
        Raises:
            ValueError: 如果输入为空字符串
            
        ⚠️ 类型约定：
            - 逻辑类型：List[float]
            - 物理约定：float32 语义（Python float 容器，值在 float32 范围内）
            - ⚠️ 架构：float32 buffer 转换应在 VectorStore 层实现（不在 Embedding 层）
        """
        if not text or not text.strip():
            raise ValueError("查询文本不能为空字符串")
        
        try:
            # FastEmbed 的 embed 方法返回迭代器
            embeddings = list(self._model.embed([text]))
            if embeddings:
                # 转换为 Python list（值在 float32 范围内）
                # ⚠️ 架构：float32 buffer 转换应在 VectorStore 层实现
                return [float(x) for x in embeddings[0]]
            else:
                logger.error("FastEmbed 查询编码返回空结果")
                raise RuntimeError("FastEmbed 查询编码返回空结果")
                
        except Exception as e:
            logger.error(f"FastEmbed 查询编码失败: {e}", exc_info=True)
            raise
    
    def dimension(self) -> int:
        """
        返回 embedding 维度
        
        Returns:
            embedding 维度（整数，与配置 EMBEDDING_DIM 一致）
        """
        return self._dimension
    
    def model_name(self) -> str:
        """
        返回模型名称
        
        Returns:
            模型名称字符串
        """
        return self._model_name
