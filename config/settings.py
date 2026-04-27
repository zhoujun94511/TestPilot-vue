#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import json
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).parent.parent
ROOT_DIR = BASE_DIR.parent


def _safe_json_parse(json_str: str, default_value: Any) -> Any:
    """
    安全的JSON解析函数
    
    Args:
        json_str: JSON字符串
        default_value: 默认值
        
    Returns:
        解析后的数据或默认值
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        # 注意：这里不能使用logger，因为logger可能还没有初始化
        # 使用print作为fallback，但格式统一
        print(f"[WARN] JSON解析失败，使用默认值: {e}")
        return default_value


class Config:
    """基础配置类"""
    # Flask配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'testpilot-secret-key-2024')
    JSON_AS_ASCII = False

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR}/testpilot.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 会话配置
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_FILE_DIR = str(BASE_DIR / 'sessions')

    # 文件上传配置
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    MAX_CONTENT_LENGTH = 3072 * 1024 * 1024  # 约3G (增加以支持大文件和批量上传)
    ALLOWED_EXTENSIONS = {'txt', 'csv', 'docx', 'pdf', 'json', 'md'}

    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = BASE_DIR / 'logs'

    # AI模型配置
    DEFAULT_COMPANY = os.getenv('DEFAULT_COMPANY', 'OPENAI').upper()
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', '4000'))  # AI聊天Token数
    
    # 用例生成专用Token配置
    TR_OPENAI_MAX_TOKENS = int(os.getenv('TR_OPENAI_MAX_TOKENS', '8000'))  # OpenAI用例生成Token数
    TR_DEEPSEEK_MAX_TOKENS = int(os.getenv('TR_DEEPSEEK_MAX_TOKENS', '8000'))  # DeepSeek用例生成Token数

    # 根据DEFAULT_COMPANY动态选择MODEL
    def _get_model(self):
        company = self.DEFAULT_COMPANY.upper() if self.DEFAULT_COMPANY else 'OPENAI'
        if company == 'OPENAI':
            return os.getenv('OPENAI_MODEL', 'gpt-5')
        elif company == 'DEEPSEEK':
            return os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
        elif company == 'OLLAMA':
            return os.getenv('OLLAMA_MODEL', 'phi:2.7b')
        elif company == 'GEMINI':
            return os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
        elif company == 'QWEN':
            return os.getenv('QWEN_MODEL', 'qwen-flash')
        else:
            return 'gpt-5'  # 默认fallback

    # 添加动态获取当前模型的方法
    @property
    def current_model(self):
        """动态获取当前配置的模型"""
        return self._get_model()

    # 添加获取可用模型列表的方法
    @property
    def available_models(self):
        """根据当前公司获取可用模型列表"""
        company = self.DEFAULT_COMPANY.upper() if self.DEFAULT_COMPANY else 'OPENAI'
        if company == 'OPENAI':
            return ['gpt-3.5-turbo', 'gpt-5']
        elif company == 'DEEPSEEK':
            return ['deepseek-chat', 'deepseek-reasoner']
        elif company == 'OLLAMA':
            return ['phi:2.7b', 'llama2:7b', 'gemma:2b']
        elif company == 'GEMINI':
            return ['gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-1.5-pro', 'gemini-1.5-flash']
        elif company == 'QWEN':
            return ['qwen-flash', 'qwen-plus', 'qwen-max']
        else:
            return ['gpt-5']

    # 添加获取模型能力的方法
    @property
    def model_capabilities(self):
        """获取当前模型的能力"""
        company = self.DEFAULT_COMPANY.upper() if self.DEFAULT_COMPANY else 'OPENAI'
        return {
            'supports_streaming': True,
            'supports_knowledge': company in ['OPENAI', 'DEEPSEEK', 'GEMINI', 'QWEN'],
            'supports_context': True,
            'max_tokens': getattr(self, 'MAX_TOKENS', 4000)  # 使用统一的MAX_TOKENS配置
        }

    # 在类初始化时设置MODEL
    def __init__(self):
        self.MODEL = self._get_model()
    
    def load_from_config_center(self):
        """
        从配置中心加载配置并更新当前配置
        优先级：配置中心 > .env 文件
        """
        try:
            # 延迟导入，避免循环依赖
            from services.config_center_service import config_center_service

            # 读取配置中心的AI提供商配置
            enable_openai = config_center_service.get_config_value('ENABLE_OPENAI')
            enable_deepseek = config_center_service.get_config_value('ENABLE_DEEPSEEK')
            enable_ollama = config_center_service.get_config_value('ENABLE_OLLAMA')
            enable_gemini = config_center_service.get_config_value('ENABLE_GEMINI')
            enable_qwen = config_center_service.get_config_value('ENABLE_QWEN')
            default_company = config_center_service.get_config_value('DEFAULT_COMPANY')
            
            # 转换布尔值
            enable_openai = str(enable_openai).lower() == 'true' if enable_openai else False
            enable_deepseek = str(enable_deepseek).lower() == 'true' if enable_deepseek else False
            enable_ollama = str(enable_ollama).lower() == 'true' if enable_ollama else False
            enable_gemini = str(enable_gemini).lower() == 'true' if enable_gemini else False
            enable_qwen = str(enable_qwen).lower() == 'true' if enable_qwen else False
            
            # 检查是否所有AI都被禁用
            all_disabled = not (enable_openai or enable_deepseek or enable_ollama or enable_gemini or enable_qwen)
            
            # 如果配置中心有DEFAULT_COMPANY配置且不是所有AI都禁用，使用配置中心的值
            if default_company and not all_disabled:
                self.DEFAULT_COMPANY = default_company.upper() if isinstance(default_company, str) else default_company
                print(f"[INFO] 从配置中心加载 DEFAULT_COMPANY: {self.DEFAULT_COMPANY}")
            elif all_disabled:
                # 所有AI都被禁用，回退到.env的deepseek配置
                env_company = os.getenv('DEFAULT_COMPANY', 'DEEPSEEK').upper()
                self.DEFAULT_COMPANY = env_company
                print(f"[INFO] 配置中心所有AI提供商均未启用，回退到 .env 配置: {env_company}")
            
            # 更新其他配置项
            config_mappings = {
                'OPENAI_API_KEY': 'OPENAI_API_KEY',
                'OPENAI_BASE_URL': 'OPENAI_BASE_URL',
                'OPENAI_MODEL': 'OPENAI_MODEL',
                'TR_OPENAI_MAX_TOKENS': 'TR_OPENAI_MAX_TOKENS',
                'DEEPSEEK_API_KEY': 'DEEPSEEK_API_KEY',
                'DEEPSEEK_BASE_URL': 'DEEPSEEK_BASE_URL',
                'DEEPSEEK_MODEL': 'DEEPSEEK_MODEL',
                'TR_DEEPSEEK_MAX_TOKENS': 'TR_DEEPSEEK_MAX_TOKENS',
                'OLLAMA_BASE_URL': 'OLLAMA_BASE_URL',
                'OLLAMA_MODEL': 'OLLAMA_MODEL',
                'GEMINI_API_KEY': 'GEMINI_API_KEY',
                'GEMINI_BASE_URL': 'GEMINI_BASE_URL',
                'GEMINI_MODEL': 'GEMINI_MODEL',
                'TR_GEMINI_MAX_TOKENS': 'TR_GEMINI_MAX_TOKENS',
                'QWEN_API_KEY': 'QWEN_API_KEY',
                'QWEN_BASE_URL': 'QWEN_BASE_URL',
                'QWEN_MODEL': 'QWEN_MODEL',
                'QWEN_TEMPERATURE': 'QWEN_TEMPERATURE',
                'TR_QWEN_MAX_TOKENS': 'TR_QWEN_MAX_TOKENS',
                'QWEN_TIMEOUT': 'QWEN_TIMEOUT',
                'MAX_TOKENS': 'MAX_TOKENS',
                'ENABLE_EXPERIMENTAL_ACTIONS': 'ENABLE_EXPERIMENTAL_ACTIONS',
            }
            
            # 从配置中心读取并更新配置
            for attr_name, config_key in config_mappings.items():
                value = config_center_service.get_config_value(config_key)
                if value is not None and value != '':
                    # 对于数值类型的配置，进行类型转换
                    if attr_name in ['MAX_TOKENS', 'TR_OPENAI_MAX_TOKENS', 'TR_DEEPSEEK_MAX_TOKENS', 'TR_GEMINI_MAX_TOKENS', 'TR_QWEN_MAX_TOKENS', 'QWEN_TIMEOUT']:
                        try:
                            value = int(value)
                        except (ValueError, TypeError):
                            continue
                    elif attr_name in ['QWEN_TEMPERATURE']:
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            continue
                    elif attr_name in ['ENABLE_EXPERIMENTAL_ACTIONS']:
                        value = str(value).strip().lower() in ('true', '1', 'yes')
                    setattr(self, attr_name, value)
            
            # 重新设置MODEL
            self.MODEL = self._get_model()
            print(f"[INFO] 配置中心加载完成，当前使用的AI提供商: {self.DEFAULT_COMPANY}, 模型: {self.MODEL}")
            
        except Exception as e:
            print(f"[WARN] 从配置中心加载配置失败，将使用 .env 配置: {e}")

    # OpenAI配置
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-5')
    GPT5_VERBOSITY = os.getenv('GPT5_VERBOSITY', 'low')
    GPT5_REASONING_EFFORT = os.getenv('GPT5_REASONING_EFFORT', 'minimal')

    # DeepSeek配置
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
    DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')

    # Ollama配置
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'phi:2.7b')

    # Gemini配置
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_BASE_URL = os.getenv('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
    TR_GEMINI_MAX_TOKENS = int(os.getenv('TR_GEMINI_MAX_TOKENS', '8000'))

    # Qwen配置
    QWEN_API_KEY = os.getenv('QWEN_API_KEY')
    QWEN_BASE_URL = os.getenv('QWEN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    QWEN_MODEL = os.getenv('QWEN_MODEL', 'qwen-flash')
    QWEN_TEMPERATURE = float(os.getenv('QWEN_TEMPERATURE', '0.7'))
    TR_QWEN_MAX_TOKENS = int(os.getenv('TR_QWEN_MAX_TOKENS', '8000'))
    # LLM 超时配置（适用于所有模型）
    LLM_TIMEOUT_DEFAULT = int(os.getenv('LLM_TIMEOUT_DEFAULT', '120'))  # 默认超时120秒
    LLM_TIMEOUT_CASE_GENERATION = int(os.getenv('LLM_TIMEOUT_CASE_GENERATION', '300'))  # 用例生成300秒
    LLM_TIMEOUT_REQUIREMENT_ANALYSIS = int(os.getenv('LLM_TIMEOUT_REQUIREMENT_ANALYSIS', '300'))  # 需求分析300秒
    
    # 保持向后兼容（Qwen特定配置）
    QWEN_TIMEOUT = int(os.getenv('QWEN_TIMEOUT', str(LLM_TIMEOUT_CASE_GENERATION)))

    # 性能配置
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1000'))
    MAX_MEMORY_MB = int(os.getenv('MAX_MEMORY_MB', '500'))
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', '3'))

    # 向量存储开关：关闭后不加载 sqlite-vec/FTS5，无对应库也可运行，便于 PyInstaller 缩减包体
    ENABLE_VECTOR_STORE = os.getenv('ENABLE_VECTOR_STORE', 'true').strip().lower() in ('true', '1', 'yes')

    # 向量存储后端配置
    VECTOR_BACKEND = os.getenv('VECTOR_BACKEND', 'sqlite')  # 'sqlite' | 'chroma'
    
    # ChromaDB配置（保留用于回滚）
    CHROMA_PERSIST_DIRECTORY = str(BASE_DIR / 'vector_store')
    VECTOR_STORE_DIR = str(BASE_DIR / 'vector_store')
    CHROMA_COLLECTION_NAME = os.getenv('CHROMA_COLLECTION_NAME', 'testpilot_knowledge')
    
    # SQLite 向量存储配置
    SQLITE_VECTOR_DB_PATH = os.getenv('SQLITE_VECTOR_DB_PATH', '')  # 如果为空，使用 VECTOR_STORE_DIR/vector_store.db
    SQLITE_VEC_EXTENSION_PATH = os.getenv('SQLITE_VEC_EXTENSION_PATH', '')  # sqlite-vec 扩展路径（可选）
    
    # 向量数据库批次大小配置（根据平台自动调整）
    # Windows 上使用更小的批次以避免访问冲突，其他平台可以使用更大的批次
    VECTOR_DB_BATCH_SIZE_WINDOWS = int(os.getenv('VECTOR_DB_BATCH_SIZE_WINDOWS', '100'))
    VECTOR_DB_BATCH_SIZE_OTHER = int(os.getenv('VECTOR_DB_BATCH_SIZE_OTHER', '500'))
    
    # 向量数据库批次间延迟配置（秒）
    VECTOR_DB_BATCH_DELAY_WINDOWS = float(os.getenv('VECTOR_DB_BATCH_DELAY_WINDOWS', '0.1'))
    VECTOR_DB_BATCH_DELAY_OTHER = float(os.getenv('VECTOR_DB_BATCH_DELAY_OTHER', '0'))
    
    # 向量数据库批量添加重试配置
    VECTOR_DB_BATCH_MAX_RETRIES = int(os.getenv('VECTOR_DB_BATCH_MAX_RETRIES', '3'))
    VECTOR_DB_BATCH_RETRY_WAIT_BASE = float(os.getenv('VECTOR_DB_BATCH_RETRY_WAIT_BASE', '0.5'))
    
    @staticmethod
    def get_vector_db_batch_size():
        """根据平台获取向量数据库批次大小"""
        import platform
        if platform.system() == "Windows":
            return Config.VECTOR_DB_BATCH_SIZE_WINDOWS
        else:
            return Config.VECTOR_DB_BATCH_SIZE_OTHER
    
    @staticmethod
    def get_vector_db_batch_delay():
        """根据平台获取向量数据库批次间延迟（秒）"""
        import platform
        if platform.system() == "Windows":
            return Config.VECTOR_DB_BATCH_DELAY_WINDOWS
        else:
            return Config.VECTOR_DB_BATCH_DELAY_OTHER
    
    @staticmethod
    def is_windows():
        """检查是否为 Windows 平台"""
        import platform
        return platform.system() == "Windows"

    # RAG配置 (统一智能检索配置)
    RAG_TOP_K = int(os.getenv('RAG_TOP_K', '5'))
    RAG_SCORE_THRESHOLD = float(os.getenv('RAG_SCORE_THRESHOLD', '0.7'))  # 统一为0.7
    RAG_ENABLE_RERANKING = os.getenv('RAG_ENABLE_RERANKING', 'true').lower() == 'true'
    RAG_ENABLE_QUERY_EXPANSION = os.getenv('RAG_ENABLE_QUERY_EXPANSION', 'true').lower() == 'true'
    RAG_ENABLE_CONTEXT_AWARENESS = os.getenv('RAG_ENABLE_CONTEXT_AWARENESS', 'true').lower() == 'true'
    RAG_MAX_CONTEXT_LENGTH = int(os.getenv('RAG_MAX_CONTEXT_LENGTH', '2000'))
    RAG_SIMILARITY_THRESHOLD = float(os.getenv('RAG_SIMILARITY_THRESHOLD', '0.8'))
    RAG_STRATEGY = os.getenv('RAG_STRATEGY', 'auto')  # auto, semantic, keyword, hybrid, context_aware
    
    # FTS5 + sqlite-vec 混合检索配置
    ENABLE_HYBRID_RETRIEVAL = os.getenv('ENABLE_HYBRID_RETRIEVAL', 'true').lower() == 'true'  # 是否启用混合检索
    
    # FTS5 召回候选数量配置（自适应策略）
    # 经验公式：FTS_CANDIDATE_K ≈ topK × factor
    #   - topK = 5  → factor=40 → 200
    #   - topK = 10 → factor=40 → 400
    # 当前默认值 200 是合理的默认值（适用于 topK = 5~10）
    FTS_CANDIDATE_K = int(os.getenv('FTS_CANDIDATE_K', '200'))  # FTS5 召回候选数量（第一阶段，已废弃，保留用于向后兼容）
    FTS_CANDIDATE_FACTOR = int(os.getenv('FTS_CANDIDATE_FACTOR', '40'))  # 自适应候选因子（默认 40，对应 topK × 40）
    MAX_FTS_CANDIDATE_K = int(os.getenv('MAX_FTS_CANDIDATE_K', '800'))  # FTS5 候选数量上限（安全上限，避免 SQLite IN 参数问题）
    
    # Embedding模型配置（FastEmbed / ONNX）
    # 重要：embedding 维度一旦确定，不允许再变更（sqlite-vec 要求）
    EMBEDDING_MODEL_NAME = os.getenv('EMBEDDING_MODEL_NAME', 'BAAI/bge-small-en-v1.5')  # FastEmbed 模型名称
    EMBEDDING_DIM = int(os.getenv('EMBEDDING_DIM', '384'))  # embedding 维度（必须与实际模型维度一致）
    EMBEDDING_CACHE_SIZE = int(os.getenv('EMBEDDING_CACHE_SIZE', '1000'))  # embedding 缓存大小
    FASTEMBED_CACHE_DIR = os.getenv('FASTEMBED_CACHE_DIR', '')  # FastEmbed 模型缓存目录（可选，默认 ~/.cache/fastembed）
    
    # 兼容旧配置（已废弃，保留用于向后兼容）
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'fastembed')  # 已废弃，固定为 fastembed
    EMBEDDING_DEVICE = os.getenv('EMBEDDING_DEVICE', 'cpu')  # 已废弃，固定为 cpu
    
    # Sentence-Transformers专用配置
    SENTENCE_TRANSFORMER_MODEL = os.getenv('SENTENCE_TRANSFORMER_MODEL', 'auto')  # 具体模型名称
    SENTENCE_TRANSFORMER_DEVICE = os.getenv('SENTENCE_TRANSFORMER_DEVICE', 'auto')  # 设备选择
    SENTENCE_TRANSFORMER_BATCH_SIZE = int(os.getenv('SENTENCE_TRANSFORMER_BATCH_SIZE', '32'))  # 批处理大小
    SENTENCE_TRANSFORMER_MAX_LENGTH = int(os.getenv('SENTENCE_TRANSFORMER_MAX_LENGTH', '512'))  # 最大序列长度
    SENTENCE_TRANSFORMER_CACHE_DIR = os.getenv('SENTENCE_TRANSFORMER_CACHE_DIR', '')  # 模型缓存目录
    SENTENCE_TRANSFORMER_ENABLE_CACHE = os.getenv('SENTENCE_TRANSFORMER_ENABLE_CACHE', 'true').lower() == 'true'  # 是否启用缓存

    # 缓存配置
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', '300'))
    
    # 智能分块配置 (统一文档分块配置)
    CHUNK_STRATEGY = os.getenv('CHUNK_STRATEGY', 'adaptive')  # fixed_size, semantic, adaptive, hierarchical
    CHUNK_BASE_SIZE = int(os.getenv('CHUNK_BASE_SIZE', '1000'))
    CHUNK_MIN_SIZE = int(os.getenv('CHUNK_MIN_SIZE', '200'))
    CHUNK_MAX_SIZE = int(os.getenv('CHUNK_MAX_SIZE', '2000'))
    CHUNK_OVERLAP_SIZE = int(os.getenv('CHUNK_OVERLAP_SIZE', '200'))
    CHUNK_ENABLE_SEMANTIC_BOUNDARY = os.getenv('CHUNK_ENABLE_SEMANTIC_BOUNDARY', 'true').lower() == 'true'
    CHUNK_ENABLE_CONTENT_TYPE_DETECTION = os.getenv('CHUNK_ENABLE_CONTENT_TYPE_DETECTION', 'true').lower() == 'true'
    CHUNK_ENABLE_QUALITY_ASSESSMENT = os.getenv('CHUNK_ENABLE_QUALITY_ASSESSMENT', 'true').lower() == 'true'
    CHUNK_QUALITY_THRESHOLD = float(os.getenv('CHUNK_QUALITY_THRESHOLD', '0.7'))
    
    # ===========================================
    # 幻觉检测配置
    # ===========================================
    
    # 是否启用幻觉检测
    # 说明：控制是否对AI生成内容进行幻觉检测，提升内容质量但增加处理时间
    # 默认值：true，可通过环境变量 ENABLE_HALLUCINATION_DETECTION 修改
    ENABLE_HALLUCINATION_DETECTION = os.getenv('ENABLE_HALLUCINATION_DETECTION', 'true').lower() == 'true'
    
    # 幻觉检测相似度阈值
    # 说明：控制内容与源文档的相似度阈值，低于此值认为可能存在幻觉
    # 默认值：0.8，可通过环境变量 HALLUCINATION_SIMILARITY_THRESHOLD 修改
    HALLUCINATION_SIMILARITY_THRESHOLD = float(os.getenv('HALLUCINATION_SIMILARITY_THRESHOLD', '0.8'))
    
    # 幻觉检测置信度阈值
    # 说明：控制幻觉检测的置信度阈值，高于此值认为存在幻觉
    # 默认值：0.7，可通过环境变量 HALLUCINATION_CONFIDENCE_THRESHOLD 修改
    HALLUCINATION_CONFIDENCE_THRESHOLD = float(os.getenv('HALLUCINATION_CONFIDENCE_THRESHOLD', '0.7'))
    
    # 幻觉处理阈值配置
    # 说明：控制不同处理策略的触发阈值
    HALLUCINATION_WARN_THRESHOLD = float(os.getenv('HALLUCINATION_WARN_THRESHOLD', '0.3'))
    HALLUCINATION_AUTO_CORRECT_THRESHOLD = float(os.getenv('HALLUCINATION_AUTO_CORRECT_THRESHOLD', '0.5'))
    HALLUCINATION_REGENERATE_THRESHOLD = float(os.getenv('HALLUCINATION_REGENERATE_THRESHOLD', '0.7'))
    HALLUCINATION_FILTER_THRESHOLD = float(os.getenv('HALLUCINATION_FILTER_THRESHOLD', '0.9'))
    
    # 重新生成保护配置
    # 说明：防止重新生成死循环，控制最大重试次数
    HALLUCINATION_MAX_REGENERATE_ATTEMPTS = int(os.getenv('HALLUCINATION_MAX_REGENERATE_ATTEMPTS', '2'))

    # ===========================================
    # 用例生成配置
    # ===========================================
    
    # 最大用例生成数量
    # 说明：控制单次生成用例的最大数量，影响前端选项和性能
    # 默认值：50，可通过环境变量 MAX_CASE_NUM 修改
    MAX_CASE_NUM = int(os.getenv('MAX_CASE_NUM', '50'))
    
    # ===========================================
    # 性能优化配置
    # ===========================================
    
    # 是否启用并行处理
    # 说明：控制是否使用多线程/多进程进行并行处理，提升性能但增加资源消耗
    # 默认值：true，可通过环境变量 ENABLE_PARALLEL 修改
    ENABLE_PARALLEL = os.getenv('ENABLE_PARALLEL', 'true').lower() == 'true'
    
    # 是否启用流式处理
    # 说明：控制是否使用流式处理，减少内存占用但可能影响响应速度
    # 默认值：false，可通过环境变量 ENABLE_STREAMING 修改
    ENABLE_STREAMING = os.getenv('ENABLE_STREAMING', 'false').lower() == 'true'

    # 实验功能开关（默认关闭，避免影响主业务）
    ENABLE_EXPERIMENTAL_ACTIONS = os.getenv('ENABLE_EXPERIMENTAL_ACTIONS', 'false').strip().lower() in ('true', '1', 'yes')

    # ===========================================
    # 内容去重配置
    # ===========================================
    
    # 内容相似度阈值
    # 说明：控制用例去重的相似度阈值，0.0-1.0之间，值越高去重越严格
    # 默认值：0.8，可通过环境变量 CONTENT_SIMILARITY_THRESHOLD 修改
    CONTENT_SIMILARITY_THRESHOLD = float(os.getenv('CONTENT_SIMILARITY_THRESHOLD', '0.8'))
    
    # 是否启用内容去重
    # 说明：控制是否对生成的用例进行去重处理，提升用例质量但增加处理时间
    # 默认值：true，可通过环境变量 ENABLE_CONTENT_DEDUP 修改
    ENABLE_CONTENT_DEDUP = os.getenv('ENABLE_CONTENT_DEDUP', 'true').lower() == 'true'

    # 内容去重权重配置（JSON字符串）
    _content_dedup_weights_str = os.getenv('CONTENT_DEDUP_WEIGHTS',
                                           '{"title": 0.4, "steps": 0.3, "expected": 0.2, "preconditions": 0.1}')
    CONTENT_DEDUP_WEIGHTS = _safe_json_parse(_content_dedup_weights_str, 
                                            {"title": 0.4, "steps": 0.3, "expected": 0.2, "preconditions": 0.1})

    CONTENT_DEDUP_BATCH_SIZE = int(os.getenv('CONTENT_DEDUP_BATCH_SIZE', '100'))
    ENABLE_CONTENT_DEDUP_REPORT = os.getenv('ENABLE_CONTENT_DEDUP_REPORT', 'false').lower() == 'true'

    # 支持的文件格式
    SUPPORTED_FORMATS = ['.txt', '.md', '.docx', '.csv', '.json', '.xlsx', '.pdf', '.yaml', '.yml']

    # 风险权重映射
    _risk_weight_map_str = os.getenv('RISK_WEIGHT_MAP', '{"low": 1, "medium": 4, "high": 8, "critical": 15}')
    RISK_WEIGHT_MAP = _safe_json_parse(_risk_weight_map_str, 
                                      {"low": 1, "medium": 4, "high": 8, "critical": 15})

    # 测试用例生成 Prompt（普通版本）
    FUNCTION_PROMPT = """作为测试专家，请为以下需求生成最多{max_case_nums}个测试用例：

    ## 需求分析
    需求描述：{requirement}

    ## 复杂度分析
    {complexity_analysis}

    ## 建议的测试类型
    {suggested_test_types}

    ## 建议的测试方法
    {suggested_methods}

    请严格按照JSON格式生成测试用例列表

    每条测试用例包含的属性：
        - 用例编号（格式TC-模块-序号，如TC-LOGIN-01）
        - 功能模块
        - 用例标题（简明描述测试目的）
        - 前置条件
        - 测试步骤（数组，例：["步骤1","步骤2"]）
        - 预期结果（数组，例：["结果1","结果2"]）
        - 优先级（P0-P4，P0为最高）
        - test_type: 测试类型（从建议的测试类型中选择）
        - test_method: 测试方法（从建议的测试方法中选择）
        - 标签：相关的功能标签

    格式要求:
    {format_instructions}
    **重要：必须返回完整的JSON格式，不要添加任何解释文字！**

    返回示例参考（示例值仅用于结构说明；内容语言必须严格遵循上方格式要求）：
    {{
        "cases": [
            {{
                "case_id": "TC-LOGIN-01",
                "module": "登录认证",
                "title": "使用有效账号密码登录成功",
                "preconditions": "已准备可用账号和密码",
                "steps": ["1. 输入有效用户名和密码", "2. 点击登录按钮"],
                "expected": ["1. 登录成功", "2. 跳转到首页"],
                "priority": "P0",
                "test_type": "功能测试",
                "test_method": "等价类划分法",
                "tags": ["登录", "冒烟"]
            }}
        ]
    }}
    """

    # 批量测试用例生成 Prompt（支持多个需求）
    BATCH_FUNCTION_PROMPT = """作为测试专家，请为以下需求列表中的**每一个需求**分别生成测试用例。

