#!/usr/bin/python
# -*- coding: utf-8 -*-
import time
import datetime
import concurrent.futures
import importlib
from typing import Optional, Dict, Any, Callable, Protocol, cast
from config.settings import settings
from utils.utils_core.logger import get_logger
from models.models import AgentFunctionCaseList
# 修复导入路径（兼容 langchain 0.3.x）
_ToolCtor = Callable[..., Any]


class _AgentExecutorInstance(Protocol):
    def invoke(self, input_data: Any) -> Any:
        ...


class _AgentExecutorCtor(Protocol):
    def __call__(
        self,
        *,
        agent: Any,
        tools: Any,
        memory: Any,
        verbose: bool,
        handle_parsing_errors: bool,
        max_iterations: int,
        max_execution_time: int,
        return_intermediate_steps: bool
    ) -> _AgentExecutorInstance:
        ...


def _fallback_tool(*, name: str, func: Callable[..., Any], description: str) -> Dict[str, Any]:
    return {"name": name, "func": func, "description": description}


class _FallbackAgentExecutor:
    def __init__(self, **_: Any):
        pass

    def invoke(self, input_data: Any) -> Any:
        raise RuntimeError(f"AgentExecutor unavailable for input: {input_data}")


Tool: _ToolCtor = _fallback_tool
for module_name, attr_name in (
    ("langchain_core.tools", "Tool"),
    ("langchain.tools", "Tool"),
    ("langchain.agents", "Tool"),
):
    try:
        Tool = cast(_ToolCtor, getattr(importlib.import_module(module_name), attr_name))
        break
    except (ImportError, AttributeError):
        continue

AgentExecutor: _AgentExecutorCtor = cast(_AgentExecutorCtor, _FallbackAgentExecutor)
for module_name, attr_name in (
    ("langchain.agents", "AgentExecutor"),
    ("langchain_core.agents", "AgentExecutor"),
    ("langchain.agents.agent", "AgentExecutor"),
):
    try:
        AgentExecutor = cast(_AgentExecutorCtor, getattr(importlib.import_module(module_name), attr_name))
        break
    except (ImportError, AttributeError):
        continue

from utils.utils_ai_models.get_llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from utils.utils_core.json_utils import safe_json_loads

from langchain_core.chat_history import InMemoryChatMessageHistory
from utils.utils_ai_models.embeddings import create_vector_db
from utils.utils_business_logic.complexity_scorer import ComplexityScorer

try:
    from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser  # type: ignore
except ImportError:
    try:
        from langchain_core.agents.output_parsers import OpenAIFunctionsAgentOutputParser  # type: ignore
    except ImportError:
        try:
            from langchain.agents.openai_functions_agent.base import OpenAIFunctionsAgentOutputParser  # type: ignore
        except ImportError:
            from langchain.agents.output_parsers.openai_functions import OpenAIFunctionsAgentOutputParser  # type: ignore
from utils.utils_performance_monitoring.token_monitor import record_llm_call, count_tokens


logger = get_logger(__name__)

__all__ = [
    "TestAgent",
    "knowledge_retrieval",
    "Tool",
    "AgentExecutor",
]


def knowledge_retrieval(retriever, query):
    """测试工具  上传到RAG的知识库 CSV格式：用例ID,用例标题,用例描述,前置条件,测试步骤,预期结果,优先级,模块,标签（Sentence-Transformers优化）"""
    try:
        # 记录开始时间
        start_time = time.time()
        
        docs = retriever.invoke(query)
        search_duration = time.time() - start_time
        
        # 记录embedding性能指标
        try:
            from utils.utils_ai_models.embedding_monitor import get_embedding_monitor
            embedding_monitor = get_embedding_monitor()
            embedding_monitor.record_call(
                tokens=len(query.split()),
                duration=search_duration,
                success=True,
                cache_hit=False,
                model_name="sentence-transformers",
                device="auto"
            )
        except Exception as monitor_error:
            logger.debug(f"记录embedding性能指标失败: {monitor_error}")
        
        if docs:
            return f"知识库检索结果：\n{chr(10).join([doc.page_content for doc in docs])}"
        else:
            return "知识库中未找到相关信息"
    except Exception as e:
        logger.error(f"知识库检索失败: {e}")
        return "知识库检索失败"


class _WindowChatMemory:
    """保留最近 10 轮对话。"""

    def __init__(self) -> None:
        self.k = 10
        self.return_messages = True
        self.memory_key = "history"
        self.chat_memory = InMemoryChatMessageHistory()

    def clear(self) -> None:
        self.chat_memory.clear()

    @property
    def memory_variables(self) -> list[str]:
        return [self.memory_key]

    def load_memory_variables(self, _inputs: Dict[str, Any]) -> Dict[str, Any]:
        messages = self.chat_memory.messages[-self.k * 2:] if self.k > 0 else []
        return {self.memory_key: messages}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        self.chat_memory.add_user_message(str(inputs.get("input", "")))
        self.chat_memory.add_ai_message(str(outputs.get("output", "")))


