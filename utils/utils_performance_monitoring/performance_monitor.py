#!/usr/bin/python
# -*- coding: utf-8 -*-
import time
import psutil
import threading
from datetime import datetime,timezone
from typing import Dict, Any, List
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.lock = threading.Lock()
        self.start_time = time.time()
        self.processed_count = 0
        self.memory_usage_history = []
        self.cpu_usage_history = []
        self.monitoring = False
        self.monitor_thread = None

    def start_monitoring(self, interval: float = 1.0):
        """开始性能监控"""
        self.monitoring = True
        self.start_time = time.time()
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("性能监控已启动")

    def stop_monitoring(self):
        """停止性能监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        logger.info("性能监控已停止")

    @staticmethod
    def start_timer() -> float:
        """开始计时，返回开始时间"""
        return time.time()

    @staticmethod
    def end_timer(start_time: float) -> float:
        """结束计时，返回耗时（秒）"""
        return time.time() - start_time

    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.monitoring:
            try:
                # 记录内存使用
                memory_percent = psutil.virtual_memory().percent
                self.memory_usage_history.append(memory_percent)

                # 记录CPU使用
                cpu_percent = psutil.cpu_percent()
                self.cpu_usage_history.append(cpu_percent)

                # 保持历史记录在合理范围内
                if len(self.memory_usage_history) > 100:
                    self.memory_usage_history = self.memory_usage_history[-50:]
                if len(self.cpu_usage_history) > 100:
                    self.cpu_usage_history = self.cpu_usage_history[-50:]

                time.sleep(interval)
            except Exception as e:
                logger.error(f"性能监控异常: {e}")
                break

    def update_processed_count(self, count: int):
        """更新处理计数 - 线程安全版本"""
        with self.lock:
            self.processed_count += count

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        elapsed_time = time.time() - self.start_time
        processing_rate = self.processed_count / elapsed_time if elapsed_time > 0 else 0

        avg_memory = sum(self.memory_usage_history) / len(self.memory_usage_history) if self.memory_usage_history else 0
        avg_cpu = sum(self.cpu_usage_history) / len(self.cpu_usage_history) if self.cpu_usage_history else 0

        return {
            'elapsed_time': elapsed_time,
            'processed_count': self.processed_count,
            'processing_rate': processing_rate,
            'avg_memory_usage': avg_memory,
            'avg_cpu_usage': avg_cpu,
            'max_memory_usage': max(self.memory_usage_history) if self.memory_usage_history else 0,
            'max_cpu_usage': max(self.cpu_usage_history) if self.cpu_usage_history else 0
        }

    def log_performance_summary(self):
        """记录性能摘要"""
        stats = self.get_performance_stats()
        logger.info(f"""
        📊   性能摘要:
            - 处理时间: {stats['elapsed_time']:.2f} 秒
            - 处理数量: {stats['processed_count']} 个用例
            - 处理速度: {stats['processing_rate']:.2f} 用例/秒
            - 平均内存使用: {stats['avg_memory_usage']:.2f}%
            - 平均CPU使用: {stats['avg_cpu_usage']:.2f}%
            - 峰值内存使用: {stats['max_memory_usage']:.2f}%
            - 峰值CPU使用: {stats['max_cpu_usage']:.2f}%
        """)

    # 新增：性能指标分析相关方法
    @staticmethod
    def calculate_performance_summary(metrics: List[Any]) -> Dict[str, float]:
        """计算性能汇总统计"""
        if not metrics:
            return {
                'avg_response_time': 0.0,
                'min_response_time': 0.0,
                'max_response_time': 0.0,
                'p95_response_time': 0.0,
                'p99_response_time': 0.0,
                'success_rate': 100.0,
                'error_rate': 0.0,
                'requests_per_minute': 0.0,
                'avg_memory_usage': 0.0,
                'avg_cpu_usage': 0.0
            }

        # 使用getattr安全访问属性
        response_times = [getattr(m, 'response_time', 0) for m in metrics]
        response_times.sort()

        total_requests = len(metrics)
        error_count = sum(1 for m in metrics if getattr(m, 'status_code', 0) >= 400)

        # 计算百分位数
        p95_index = int(total_requests * 0.95)
        p99_index = int(total_requests * 0.99)

        # 计算时间范围内的请求频率
        first_timestamp = getattr(metrics[0], 'timestamp', datetime.now(timezone.utc))
        last_timestamp = getattr(metrics[-1], 'timestamp', datetime.now(timezone.utc))
        time_span = (last_timestamp - first_timestamp).total_seconds() / 60
        requests_per_minute = total_requests / time_span if time_span > 0 else 0

        return {
            'avg_response_time': sum(response_times) / total_requests,
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'p95_response_time': response_times[p95_index] if p95_index < total_requests else max(response_times),
            'p99_response_time': response_times[p99_index] if p99_index < total_requests else max(response_times),
            'success_rate': ((total_requests - error_count) / total_requests) * 100,
            'error_rate': (error_count / total_requests) * 100,
            'requests_per_minute': requests_per_minute,
            'avg_memory_usage': sum(getattr(m, 'memory_usage', 0) for m in metrics) / total_requests,
            'avg_cpu_usage': sum(getattr(m, 'cpu_usage', 0) for m in metrics) / total_requests
        }

    @staticmethod
    def generate_performance_timeline(metrics: List[Any]) -> List[Dict]:
        """生成性能时间线数据"""
        if not metrics:
            return []

        # 按小时分组
        hourly_data = {}
        for metric in metrics:
            timestamp = getattr(metric, 'timestamp', datetime.now(timezone.utc))
            hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
            if hour_key not in hourly_data:
                hourly_data[hour_key] = []
            hourly_data[hour_key].append(metric)

        timeline = []
        for hour, hour_metrics in sorted(hourly_data.items()):
            response_times = [getattr(m, 'response_time', 0) for m in hour_metrics]
            error_count = sum(1 for m in hour_metrics if getattr(m, 'status_code', 0) >= 400)

            timeline.append({
                'timestamp': hour.isoformat(),
                'requests': len(hour_metrics),
                'avg_response_time': sum(response_times) / len(response_times),
                'error_count': error_count,
                'error_rate': (error_count / len(hour_metrics)) * 100,
                'avg_memory_usage': sum(getattr(m, 'memory_usage', 0) for m in hour_metrics) / len(hour_metrics),
                'avg_cpu_usage': sum(getattr(m, 'cpu_usage', 0) for m in hour_metrics) / len(hour_metrics)
            })

        return timeline

    @staticmethod
    def analyze_endpoint_performance(metrics: List[Any]) -> Dict[str, Dict]:
        """分析端点性能"""
        endpoint_data = {}

        for metric in metrics:
            endpoint = getattr(metric, 'endpoint', 'unknown') or 'unknown'
            if endpoint not in endpoint_data:
                endpoint_data[endpoint] = []
            endpoint_data[endpoint].append(metric)

        endpoint_stats = {}
        for endpoint, endpoint_metrics in endpoint_data.items():
            response_times = [getattr(m, 'response_time', 0) for m in endpoint_metrics]
            error_count = sum(1 for m in endpoint_metrics if getattr(m, 'status_code', 0) >= 400)
            total_requests = len(endpoint_metrics)

            endpoint_stats[endpoint] = {
                'total_requests': total_requests,
                'avg_response_time': sum(response_times) / total_requests,
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'error_count': error_count,
                'error_rate': (error_count / total_requests) * 100,
                'success_rate': ((total_requests - error_count) / total_requests) * 100
            }

        return endpoint_stats

    @staticmethod
    def get_empty_performance_summary() -> Dict[str, float]:
        """获取空的性能汇总"""
        return {
            'avg_response_time': 0.0,
            'min_response_time': 0.0,
            'max_response_time': 0.0,
            'p95_response_time': 0.0,
            'p99_response_time': 0.0,
            'success_rate': 100.0,
            'error_rate': 0.0,
            'requests_per_minute': 0.0,
            'avg_memory_usage': 0.0,
            'avg_cpu_usage': 0.0
        }


# 全局性能监控器
_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器实例（单例模式）"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor