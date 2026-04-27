#!/usr/bin/python
# -*- coding: utf-8 -*-
from typing import Dict
import json
import re
from utils.utils_core.logger import get_logger
from config.settings import settings
from models.models import FunctionCaseList
from concurrent.futures import ThreadPoolExecutor
from langchain_core.prompts import PromptTemplate
from utils.utils_business_logic.complexity_scorer import ComplexityScorer
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableLambda
from utils.utils_performance_monitoring.token_monitor import record_llm_call,count_tokens
from utils.utils_performance_monitoring.performance_monitor import get_performance_monitor
from utils.utils_core.api_error_handler import normalize_provider_error



logger = get_logger(__name__)


class OptimizedCaseGenerator:
    """优化的测试用例生成器"""

    def __init__(self, llm):
        self.llm = llm
        self.parser = JsonOutputParser(pydantic_object=FunctionCaseList)
        # 初始化复杂度评分器
        self.complexity_scorer = ComplexityScorer.from_knowledge_base()
        
        # 使用自定义的简短格式说明，替代 LangChain 自动生成的长 prompt
        # 减少 token 消耗，同时保持格式要求清晰
        self.custom_format_instructions = """请严格按照以下JSON格式返回，不要添加任何解释文字或Markdown代码块：

{
  "cases": [
    {
      "case_id": "TC-模块-序号",
      "module": "功能模块",
      "title": "用例标题",
      "preconditions": "前置条件",
      "steps": ["步骤1", "步骤2"],
      "expected": ["结果1", "结果2"],
      "priority": "P0|P1|P2|P3|P4",
      "test_type": "测试类型",
      "test_method": "测试方法",
      "tags": ["标签1", "标签2"]
    }
  ]
}"""
        
        self._build_chains()

    def _build_chains(self):
        """预构建链式结构，避免重复构建"""
        prompt_with_language = settings.FUNCTION_PROMPT + "\n\n语言输出要求：{language_instruction}\n"
        rag_prompt_with_language = settings.FUNCTION_PROMPT_RAG + "\n\n语言输出要求：{language_instruction}\n"

        def extract_tokens_and_parse(response):
            """提取Token信息并继续解析"""
            # 获取Token信息
            if hasattr(response, 'response_metadata'):
                token_usage = response.response_metadata.get('token_usage', {})
                if token_usage:
                    input_tokens = token_usage.get('prompt_tokens', 0)
                    output_tokens = token_usage.get('completion_tokens', 0)
                    total_tokens = token_usage.get('total_tokens', 0)

                    # 从completion_tokens_details中获取思考Token
                    completion_details = token_usage.get('completion_tokens_details', {})
                    reasoning_tokens = completion_details.get('reasoning_tokens', 0)

                    logger.info(f"📊 实际Tokens消耗详情:")
                    logger.info(f"   输入Tokens消耗: {input_tokens}")
                    logger.info(f"   输出Tokens消耗: {output_tokens}")
                    logger.info(f"   思考Tokens消耗: {reasoning_tokens}")
                    logger.info(f"   总体Tokens消耗: {total_tokens}")

                    if total_tokens > 0:
                        record_llm_call(total_tokens, is_actual=True)

            # 继续解析
            return self.parser.invoke(response)

        # 标准链 - 在LLM和Parser之间插入Token提取
        # 使用 RunnableLambda 包装函数以符合 Runnable 类型要求
        self.standard_chain = (
                PromptTemplate.from_template(prompt_with_language)
                .partial(
                    format_instructions=self.custom_format_instructions,
                    max_case_nums=settings.MAX_CASE_NUM
                )
                | self.llm
                | RunnableLambda(extract_tokens_and_parse)
        )

        # RAG链 - 同样处理
        self.rag_chain = (
                PromptTemplate.from_template(rag_prompt_with_language)
                .partial(
                    format_instructions=self.custom_format_instructions,
                    max_case_nums=settings.MAX_CASE_NUM
                )
                | self.llm
                | RunnableLambda(extract_tokens_and_parse)
        )

    def _get_enhanced_context(self, requirement: str) -> Dict:
        """获取增强的上下文信息"""
        # 分析需求风险
        risk_analysis = self.complexity_scorer.analyze_requirement_risks(requirement)

        # 获取建议的测试类型和方法
        suggested_test_types = self.complexity_scorer.get_risk_based_test_types(risk_analysis["overall_risk"])
        suggested_methods = self.complexity_scorer.get_risk_based_test_methods(risk_analysis["overall_risk"])

        # 构建复杂度分析文本
        complexity_text = f"""
- 总体风险等级: {risk_analysis['overall_risk']}
- 平台风险: {[p['platform'] + '(' + p['risk'] + ')' for p in risk_analysis['platform_risks']]}
- 应用类型风险: {[a['category'] + '(' + a['risk'] + ')' for a in risk_analysis['application_risks']]}
- 功能风险: {[f['function'] + '(' + f['risk'] + ')' for f in risk_analysis['functional_risks']]}
"""

        return {
            "complexity_analysis": complexity_text,
            "suggested_test_types": ', '.join(suggested_test_types) if suggested_test_types else '功能测试',
            "suggested_methods": ', '.join(suggested_methods) if suggested_methods else '等价类划分法'
        }

    def generate_cases(self, requirement, retriever=None, is_rag=False):
        """生成测试用例 - 在现有基础上增强"""
        try:
            zh_count = sum(1 for ch in (requirement or '') if '\u4e00' <= ch <= '\u9fff')
            en_count = sum(1 for ch in (requirement or '') if ('a' <= ch.lower() <= 'z'))
            if zh_count > en_count:
                language_instruction = "请使用简体中文输出测试用例内容（字段名保持英文）。"
            elif en_count > zh_count:
                language_instruction = "Please output test case content in English (field names remain in English)."
            else:
                language_instruction = "请跟随用户输入主体语言输出测试用例内容（字段名保持英文）。"

            # 获取增强的上下文信息
            enhanced_context = self._get_enhanced_context(requirement)

            if is_rag and retriever:
                # 使用RAG链，传入增强的上下文
                chain_input = {
                    "context": retriever,
                    "requirement": requirement,
                    "language_instruction": language_instruction,
                    "complexity_analysis": enhanced_context["complexity_analysis"],
                    "suggested_test_types": enhanced_context["suggested_test_types"],
                    "suggested_methods": enhanced_context["suggested_methods"]
                }
                result = self.rag_chain.invoke(chain_input)
            else:
                # 使用标准链，传入增强的上下文
                chain_input = {
                    "requirement": requirement,
                    "language_instruction": language_instruction,
                    "complexity_analysis": enhanced_context["complexity_analysis"],
                    "suggested_test_types": enhanced_context["suggested_test_types"],
                    "suggested_methods": enhanced_context["suggested_methods"]
                }
                # 修改 utils/function_cases.py 第115-140行
                result = self.standard_chain.invoke(chain_input)

            logger.debug(f"测试用例生成完成: {len(result.get('cases', []))} 个用例")
            cases_list = result["cases"]
            cases_list = self._normalize_cases_language(cases_list, language_instruction)

            # 优化数据处理
            for case in cases_list:
                if isinstance(case.get("steps"), list):
                    # 保持序号格式，确保每个步骤都有正确的序号
                    numbered_steps = []
                    for i, step in enumerate(case["steps"], 1):
                        step_str = str(step).strip()
                        # 如果步骤已经有序号，保持原样；否则添加序号
                        if step_str.startswith(f"{i}.") or step_str.startswith(f"{i}、"):
                            numbered_steps.append(step_str)
                        else:
                            numbered_steps.append(f"{i}. {step_str}")
                    case["steps"] = "\n".join(numbered_steps)

                if isinstance(case.get("expected"), list):
                    # 保持序号格式，确保每个预期结果都有正确的序号
                    numbered_expected = []
                    for i, expected in enumerate(case["expected"], 1):
                        expected_str = str(expected).strip()
                        # 如果预期结果已经有序号，保持原样；否则添加序号
                        if expected_str.startswith(f"{i}.") or expected_str.startswith(f"{i}、"):
                            numbered_expected.append(expected_str)
                        else:
                            numbered_expected.append(f"{i}. {expected_str}")
                    case["expected"] = "\n".join(numbered_expected)

            return cases_list
        except Exception as e:
            normalized = normalize_provider_error(getattr(settings, 'DEFAULT_COMPANY', 'OPENAI'), e)
            logger.error(f"测试用例生成失败: {normalized.get('message')}")
            raise RuntimeError(normalized.get('message', '测试用例生成失败')) from e

    def _normalize_cases_language(self, cases_list, language_instruction: str):
        if not isinstance(cases_list, list) or not cases_list:
            return cases_list
        target_language = self._target_language_from_instruction(language_instruction)
        raw_text = json.dumps(cases_list, ensure_ascii=False)
        if not self._needs_rewrite(raw_text, target_language):
            return cases_list

        if target_language == "zh":
            language_rule = "请将测试用例中的可读文本字段改写为简体中文。"
        elif target_language == "en":
            language_rule = "Please rewrite human-readable test case fields in English."
        else:
            return cases_list

        rewrite_prompt = f"""
你将收到一个 JSON 数组，请仅改写字段值语言，不要改字段名、结构、顺序与数量。
{language_rule}
返回必须是合法 JSON 数组，不要输出解释。

JSON:
{raw_text}
"""
        try:
            rewritten = self.llm.invoke(rewrite_prompt)
            rewritten_text = rewritten.content if hasattr(rewritten, "content") else str(rewritten)
            match = re.search(r'\[.*]', rewritten_text, re.DOTALL)
            if not match:
                return cases_list
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                return parsed
            return cases_list
        except Exception as e:
            logger.warning(f"用例语言兜底改写失败，使用原始输出: {e}")
            return cases_list

    @staticmethod
    def _target_language_from_instruction(instruction: str) -> str:
        text = instruction or ""
        if "English" in text or "english" in text:
            return "en"
        if "简体中文" in text or "中文" in text:
            return "zh"
        return "auto"

    @staticmethod
    def _needs_rewrite(text: str, target_language: str) -> bool:
        if target_language == "auto":
            return False
        zh_count = len(re.findall(r'[\u4e00-\u9fff]', text or ""))
        en_count = len(re.findall(r'[A-Za-z]', text or ""))
        if target_language == "zh":
            return en_count > max(zh_count * 2, 30)
        return zh_count > max(en_count * 2, 15)

    def generate_cases_batch(self, requirements, max_workers=3):
        """批量生成测试用例 - 添加安全限制"""
        # 添加批量处理限制
        max_batch_size = 20  # 最大批量处理数量
        if len(requirements) > max_batch_size:
            logger.info(f"批量处理数量超过限制，将分批处理")
            # 分批处理
            results = []
            for i in range(0, len(requirements), max_batch_size):
                batch = requirements[i:i + max_batch_size]
                batch_results = self._process_batch_safely(batch, max_workers)
                results.extend(batch_results)
            return results

        return self._process_batch_safely(requirements, max_workers)

    def _process_batch_safely(self, requirements, max_workers):
        """安全批量处理 - 多线程安全版本"""
        monitor = get_performance_monitor()

        # 启动性能监控
        monitor.start_monitoring()
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []

                # 添加 token 消耗监控
                total_tokens = 0
                for req in requirements:
                    est_tokens = count_tokens(str(req))
                    total_tokens += est_tokens

                if total_tokens > 10000:  # 如果预估超过 10000 tokens
                    logger.debug(f"批量处理预估 token 消耗: {total_tokens:,} tokens")

                for req in requirements:
                    # 修改：为每个线程创建独立的生成器实例
                    future = executor.submit(self._generate_cases_safe, req)
                    futures.append(future)

                results = []
                for future in futures:
                    try:
                        result = future.result(timeout=60)  # 添加超时限制
                        results.extend(result)
                    except Exception as e:
                        logger.error(f"批量生成失败: {type(e).__name__}")
                        continue

                # 更新处理数量
                monitor.update_processed_count(len(results))

        finally:
            # 停止性能监控
            monitor.stop_monitoring()

        # 在 finally 块之后返回结果
        return results

    def _generate_cases_safe(self, requirement):
        """线程安全的测试用例生成"""
        try:
            # 为每个线程创建独立的生成器实例，传入LLM参数
            generator = OptimizedCaseGenerator(llm=self.llm)
            return generator.generate_cases(requirement)
        except Exception as e:
            normalized = normalize_provider_error(getattr(settings, 'DEFAULT_COMPANY', 'OPENAI'), e)
            logger.error(f"测试用例生成失败: {normalized.get('message')}")
            raise RuntimeError(normalized.get('message', '测试用例生成失败')) from e


# 全局生成器实例
_case_generator = None


def get_case_generator(llm):
    """获取用例生成器实例（单例模式）"""
    global _case_generator
    if _case_generator is None:
        _case_generator = OptimizedCaseGenerator(llm)
    return _case_generator


def generate_function_cases(llm, requirement, retriever=None, is_rag=False):
    """兼容性函数，保持原有接口"""
    generator = get_case_generator(llm)
    return generator.generate_cases(requirement, retriever, is_rag)


def generate_cases_batch(llm, requirements, max_workers=3):
    """批量生成接口"""
    generator = get_case_generator(llm)
    return generator.generate_cases_batch(requirements, max_workers)

if __name__ == "__main__":
    pass