class TestAgent:
    # 添加类变量
    TIMEOUT_SECONDS = 120  # 超时时间（秒）

    def __init__(self, llm=None):
        # 如果传入了LLM实例，使用传入的；否则创建新的
        self.llm = llm if llm is not None else self._init_llm(settings.COMPANY)
        self.memory = self._init_memory()
        self.retriever = self._init_retriever()
        self.tools = self._init_tools()
        self.output_parser = self._output_parser()
        self.agent_executor: _AgentExecutorInstance = self._build_agent_chain()

    @staticmethod
    def _init_llm(company):
        return get_llm(company)

    @staticmethod
    def _init_memory() -> _WindowChatMemory:
        return _WindowChatMemory()

    @staticmethod
    def _init_retriever():
        return create_vector_db().as_retriever(search_kwargs={"k": 2})

    def _init_tools(self):
        tools = []
        if self.retriever:
            tools.append(Tool(
                name="TestKnowledgeBase",
                func=lambda query: knowledge_retrieval(self.retriever, query),
                description="""
        访问测试知识库获取历史用例，输入应为自然语言查询，例如：
        '登录功能的边界测试场景'
        """))
        return tools

    def _build_agent_chain(self) -> _AgentExecutorInstance:
        """构建 Agent 链 - 添加重试限制"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            ("placeholder", "{history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])

        # 使用 RunnableLambda 构建链，修复类型问题
        def format_input(x):
            return {
                "input": x.get("input", ""),
                "history": x.get("history", []),
                "agent_scratchpad": x.get("intermediate_steps", [])
            }
        
        agent_chain = (
            RunnableLambda(format_input) 
            | prompt 
            | self.llm 
            | self.output_parser
        )

        return AgentExecutor(
            agent=agent_chain,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,  # 最大迭代次数限制
            max_execution_time=120,  # 最大执行时间限制（2分钟）
            return_intermediate_steps=True  # 返回中间步骤，便于调试
        )

    def safe_invoke(self, input_data):
        """安全的 Agent 调用 - 添加重试限制"""
        max_retries = 3
        retry_count = 0

        input_text = str(input_data)
        estimated_tokens = count_tokens(input_text)
        record_llm_call(estimated_tokens, is_actual=True, input_text=input_text)

        while retry_count < max_retries:
            try:
                result = self.agent_executor.invoke(input_data)
                return result
            except Exception as e:
                retry_count += 1
                logger.warning(f"Agent 调用失败，重试 {retry_count}/{max_retries}: {e}")
                if retry_count >= max_retries:
                    logger.error(f"Agent 调用失败，已达到最大重试次数: {e}")
                    raise
                time.sleep(1)  # 等待 1 秒后重试

        return None

    @staticmethod
    def _get_system_prompt():
        return settings.AGENT_PROMPT

    @staticmethod
    def _output_parser():
        return OpenAIFunctionsAgentOutputParser(pydantic_object=AgentFunctionCaseList)  # type: ignore

    def _retriever_knowledge(self, query):
        if self.retriever:
            docs = self.retriever.invoke(query)
            return "\n".join([
                f"[知识条目 {doc.page_content[:200]}..."
                for doc in docs
            ])
        return ""

    def reset_memery(self):
        self.memory.clear()

    @staticmethod
    def update_knowledge(vector_db, docs):
        vector_db.add_documents(docs)

    # 测试用例生成方法
    def generate_test_cases(self, query, context=None, use_rag=False, case_count=None):
        """
        生成测试用例 - 增强版本
        
        Args:
            query: 需求描述
            context: 上下文信息
            use_rag: 是否使用RAG增强
            case_count: 生成用例数量
        """
        try:
            estimated_tokens = count_tokens(query)
            record_llm_call(estimated_tokens, is_actual=True, input_text=query)

            # 获取知识库检索结果
            retriever = ""
            if use_rag:
                retriever = self._retriever_knowledge(query)

            # 初始化复杂度分析器并分析需求风险
            complexity_scorer = ComplexityScorer.from_knowledge_base()
            risk_analysis = complexity_scorer.analyze_requirement_risks(query)

            # 获取建议的测试类型和方法
            suggested_test_types = ComplexityScorer.get_risk_based_test_types(risk_analysis["overall_risk"])
            suggested_methods = ComplexityScorer.get_risk_based_test_methods(risk_analysis["overall_risk"])

            # 构建复杂度分析文本
            complexity_analysis = f"""
    - 总体风险等级: {risk_analysis['overall_risk']}
    - 平台风险: {[p['platform'] + '(' + p['risk'] + ')' for p in risk_analysis['platform_risks']]}
    - 应用类型风险: {[a['category'] + '(' + a['risk'] + ')' for a in risk_analysis['application_risks']]}
    - 功能风险: {[f['function'] + '(' + f['risk'] + ')' for f in risk_analysis['functional_risks']]}
    """

            # 确定用例数量
            max_cases = case_count or settings.MAX_CASE_NUM

            # 选择合适的提示词模板
            if use_rag and retriever:
                prompt_text = settings.FUNCTION_PROMPT_RAG.format(
                    max_case_nums=max_cases,
                    requirement=query,
                    context=retriever,
                    complexity_analysis=complexity_analysis,
                    suggested_test_types=', '.join(suggested_test_types) if suggested_test_types else '功能测试',
                    suggested_methods=', '.join(suggested_methods) if suggested_methods else '等价类划分法',
                    format_instructions="请严格返回 JSON 格式，字段名必须是英文(case_id, module, title, preconditions, steps, expected, priority, test_type, test_method, tags)，但所有测试用例内容必须使用中文"
                )
            else:
                prompt_text = settings.FUNCTION_PROMPT.format(
                    max_case_nums=max_cases,
                    requirement=query,
                    complexity_analysis=complexity_analysis,
                    suggested_test_types=', '.join(suggested_test_types) if suggested_test_types else '功能测试',
                    suggested_methods=', '.join(suggested_methods) if suggested_methods else '等价类划分法',
                    format_instructions="请严格返回 JSON 格式，字段名必须是英文(case_id, module, title, preconditions, steps, expected, priority, test_type, test_method, tags)，但所有测试用例内容必须使用中文"
                )

            # 构建查询
            full_query = f"{prompt_text}\n\n知识库：{retriever}\n上下文：{context or ''}"

            # 添加详细的日志追踪
            logger.info(" 开始调用 LLM...")
            logger.info(f"📝 请求内容长度: {len(full_query)}")
            logger.info(f"🔧 使用模型: {getattr(self.llm, 'model_name', 'unknown')}")
            logger.info(f"⏰ 开始时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # 只记录操作状态，不记录业务数据
            logger.debug(f"测试用例生成请求长度：{len(full_query)}")

            # 添加进度提示
            logger.info("⏳ GPT-5 正在思考中，请耐心等待...")
            logger.info(" 提示：GPT-5 响应时间较长，请耐心等待...")

            # 使用多线程安全的超时控制
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self.llm.invoke, full_query)
                try:
                    response = future.result(timeout=TestAgent.TIMEOUT_SECONDS)
                    logger.info("✅ LLM 调用成功完成")
                except concurrent.futures.TimeoutError:
                    logger.error("⏰ LLM 调用超时")
                    raise TimeoutError("LLM 调用超时")
                except Exception as e:
                    logger.error(f"❌ LLM 调用失败: {e}")
                    logger.error(f"错误类型: {type(e)}")
                    logger.error(f"错误详情: {str(e)}")
                    raise

            # 添加实际 Token 使用情况记录
            if hasattr(response, 'response_metadata'):
                token_usage = response.response_metadata.get('token_usage', {})
                if token_usage:
                    # 打印详细的Token信息
                    input_tokens = token_usage.get('prompt_tokens', 0)
                    output_tokens = token_usage.get('completion_tokens', 0)
                    total_tokens = token_usage.get('total_tokens', 0)

                    # 从completion_tokens_details中获取思考Token
                    completion_details = token_usage.get('completion_tokens_details', {})
                    reasoning_tokens = completion_details.get('reasoning_tokens', 0)

                    logger.info(f"""
                    📊 Tokens消耗摘要:
                       - 输入Tokens: {input_tokens}
                       - 输出Tokens: {output_tokens}
                       - 思考Tokens: {reasoning_tokens}
                       - 总体Tokens: {total_tokens}
                    """)

                    # 记录到 Token 监控器
                    if total_tokens > 0:
                        record_llm_call(total_tokens, is_actual=True)

            # 解析响应
            response_text = getattr(response, 'content', str(response))
            parsed_response = safe_json_loads(response_text)
            logger.debug(f"测试用例解析完成，数量：{len(parsed_response) if parsed_response else 0}")

            # 返回纯净的业务数据
            return parsed_response

        except Exception as e:
            logger.error(f"测试用例生成异常：{type(e).__name__}")
            return {"status": "error", "message": "生成失败"}

    def rag_test_cases(self, query, context: Optional[str] = None) -> Dict:
        """
        基于RAG知识库生成测试用例（使用 settings.FUNCTION_PROMPT_RAG）
        """
        try:
            estimated_tokens = count_tokens(query)
            record_llm_call(estimated_tokens, is_actual=True, input_text=query)

            # 获取知识库检索结果
            retriever = self._retriever_knowledge(query)

            # 初始化复杂度分析器并分析需求风险
            complexity_scorer = ComplexityScorer()
            risk_analysis = complexity_scorer.analyze_requirement_risks(query)

            # 获取建议的测试类型和方法（静态方法）
            suggested_test_types = ComplexityScorer.get_risk_based_test_types(risk_analysis["overall_risk"])
            suggested_methods = ComplexityScorer.get_risk_based_test_methods(risk_analysis["overall_risk"])

            # 构建复杂度分析文本
            complexity_analysis = f"""
    - 总体风险等级: {risk_analysis['overall_risk']}
    - 平台风险: {[p['platform'] + '(' + p['risk'] + ')' for p in risk_analysis['platform_risks']]}
    - 应用类型风险: {[a['category'] + '(' + a['risk'] + ')' for a in risk_analysis['application_risks']]}
    - 功能风险: {[f['function'] + '(' + f['risk'] + ')' for f in risk_analysis['functional_risks']]}
    """

            # 构建提示词
            prompt_text = settings.FUNCTION_PROMPT_RAG.format(
                max_case_nums=settings.MAX_CASE_NUM,
                requirement=query,
                context=context or "",
                complexity_analysis=complexity_analysis,
                suggested_test_types=', '.join(suggested_test_types) if suggested_test_types else '功能测试',
                suggested_methods=', '.join(suggested_methods) if suggested_methods else '等价类划分法',
                format_instructions="请严格返回 JSON 格式，字段名必须是英文(case_id, module, title, preconditions, steps, expected, priority)"
            )

            # 构建包含知识库的完整查询
            full_query = f"{prompt_text}\n\n知识库检索结果：{retriever}"

            # 添加详细的日志追踪
            logger.info(" 开始调用 LLM (RAG模式)...")
            logger.info(f"📝 请求内容长度: {len(full_query)}")
            logger.info(f"🔧 使用模型: {getattr(self.llm, 'model_name', 'unknown')}")
            logger.info(f"⏰ 开始时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # 只记录操作状态，不记录业务数据
            logger.debug(f"RAG测试用例生成请求长度：{len(full_query)}")

            # 添加进度提示
            logger.info("⏳ GPT-5 正在思考中，请耐心等待...")
            logger.info(" 提示：GPT-5 响应时间较长，请耐心等待...")

            # 使用多线程安全的超时控制
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self.llm.invoke, full_query)
                try:
                    response = future.result(timeout=TestAgent.TIMEOUT_SECONDS)
                    logger.info("✅ LLM 调用成功完成")
                except concurrent.futures.TimeoutError:
                    logger.error("⏰ LLM 调用超时")
                    raise TimeoutError("LLM 调用超时")
                except Exception as e:
                    logger.error(f"❌ LLM 调用失败: {e}")
                    logger.error(f"错误类型: {type(e)}")
                    logger.error(f"错误详情: {str(e)}")
                    raise

            # 添加实际 Token 使用情况记录
            if hasattr(response, 'response_metadata'):
                token_usage = response.response_metadata.get('token_usage', {})
                if token_usage:
                    # 打印详细的Token信息
                    input_tokens = token_usage.get('prompt_tokens', 0)
                    output_tokens = token_usage.get('completion_tokens', 0)
                    total_tokens = token_usage.get('total_tokens', 0)

                    # 从completion_tokens_details中获取思考Token
                    completion_details = token_usage.get('completion_tokens_details', {})
                    reasoning_tokens = completion_details.get('reasoning_tokens', 0)

                    logger.info(f"""
                    📊 RAG Tokens消耗摘要:
                       - 输入Tokens: {input_tokens}
                       - 输出Tokens: {output_tokens}
                       - 思考Tokens: {reasoning_tokens}
                       - 总体Tokens: {total_tokens}
                    """)

                    # 记录到 Token 监控器
                    if total_tokens > 0:
                        record_llm_call(total_tokens, is_actual=True)

            response_text = getattr(response, 'content', str(response))
            parsed_response = safe_json_loads(response_text)
            logger.debug(f"测试用例解析完成，数量：{len(parsed_response) if parsed_response else 0}")

            return parsed_response

        except Exception as e:
            logger.error(f"RAG测试用例生成异常：{type(e).__name__}")
            return {
                "status": "error",
                "message": "RAG生成失败"
            }


if __name__ == "__main__":
    pass