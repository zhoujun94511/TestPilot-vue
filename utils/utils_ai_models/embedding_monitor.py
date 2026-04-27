#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Embedding性能监控器
监控Sentence-Transformers的性能指标和错误
"""
import time
import psutil
import threading
from typing import Dict, Any, List
from collections import deque
from dataclasses import dataclass
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)

@dataclass
class EmbeddingMetrics:
    """Embedding性能指标"""
    total_calls: int = 0
    total_tokens: int = 0
    total_time: float = 0.0
    avg_time_per_call: float = 0.0
    avg_tokens_per_call: float = 0.0
    error_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    memory_usage_mb: float = 0.0
    gpu_usage_percent: float = 0.0

@dataclass
class EmbeddingError:
    """Embedding错误记录"""
    timestamp: float
    error_type: str
    error_message: str
    model_name: str
    device: str
    input_length: int

class EmbeddingMonitor:
    """Embedding性能监控器"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics = EmbeddingMetrics()
        self.error_history: deque = deque(maxlen=max_history)
        self.performance_history: deque = deque(maxlen=max_history)
        self.lock = threading.Lock()
        self.start_time = time.time()
        
    def record_call(self, 
                   tokens: int, 
                   duration: float, 
                   success: bool = True,
                   cache_hit: bool = False,
                   model_name: str = "unknown",
                   device: str = "unknown"):
        """记录embedding调用"""
        with self.lock:
            self.metrics.total_calls += 1
            self.metrics.total_tokens += tokens
            self.metrics.total_time += duration
            
            if success:
                self.metrics.avg_time_per_call = self.metrics.total_time / self.metrics.total_calls
                self.metrics.avg_tokens_per_call = self.metrics.total_tokens / self.metrics.total_calls
            else:
                self.metrics.error_count += 1
            
            if cache_hit:
                self.metrics.cache_hits += 1
            else:
                self.metrics.cache_misses += 1
            
            # 记录性能历史
            self.performance_history.append({
                'timestamp': time.time(),
                'tokens': tokens,
                'duration': duration,
                'success': success,
                'cache_hit': cache_hit,
                'model_name': model_name,
                'device': device
            })
            
            # 更新系统资源使用情况
            self._update_system_metrics()
    
    def record_error(self, 
                    error_type: str, 
                    error_message: str,
                    model_name: str = "unknown",
                    device: str = "unknown",
                    input_length: int = 0):
        """记录错误"""
        with self.lock:
            error = EmbeddingError(
                timestamp=time.time(),
                error_type=error_type,
                error_message=error_message,
                model_name=model_name,
                device=device,
                input_length=input_length
            )
            self.error_history.append(error)
            self.metrics.error_count += 1
    
    def _update_system_metrics(self):
        """更新系统资源指标"""
        try:
            # 内存使用情况
            process = psutil.Process()
            memory_info = process.memory_info()
            self.metrics.memory_usage_mb = memory_info.rss / 1024 / 1024
            
            # GPU使用情况（已移除 PyTorch 依赖，GPU 监控不再可用）
            # 注意：FastEmbed 使用 ONNX/CPU，不支持 GPU 监控
            self.metrics.gpu_usage_percent = 0.0
                
        except Exception as e:
            logger.warning(f"更新系统指标失败: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        with self.lock:
            uptime = time.time() - self.start_time
            return {
                'uptime_seconds': uptime,
                'total_calls': self.metrics.total_calls,
                'total_tokens': self.metrics.total_tokens,
                'total_time': self.metrics.total_time,
                'avg_time_per_call': self.metrics.avg_time_per_call,
                'avg_tokens_per_call': self.metrics.avg_tokens_per_call,
                'error_count': self.metrics.error_count,
                'error_rate': self.metrics.error_count / max(self.metrics.total_calls, 1),
                'cache_hits': self.metrics.cache_hits,
                'cache_misses': self.metrics.cache_misses,
                'cache_hit_rate': self.metrics.cache_hits / max(self.metrics.cache_hits + self.metrics.cache_misses, 1),
                'memory_usage_mb': self.metrics.memory_usage_mb,
                'gpu_usage_percent': self.metrics.gpu_usage_percent,
                'calls_per_second': self.metrics.total_calls / max(uptime, 1),
                'tokens_per_second': self.metrics.total_tokens / max(uptime, 1)
            }
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的错误"""
        with self.lock:
            recent_errors = list(self.error_history)[-limit:]
            return [
                {
                    'timestamp': error.timestamp,
                    'error_type': error.error_type,
                    'error_message': error.error_message,
                    'model_name': error.model_name,
                    'device': error.device,
                    'input_length': error.input_length
                }
                for error in recent_errors
            ]
    
    def get_performance_trend(self, window_size: int = 100) -> Dict[str, Any]:
        """获取性能趋势"""
        with self.lock:
            recent_performance = list(self.performance_history)[-window_size:]
            if not recent_performance:
                return {}
            
            durations = [p['duration'] for p in recent_performance if p['success']]
            tokens = [p['tokens'] for p in recent_performance if p['success']]
            
            if not durations:
                return {}
            
            return {
                'window_size': len(recent_performance),
                'avg_duration': sum(durations) / len(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'avg_tokens': sum(tokens) / len(tokens),
                'success_rate': sum(1 for p in recent_performance if p['success']) / len(recent_performance)
            }
    
    def reset_metrics(self):
        """重置指标"""
        with self.lock:
            self.metrics = EmbeddingMetrics()
            self.error_history.clear()
            self.performance_history.clear()
            self.start_time = time.time()
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        metrics = self.get_metrics()
        
        # 健康状态评估
        health_score = 100
        
        # 错误率检查
        if metrics['error_rate'] > 0.1:  # 错误率超过10%
            health_score -= 30
        elif metrics['error_rate'] > 0.05:  # 错误率超过5%
            health_score -= 15
        
        # 性能检查
        if metrics['avg_time_per_call'] > 1.0:  # 平均调用时间超过1秒
            health_score -= 20
        elif metrics['avg_time_per_call'] > 0.5:  # 平均调用时间超过0.5秒
            health_score -= 10
        
        # 内存使用检查
        if metrics['memory_usage_mb'] > 1000:  # 内存使用超过1GB
            health_score -= 15
        elif metrics['memory_usage_mb'] > 500:  # 内存使用超过500MB
            health_score -= 5
        
        # 确定健康状态
        if health_score >= 90:
            status = "excellent"
        elif health_score >= 70:
            status = "good"
        elif health_score >= 50:
            status = "fair"
        else:
            status = "poor"
        
        return {
            'health_score': max(0, health_score),
            'status': status,
            'recommendations': self._get_recommendations(metrics)
        }
    
    @staticmethod
    def _get_recommendations(metrics: Dict[str, Any]) -> List[str]:
        """获取优化建议"""
        recommendations = []
        
        if metrics['error_rate'] > 0.05:
            recommendations.append("错误率较高，建议检查模型配置和输入数据")
        
        if metrics['avg_time_per_call'] > 0.5:
            recommendations.append("响应时间较慢，建议优化批处理大小或使用GPU")
        
        if metrics['memory_usage_mb'] > 500:
            recommendations.append("内存使用较高，建议启用缓存或减少批处理大小")
        
        if metrics['cache_hit_rate'] < 0.3:
            recommendations.append("缓存命中率较低，建议优化缓存策略")
        
        return recommendations

# 全局监控器实例
_embedding_monitor = None

def get_embedding_monitor() -> EmbeddingMonitor:
    """获取全局embedding监控器实例"""
    global _embedding_monitor
    if _embedding_monitor is None:
        _embedding_monitor = EmbeddingMonitor()
    return _embedding_monitor
