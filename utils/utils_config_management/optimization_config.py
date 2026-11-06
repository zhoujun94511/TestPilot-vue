#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import json
from typing import Dict, Any
from config.settings import settings
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


class OptimizationConfig:
    """
    性能优化配置管理器
    
    职责：
    - 管理性能优化相关配置
    - 处理内容去重配置
    - 管理知识库配置
    - 不处理前端API配置
    """

    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.reload_from_settings()

    @staticmethod
    def _load_json_config(filename: str, default_value: Any = None) -> Any:
        """
        统一的JSON配置文件加载方法
        
        Args:
            filename: 配置文件名
            default_value: 默认值
            
        Returns:
            加载的配置数据或默认值
        """
        if default_value is None:
            default_value = {}
            
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.abspath(os.path.join(base_dir, "..", "..", "config", filename))
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            
            # 验证配置数据
            if not isinstance(config_data, dict):
                logger.warning(f"{filename} 配置格式不正确，使用默认值")
                return default_value

            return config_data
            
        except FileNotFoundError:
            logger.warning(f"未找到配置文件: {filename}，路径: {config_path}")
            return default_value
        except json.JSONDecodeError as e:
            logger.error(f"解析配置文件 {filename} 失败: {e}")
            return default_value
        except Exception as e:
            logger.error(f"加载配置文件 {filename} 出错: {e}")
            return default_value

    def refresh_settings_values(self):
        """从 settings 实例读取当前值；配置中心保存后会写回 settings，所以每次取配置都要重读。"""
        self.config.update({
            'max_workers': getattr(settings, "MAX_WORKERS", 3),
            'chunk_size': getattr(settings, "CHUNK_SIZE", 1000),
            'max_memory_mb': getattr(settings, "MAX_MEMORY_MB", 500),
            'enable_parallel': getattr(settings, "ENABLE_PARALLEL", True),
            'enable_streaming': getattr(settings, "ENABLE_STREAMING", False),
            'max_case_num': getattr(settings, "MAX_CASE_NUM", 50),
            'supported_formats': getattr(
                settings,
                "SUPPORTED_FORMATS",
                ['.txt', '.md', '.docx', '.csv', '.json', '.xlsx', '.pdf', '.yaml', '.yml']
            ),
            'content_similarity_threshold': getattr(settings, "CONTENT_SIMILARITY_THRESHOLD", 0.8),
            'enable_content_dedup': getattr(settings, "ENABLE_CONTENT_DEDUP", True),
            'content_dedup_weights': getattr(settings, "CONTENT_DEDUP_WEIGHTS", {
                'title': 0.4, 'steps': 0.3, 'expected': 0.2, 'preconditions': 0.1
            }),
            'content_dedup_batch_size': getattr(settings, "CONTENT_DEDUP_BATCH_SIZE", 100),
            'enable_content_dedup_report': getattr(settings, "ENABLE_CONTENT_DEDUP_REPORT", False),
            'risk_weight_map': getattr(settings, "RISK_WEIGHT_MAP", {
                "low": 1,
                "medium": 4,
                "high": 8,
                "critical": 15
            }),
        })

    def reload_from_settings(self):
        """从 settings 和 JSON 文件重新加载配置"""
        self.config = {'knowledge_base': self._load_json_config("knowledge_base.json", {})}
        self.refresh_settings_values()

    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        self.refresh_settings_values()
        return self.config.copy()

    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        self.config.update(new_config)

    def log_current_config(self):
        """打印当前配置到日志"""
        logger.info(f"当前优化配置: {self.config}")

    # -----------------------
    # 优化工具方法
    # -----------------------
    @staticmethod
    def get_optimal_chunk_size(data_size: int) -> int:
        if data_size < 1000:
            return max(data_size, 1)
        elif data_size < 10000:
            return 1000
        elif data_size < 100000:
            return 5000
        else:
            return 10000

    @staticmethod
    def get_optimal_workers(data_size: int) -> int:
        if data_size < 1000:
            return 1
        elif data_size < 10000:
            return 2
        elif data_size < 100000:
            return 3
        else:
            return 4

    def should_use_streaming(self, data_size: int) -> bool:
        return data_size > self.config['chunk_size'] or self.config['enable_streaming']

    def should_use_parallel(self, data_size: int) -> bool:
        return data_size > 1000 and self.config['enable_parallel']

    # -----------------------
    # 内容去重相关方法
    # -----------------------
    def should_use_content_dedup(self, case_count: int) -> bool:
        """判断是否应该使用内容去重"""
        return (self.config['enable_content_dedup'] and
                case_count > 1)

    def get_content_dedup_batch_size(self, total_cases: int) -> int:
        """获取内容去重的最佳批次大小"""
        batch_size = self.config['content_dedup_batch_size']
        if total_cases < batch_size:
            return total_cases
        return batch_size

    def get_content_similarity_threshold(self) -> float:
        """获取内容相似度阈值"""
        return self.config['content_similarity_threshold']

    def get_content_dedup_weights(self) -> Dict[str, float]:
        """获取内容去重权重配置"""
        return self.config['content_dedup_weights']

    def should_generate_dedup_report(self) -> bool:
        """是否应该生成去重报告"""
        return self.config['enable_content_dedup_report']

    @staticmethod
    def get_optimal_dedup_strategy(case_count: int) -> str:
        """获取最佳去重策略"""
        if case_count < 10:
            return "simple"  # 简单去重
        elif case_count < 100:
            return "standard"  # 标准去重
        else:
            return "advanced"  # 高级去重（分批处理）

    def get_dedup_performance_config(self, case_count: int) -> Dict[str, Any]:
        """获取去重性能配置"""
        strategy = self.get_optimal_dedup_strategy(case_count)

        if strategy == "simple":
            return {
                'batch_size': case_count,
                'parallel': False,
                'streaming': False
            }
        elif strategy == "standard":
            return {
                'batch_size': min(self.get_content_dedup_batch_size(case_count), 50),
                'parallel': False,
                'streaming': False
            }
        else:  # advanced
            return {
                'batch_size': self.get_content_dedup_batch_size(case_count),
                'parallel': self.should_use_parallel(case_count),
                'streaming': self.should_use_streaming(case_count)
            }


# -----------------------
# 全局配置实例（单例）
# -----------------------
_optimization_config: OptimizationConfig | None = None


def get_optimization_config() -> OptimizationConfig:
    global _optimization_config
    if _optimization_config is None:
        _optimization_config = OptimizationConfig()
    else:
        _optimization_config.refresh_settings_values()
    return _optimization_config


# -----------------------
# 便捷函数
# -----------------------
def get_content_dedup_config() -> Dict[str, Any]:
    """获取内容去重配置的便捷函数"""
    config = get_optimization_config()
    return {
        'threshold': config.get_content_similarity_threshold(),
        'weights': config.get_content_dedup_weights(),
        'batch_size': config.config['content_dedup_batch_size'],
        'enabled': config.config['enable_content_dedup'],
        'report_enabled': config.config['enable_content_dedup_report']
    }