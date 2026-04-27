#!/usr/bin/python
# -*- coding: utf-8 -*-
import time
import pandas as pd
import concurrent.futures
from typing import List, Dict
from utils.utils_ai_models.get_llm import get_llm
from utils.utils_core.logger import get_logger
from config.settings import settings
from pilotAgent.pilotAgent import TestAgent
from utils.utils_core.common_utils import CaseNumberManager
from utils.utils_core.json_utils import safe_json_loads
from utils.utils_config_management.optimization_config import get_optimization_config
from utils.utils_performance_monitoring.performance_monitor import get_performance_monitor

logger = get_logger(__name__)


class OptimizedBatchProcessor:
    """优化的批次处理器"""

    def __init__(self):
        # 修改：不再创建共享的agent实例，改为存储LLM实例
        self.llm = get_llm(settings.COMPANY)  # 获取共享的LLM实例
        self.processed_cases = pd.DataFrame()
        self.batch_results = []
        self.global_case_counter = 0
        self.config = get_optimization_config()

    def process_batch_parallel(self, batch_plan: Dict, batch_index: int = 0) -> Dict:
        """并行处理单个批次"""
        monitor = get_performance_monitor()

        # 启动性能监控
        monitor.start_monitoring()

        try:
            logger.info(f"开始并行处理批次 {batch_plan['batch_id']}: {batch_plan['description']}")

            modules = batch_plan['modules']
            workers = self.config.get_optimal_workers(len(modules))  # 自适应线程数

            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_module = {
                    executor.submit(self._generate_module_cases, module, batch_index): module
                    for module in modules
                }

                results = []
                for future in concurrent.futures.as_completed(future_to_module):
                    module = future_to_module[future]
                    try:
                        result = future.result()
                        if not result.empty:
                            results.append(result)
                            logger.info(f"模块 {module.get('name')} 处理完成: {len(result)} 个用例")
                    except Exception as e:
                        logger.error(f"模块 {module.get('name')} 处理失败: {e}")

            if results:
                batch_cases = pd.concat(results, ignore_index=True)
                batch_cases = CaseNumberManager.renumber_cases_for_batch(batch_cases, batch_index)

                # 更新处理数量
                monitor.update_processed_count(len(batch_cases))

                result = {
                    'success': True,
                    'cases': batch_cases,
                    'error': None,
                    'batch_info': {
                        'batch_id': batch_plan['batch_id'],
                        'modules_count': len(modules),
                        'cases_count': len(batch_cases),
                        'processing_time': time.time()
                    }
                }
                logger.info(f"批次 {batch_plan['batch_id']} 并行处理完成: {len(batch_cases)}个用例")

            else:
                result = {'success': False, 'cases': pd.DataFrame(), 'error': '所有模块处理失败'}

        except Exception as e:
            logger.error(f"批次处理异常: {e}")
            result = {'success': False, 'cases': pd.DataFrame(), 'error': str(e)}

        finally:
            # 停止性能监控
            monitor.stop_monitoring()

        # 在 finally 块之后返回结果
        return result

    def _generate_module_cases(self, module: Dict, batch_index: int) -> pd.DataFrame:
        """生成单个模块的测试用例（多线程安全版本）"""
        try:
            # 修改：为每个线程创建独立的TestAgent实例
            agent = TestAgent(llm=self.llm)  # 使用共享的LLM实例，但独立的agent实例

            module_prompt = self._build_module_prompt(module, batch_index)
            response = agent.generate_test_cases(module_prompt)

            if isinstance(response, str):
                response = safe_json_loads(response)

            if isinstance(response, dict) and "cases" in response:
                cases = response["cases"]

                for c in cases:
                    if isinstance(c.get("steps"), list):
                        # 保持序号格式
                        numbered_steps = []
                        for i, step in enumerate(c["steps"], 1):
                            step_str = str(step).strip()
                            if step_str.startswith(f"{i}.") or step_str.startswith(f"{i}、"):
                                numbered_steps.append(step_str)
                            else:
                                numbered_steps.append(f"{i}. {step_str}")
                        c["steps"] = "\n".join(numbered_steps)

                    if isinstance(c.get("expected"), list):
                        # 保持序号格式
                        numbered_expected = []
                        for i, expected in enumerate(c["expected"], 1):
                            expected_str = str(expected).strip()
                            if expected_str.startswith(f"{i}.") or expected_str.startswith(f"{i}、"):
                                numbered_expected.append(expected_str)
                            else:
                                numbered_expected.append(f"{i}. {expected_str}")
                        c["expected"] = "\n".join(numbered_expected)

                df = pd.DataFrame(cases)
                df.rename(columns={
                    "case_id": "用例编号",
                    "module": "功能模块",
                    "title": "标题",
                    "preconditions": "前置条件",
                    "priority": "优先级",
                    "steps": "测试步骤",
                    "expected": "预期结果",
                    "test_type": "测试类型",
                    "test_method": "测试方法"
                }, inplace=True)

                df['批次ID'] = batch_index + 1
                df['模块名称'] = module.get("name", "未知模块")
                return df
            else:
                logger.warning(f"模块 {module.get('name')} 未生成有效测试用例: {response}")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"模块 {module.get('name')} 测试用例生成失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def _build_module_prompt(module: Dict, batch_index: int) -> str:
        """构建模块提示词，包含描述信息"""
        name = module.get("name", "未知模块")
        desc = module.get("description", "")

        # 使用下划线前缀表示未使用的参数
        _ = batch_index  # 明确表示这个参数未使用

        prompt = f"""
        请为以下功能模块生成测试用例：

        模块名称：{name}
        模块描述：{desc}

        请生成详细的测试用例，包括：
        - 正常流程测试
        - 边界值测试
        - 异常情况测试
        - 性能测试（如适用）

        要求：
        - 测试用例要全面覆盖功能点
        - 每个测试用例都要有明确的预期结果
        - 测试步骤要清晰可执行
        - 确保测试用例的完整性和实用性
        """
        return prompt

    def process_all_batches_parallel(self, batch_plans: List[Dict]) -> Dict:
        """并行处理所有批次"""
        logger.info(f"开始并行处理 {len(batch_plans)} 个批次")

        all_cases = pd.DataFrame()
        batch_results = []
        workers = self.config.get_optimal_workers(len(batch_plans))  # 自适应线程数

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_batch = {
                executor.submit(self.process_batch_parallel, batch_plan, i): (batch_plan, i)
                for i, batch_plan in enumerate(batch_plans)
            }

            for future in concurrent.futures.as_completed(future_to_batch):
                batch_plan, batch_index = future_to_batch[future]
                try:
                    result = future.result()
                    batch_results.append(result)

                    if result['success']:
                        all_cases = pd.concat([all_cases, result['cases']], ignore_index=True)
                        logger.info(f"批次 {batch_plan['batch_id']} 完成")
                    else:
                        logger.error(f"批次 {batch_plan['batch_id']} 失败: {result['error']}")
                except Exception as e:
                    logger.error(f"批次 {batch_plan['batch_id']} 处理异常: {e}")

        return {
            'success': len(batch_results) > 0 and any(r['success'] for r in batch_results),
            'total_cases': len(all_cases),
            'total_batches': len(batch_plans),
            'successful_batches': sum(1 for r in batch_results if r['success']),
            'failed_batches': sum(1 for r in batch_results if not r['success']),
            'cases': all_cases,
            'batch_results': batch_results
        }


class BatchProcessor(OptimizedBatchProcessor):
    """向后兼容的批次处理器"""
    pass