核心要求（必须严格遵守）：
1. 下面列出了多个需求，每个需求都有一个唯一的需求ID（如req_1, req_2, req_3...）
2. 你必须为**每一个需求ID**都生成 **{max_case_nums} 个**测试用例
3. 不要遗漏任何一个需求ID
4. 每个测试用例必须包含正确的 requirement_id 字段

## 需求列表
{requirements_list}

## 复杂度分析
{complexity_analysis}

## 建议的测试类型
{suggested_test_types}

## 建议的测试方法
{suggested_methods}

    ## 输出要求

    **必须严格按照以下JSON格式返回，不要添加任何解释文字！**

    每条测试用例必须包含以下字段：
        - requirement_id: 对应的需求ID（从需求列表中获取，如"req_1"、"req_2"）
        - case_id: 用例编号（格式TC-模块-序号，如"TC-LOGIN-01"）
        - module: 功能模块（如"登录"）
        - title: 用例标题（简明描述测试目的）
        - preconditions: 前置条件（字符串）
        - steps: 测试步骤（字符串数组，如["步骤1","步骤2"]）
        - expected: 预期结果（字符串数组，如["结果1","结果2"]）
        - priority: 优先级（P0/P1/P2/P3/P4，P0为最高）
        - test_type: 测试类型（从建议的测试类型中选择）
        - test_method: 测试方法（从建议的测试方法中选择）
        - tags: 相关的功能标签（字符串数组，如["功能标签1", "功能标签2"]）

    JSON格式注意事项：
    1. 每个字段后面必须有逗号（除了最后一个字段）
    2. 所有字符串必须用双引号
    3. 数组最后一个元素后不要有逗号
    4. {format_instructions}

