#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
流式处理器模块
支持大量数据的流式处理和内存优化
"""
import time
import asyncio
import pandas as pd
from utils.utils_core.logger import get_logger
from typing import Generator, List, Dict, Any, Iterable
from utils.utils_config_management.optimization_config import get_optimization_config

logger = get_logger(__name__)


class StreamingCaseProcessor:
    """流式处理大量测试用例"""

    def __init__(self, chunk_size: int = None, max_memory_mb: int = None, data_size: int = 0):
        config = get_optimization_config()
        cfg = config.get_config()

        # 支持动态优化：如果没传 chunk_size，就根据数据量算最优值
        self.chunk_size = chunk_size or config.get_optimal_chunk_size(data_size or cfg['chunk_size'])
        self.max_memory_mb = max_memory_mb or cfg['max_memory_mb']

        self.processed_count = 0
        self.start_time = time.time()

    def process_cases_streaming(
        self, cases_iter: Iterable[Dict]
    ) -> Generator[pd.DataFrame, None, None]:
        """流式处理用例生成器，支持 list 或 generator"""
        try:
            for chunk in self._chunk_generator(cases_iter):
                processed_chunk = self._process_chunk(chunk)
                if not processed_chunk.empty:
                    yield processed_chunk
                    self.processed_count += len(processed_chunk)
                    self._log_progress()
        except Exception as e:
            logger.error(f"流式处理异常: {e}")
            raise

    def _chunk_generator(self, cases: Iterable[Dict]) -> Generator[List[Dict], None, None]:
        """生成数据块"""
        chunk: List[Dict] = []
        for case in cases:
            chunk.append(case)
            if len(chunk) >= self.chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

    @staticmethod
    def _process_chunk(chunk: List[Dict]) -> pd.DataFrame:
        """处理单个数据块"""
        try:
            if not chunk:
                return pd.DataFrame()
            df = pd.DataFrame(chunk)
            # 简单的序号重排，替代原来的CaseNumberManager
            if 'case_id' in df.columns:
                df = df.reset_index(drop=True)
                df['case_id'] = df.apply(lambda x: f"TC-{x.name + 1:03d}", axis=1)
            return df
        except Exception as e:
            logger.error(f"处理数据块异常: {e}")
            return pd.DataFrame()

    def _log_progress(self):
        """记录处理进度"""
        elapsed_time = time.time() - self.start_time
        rate = self.processed_count / elapsed_time if elapsed_time > 0 else 0
        logger.info(f"已处理 {self.processed_count} 个用例，处理速度: {rate:.2f} 用例/秒")

    def get_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        elapsed_time = time.time() - self.start_time
        return {
            'processed_count': self.processed_count,
            'elapsed_time': elapsed_time,
            'processing_rate': self.processed_count / elapsed_time if elapsed_time > 0 else 0,
            'chunk_size': self.chunk_size,
            'max_memory_mb': self.max_memory_mb
        }


class AsyncCaseProcessor:
    """异步用例处理器"""

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def process_cases_async(self, cases_list: List[Dict]) -> List[Dict]:
        """异步处理用例列表"""
        tasks = [self._process_single_case(c) for c in cases_list]
        results: List[Dict] = await asyncio.gather(*tasks)
        return results

    async def _process_single_case(self, case: Dict) -> Dict:
        """异步处理单个用例"""
        async with self.semaphore:
            try:
                await asyncio.sleep(0.01)  # 模拟处理时间
                if isinstance(case.get("steps"), list):
                    case["steps"] = "\n".join(case["steps"])
                if isinstance(case.get("expected"), list):
                    case["expected"] = "\n".join(case["expected"])
                return case
            except Exception as e:
                logger.error(f"异步处理用例异常: {e}")
                return case


class MemoryOptimizedProcessor:
    """内存优化的处理器"""

    def __init__(self, max_memory_mb: int = 500):
        self.max_memory_mb = max_memory_mb
        self.current_memory_usage = 0

    def process_with_memory_limit(self, cases_df: pd.DataFrame) -> Generator[pd.DataFrame, None, None]:
        """在内存限制下处理数据"""
        if len(cases_df) == 0:
            return

        memory_usage = self.get_memory_usage(cases_df)

        if memory_usage > self.max_memory_mb:
            chunk_size = int(len(cases_df) * self.max_memory_mb / memory_usage)
            for i in range(0, len(cases_df), chunk_size):
                chunk = cases_df.iloc[i:i + chunk_size]
                processed_chunk = self._renumber_cases(chunk)
                yield processed_chunk
        else:
            processed_df = self._renumber_cases(cases_df)
            yield processed_df

    @staticmethod
    def _renumber_cases(df: pd.DataFrame) -> pd.DataFrame:
        """重新编号测试用例"""
        try:
            df = df.reset_index(drop=True)
            if 'case_id' in df.columns:
                df['case_id'] = df.apply(lambda x: f"TC-{x.name + 1:03d}", axis=1)
            return df
        except Exception as e:
            logger.error(f"重新编号失败: {e}")
            return df

    @staticmethod
    def get_memory_usage(df: pd.DataFrame) -> float:
        """获取DataFrame内存使用量（MB）"""
        return df.memory_usage(deep=True).sum() / 1024 / 1024
