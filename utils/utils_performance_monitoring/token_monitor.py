#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import time
import tiktoken
from typing import Dict, Optional
from utils.utils_core.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)


class TokenMonitor:
    """增强的Token消耗监控器 - 集成TikToken精确计算"""

    def __init__(self, model_name: str = None):  # 改为None
        if model_name is None:
            model_name = settings.MODEL  # 从配置获取
        self.session_start = time.time()
        self.total_tokens = 0
        self.call_count = 0
        self.max_tokens_per_session = 50000  # 单次会话最大Token限制
        self.max_calls_per_session = 100  # 单次会话最大调用次数

        # 新增：模型名称和TikToken编码器
        self.model_name = model_name
        self.encoding = None
        self._init_encoding()

        # 新增：详细的token统计
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

        # 新增：价格配置（每1K tokens）
        self.input_price = 0.005
        self.output_price = 0.015

    def _init_encoding(self):
        """初始化TikToken编码器"""
        try:
            if "gpt-5" in self.model_name or "gpt-3.5" in self.model_name:
                self.encoding = tiktoken.get_encoding("cl100k_base")
            elif "gpt-3" in self.model_name:
                self.encoding = tiktoken.get_encoding("r50k_base")
            else:
                # 默认使用cl100k_base (GPT-4编码器)
                self.encoding = tiktoken.get_encoding("cl100k_base")
            logger.info(f"TikTokens编码器初始化成功: {self.model_name}")
        except Exception as e:
            logger.warning(f"TikToken编码器初始化失败: {e}")
            self.encoding = None

    def count_tokens(self, text: str) -> int:
        """
        精确计算文本的token数量

        Args:
            text: 输入文本

        Returns:
            token数量
        """
        if not text:
            return 0

        try:
            if self.encoding:
                return len(self.encoding.encode(text))
            else:
                # 回退到估算方法
                return self._estimate_tokens(text)
        except Exception as e:
            logger.warning(f"TikToken计算失败，回退到估算方法: {e}")
            return self._estimate_tokens(text)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """估算文本的token数量（回退方法）"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        other_chars = len(text) - chinese_chars - english_chars

        return int(chinese_chars * 1.5 + english_chars * 0.75 + other_chars * 0.5)

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        计算成本

        Args:
            input_tokens: 输入token数量
            output_tokens: 输出token数量

        Returns:
            总成本
        """
        input_cost = (input_tokens / 1000) * self.input_price
        output_cost = (output_tokens / 1000) * self.output_price
        return input_cost + output_cost

    def record_call(self, estimated_tokens: int = 1000, is_actual: bool = False,
                    input_text: str = "", output_text: str = "",
                    actual_tokens: Optional[Dict] = None):
        """
        记录LLM调用 - 增强版本，保持向后兼容

        Args:
            estimated_tokens: 预估token数量（向后兼容）
            is_actual: 是否为实际token数据（向后兼容）
            input_text: 输入文本（新增）
            output_text: 输出文本（新增）
            actual_tokens: 实际token数据（新增）
        """
        self.call_count += 1

        # 计算token数量
        if actual_tokens:
            # 使用实际token数据
            input_tokens = actual_tokens.get('prompt_tokens', 0)
            output_tokens = actual_tokens.get('completion_tokens', 0)
        elif input_text or output_text:
            # 使用TikToken精确计算
            input_tokens = self.count_tokens(input_text) if input_text else 0
            output_tokens = self.count_tokens(output_text) if output_text else 0
        else:
            # 向后兼容：使用传入的estimated_tokens
            input_tokens = estimated_tokens if is_actual else 0
            output_tokens = 0

        # 计算成本
        cost = self.calculate_cost(input_tokens, output_tokens)

        # 更新统计
        if is_actual or actual_tokens or (input_text or output_text):
            self.total_tokens += input_tokens + output_tokens
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_cost += cost

        # 检查限制（使用实际总计）
        if self.total_tokens > self.max_tokens_per_session:
            raise Exception(f"Token消耗超过限制: {self.total_tokens:,} > {self.max_tokens_per_session:,}")

        if self.call_count > self.max_calls_per_session:
            raise Exception(f"调用次数超过限制: {self.call_count} > {self.max_calls_per_session}")

        # 根据类型显示不同的日志
        if is_actual or actual_tokens or (input_text or output_text):
            logger.info(f"""
 Token统计 - 调用 #{self.call_count}:
   - 输入Token: {input_tokens:,}
   - 输出Token: {output_tokens:,}
   - 本次成本: ${cost:.6f}
   - 累计输入Token: {self.total_input_tokens:,}
   - 累计输出Token: {self.total_output_tokens:,}
   - 累计成本: ${self.total_cost:.6f}
            """)
        else:
            # 预估Token消耗改为debug级别，不显示在INFO日志中
            logger.debug(f"预估Token消耗: {estimated_tokens:,} tokens (总计: {self.total_tokens:,})")

    def get_stats(self) -> Dict:
        """获取统计信息 - 增强版本"""
        session_duration = time.time() - self.session_start
        return {
            "total_tokens": self.total_tokens,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost": self.total_cost,
            "call_count": self.call_count,
            "session_duration": session_duration,
            "tokens_per_minute": self.total_tokens / (session_duration / 60) if session_duration > 0 else 0,
            "average_cost_per_call": self.total_cost / self.call_count if self.call_count > 0 else 0
        }

    def reset(self):
        """重置监控器"""
        self.session_start = time.time()
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.call_count = 0


# 全局监控器实例
_token_monitor = None


def get_token_monitor(model_name: str = None):
    """获取Token监控器 - 支持模型名称参数"""
    if model_name is None:
        model_name = settings.MODEL  # 从配置获取
    global _token_monitor
    if _token_monitor is None or _token_monitor.model_name != model_name:
        _token_monitor = TokenMonitor(model_name)
    return _token_monitor


def record_llm_call(estimated_tokens: int = 1000, is_actual: bool = False,
                    input_text: str = "", output_text: str = "",
                    actual_tokens: Optional[Dict] = None, model_name: str = None):
    if model_name is None:
        model_name = settings.MODEL
    """
    记录LLM调用 - 增强版本，保持向后兼容

    Args:
        estimated_tokens: 预估token数量（向后兼容）
        is_actual: 是否为实际token数据（向后兼容）
        input_text: 输入文本（新增）
        output_text: 输出文本（新增）
        actual_tokens: 实际token数据（新增）
        model_name: 模型名称（新增）
    """
    monitor = get_token_monitor(model_name)
    monitor.record_call(estimated_tokens, is_actual, input_text, output_text, actual_tokens)


def count_tokens(text: str, model_name: str = None) -> int:
    if model_name is None:
        model_name = settings.MODEL
    monitor = get_token_monitor(model_name)
    return monitor.count_tokens(text)