数量检查：
    - 请确保为每个需求ID都生成了 {max_case_nums} 个测试用例
    - 检查你的返回结果中是否包含了所有需求ID

返回格式示例：
{{
    "cases": [
        {{
            "requirement_id": "req_1",
            "case_id": "TC-LOGIN-01",
            "module": "登录认证",
            "title": "使用有效账号密码登录成功",
            "preconditions": "已准备可用账号和密码",
            "steps": ["1. 输入有效用户名和密码", "2. 点击登录按钮"],
            "expected": ["1. 登录成功", "2. 跳转到首页"],
            "priority": "P0",
            "test_type": "功能测试",
            "test_method": "等价类划分法",
            "tags": ["登录", "冒烟"]
        }},
        {{
            "requirement_id": "req_2",
            "case_id": "TC-LOGIN-02",
            ...
        }}
    ]
}}
"""

    # 测试用例生成 Prompt（带上下文 RAG 版本）
    FUNCTION_PROMPT_RAG = """作为测试专家，请为以下需求生成最多{max_case_nums}个测试用例：

    ## 需求分析
    先参考到的内容：{context}
    需求描述：{requirement}

    ## 复杂度分析
    {complexity_analysis}

    ## 建议的测试类型
    {suggested_test_types}

    ## 建议的测试方法
    {suggested_methods}

    每条测试用例包含的属性：
        - 用例编号（格式TC-模块-序号，如TC-LOGIN-01）
        - 功能模块
        - 用例标题（简明描述测试目的）
        - 前置条件
        - 测试步骤（数组，例：["步骤1","步骤2"]）
        - 预期结果（数组，例：["结果1","结果2"]）
        - 优先级（P0-P4，P0为最高）
        - test_type: 测试类型（从建议的测试类型中选择）
        - test_method: 测试方法（从建议的测试方法中选择）
        - 标签：相关的功能标签

    格式要求:
        {format_instructions}
        **重要：必须返回完整的JSON格式，不要添加任何解释文字！**

    返回示例参考（示例值仅用于结构说明；内容语言必须严格遵循上方格式要求）：
    {{
        "cases": [
            {{
                "case_id": "TC-LOGIN-01",
                "module": "登录认证",
                "title": "使用有效账号密码登录成功",
                "preconditions": "已准备可用账号和密码",
                "steps": ["1. 输入有效用户名和密码", "2. 点击登录按钮"],
                "expected": ["1. 登录成功", "2. 跳转到首页"],
                "priority": "P0",
                "test_type": "功能测试",
                "test_method": "等价类划分法",
                "tags": ["登录", "冒烟"]
            }}
        ]
    }}
    """

    # 需求分析提示模板
    REQUIREMENT_PROMPT = """
    你是一个专业的需求分析师，请从以下文档内容中提取结构化需求：
    {format_instructions}
    
    文档内容：
    {context}

    要求：
        1. 每个需求都要有明确的标题和描述
        2. 优先级分为：P0、P1、P2、P3（P0最高）
        3. 类型分为：functional、non-functional、business、technical
        4. 确保需求具体、可测试、可验证
    """

    # 测试点提取提示模板
    TEST_POINTS_PROMPT = """
请从以下文档中提取所有的测试点，包括功能测试点、边界测试点、异常测试点等。

文档内容：
{content}

请以JSON格式返回测试点列表，每个测试点包含：
- name: 测试点名称
- description: 详细描述
- type: 测试类型（functional/boundary/exception/performance）
- priority: 优先级（P0/P1/P2/P3）

请严格按照以下JSON格式返回：
{{
    "test_points": [
        {{
            "name": "测试点名称",
            "description": "详细描述",
            "type": "functional",
            "priority": "P1"
        }}
    ]
}}

**重要：必须返回完整的JSON格式，不要添加任何解释文字！**

语言输出要求：
{language_instruction}
"""

    # 业务规则提取提示模板
    BUSINESS_RULES_PROMPT = """
请从以下文档中提取所有的业务规则，包括验证规则、计算规则、流程规则等。

文档内容：
{content}

请以JSON格式返回业务规则列表，每个规则包含：
- name: 规则名称
- description: 规则描述
- type: 规则类型（validation/calculation/workflow）
- condition: 触发条件
- priority: 优先级（P0/P1/P2/P3）

请严格按照以下JSON格式返回：
{{
    "business_rules": [
        {{
            "name": "规则名称",
            "description": "规则描述",
            "type": "validation",
            "condition": "触发条件",
            "priority": "P2"
        }}
    ]
}}

**重要：必须返回完整的JSON格式，不要添加任何解释文字！**

语言输出要求：
{language_instruction}
"""

    # 测试用例生成 Prompt
    AGENT_PROMPT = """您是一个资深测试工程师，根据需求生成结构化的测试用例，要求：
    
     请严格按照JSON格式生成测试用例列表
     
     每条测试用例包含的属性：
        - 用例编号（格式TC-模块-序号，如TC-LOGIN-01）
        - 功能模块
        - 用例标题（简明描述测试目的）
        - 前置条件
        - 步骤（数组，例：["步骤1","步骤2"]）
        - 预期（数组，例：["结果1","结果2"]）
        - 优先级（P0-P4，P0为最高）
        - test_type: 测试类型
        - test_method: 测试方法
        - 标签：相关的功能标签
            
    **格式要求：**
        - 每条用例都是JSON格式
        - 必须返回完整的JSON格式
        - 不要添加任何解释文字
        - 确保JSON结构完整闭合
        - 每个字段都要用双引号包围
        - 数组格式正确
        - 不要输出多余的信息，只要结果
    
    返回参考：
         {{
            "cases": [
                {{
                    "case_id": "TC-LOGIN-01",
                    "module": "登录",
                    "title": "登录成功",
                    "preconditions": "用户名和密码正确",
                    "steps": ["1. 输入正确的用户名和密码", "2. 点击登录按钮"],
                    "expected": ["1. 登录成功", "2. 跳转到首页"],
                    "priority": "P0",
                    "test_type": "功能测试",
                    "test_method": "等价类划分法",
                    "tags": ["标签1", "标签2"]
                }}
            ]
         }}
    """

    @classmethod
    def init_app(cls, app):
        """初始化应用配置"""
        # 确保必要目录存在
        cls.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        (BASE_DIR / 'sessions').mkdir(parents=True, exist_ok=True)
        (BASE_DIR / 'vector_store').mkdir(parents=True, exist_ok=True)

        # 设置环境变量禁用遥测
        os.environ.update({
            "CHROMA_TELEMETRY_ENABLED": "false",
            "CHROMA_DISABLE_TELEMETRY": "true",
            "POSTHOG_DISABLED": "true",
            "POSTHOG_OPT_OUT_CAPTURING": "true",
            "OTEL_SDK_DISABLED": "true",
            "OTEL_TRACES_EXPORTER": "none",
            "OTEL_METRICS_EXPORTER": "none",
            "OTEL_LOGS_EXPORTER": "none",
            "LANGCHAIN_TRACING_V2": "false",
            "LANGCHAIN_API_KEY": ""
        })

        # 使用 app 参数进行配置
        app.config.update({
            'UPLOAD_FOLDER': str(cls.UPLOAD_FOLDER),
            'LOG_DIR': str(cls.LOG_DIR),
            'MAX_CONTENT_LENGTH': cls.MAX_CONTENT_LENGTH,
            'ALLOWED_EXTENSIONS': cls.ALLOWED_EXTENSIONS
        })


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    LOG_LEVEL = 'WARNING'


class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR}/test.db"


# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# 导出当前配置 - 关键修复：创建实例而不是类
settings = config.get(os.getenv('FLASK_ENV', 'default'), DevelopmentConfig)()


# 创建Settings类，用于optimization_config.py中的getattr调用
class Settings:
    """Settings类，用于optimization_config.py中的getattr调用"""

    def __init__(self):
        # 从当前配置中获取所有属性
        current_config = settings
        for attr_name in dir(current_config):
            if not attr_name.startswith('_'):
                setattr(self, attr_name, getattr(current_config, attr_name))


# 创建Settings实例
Settings = Settings()