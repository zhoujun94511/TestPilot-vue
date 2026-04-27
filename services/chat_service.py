"""
TestPilot 聊天服务模块
处理AI聊天对话、会话管理、流式响应等功能
"""
import re
import sys
import json
import time
from uuid import uuid4
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Generator, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from models.models import ChatHistory
from utils.utils_performance_monitoring.performance_monitor import get_performance_monitor
from utils.utils_ai_models.smart_quick_reply_generator import SmartQuickReplyGenerator
from utils.utils_core.logger import get_logger
from utils.utils_core.api_error_handler import normalize_provider_error
from utils.utils_intelligent_retrieval.smart_retrieval_strategy import get_smart_retrieval_strategy
from utils.utils_ai_quality.hallucination_detector import create_hallucination_detector
from config.settings import settings

logger = get_logger(__name__)


class ChatService:
    """聊天服务类"""

    def __init__(self):
        self.performance_monitor = get_performance_monitor()
        self.smart_retrieval = get_smart_retrieval_strategy()
        self.hallucination_detector = create_hallucination_detector()
        self.llm = None
        self.vector_db = None

    def initialize(self, llm, vector_db):
        """初始化服务依赖"""
        self.llm = llm
        self.vector_db = vector_db

    @staticmethod
    def _is_valid_retrieval_query(query: str) -> bool:
        """Guard empty/meaningless retrieval query to avoid embedding errors."""
        text = str(query or "").strip()
        if not text:
            return False
        # Strip common punctuation/symbols and keep meaningful chars only.
        normalized = re.sub(r"[\s`~!@#$%^&*()\-_=+\[\]{}|;:'\",.<>/?，。！？；：、（）【】《》…·]+", "", text)
        return bool(normalized)

    @staticmethod
    def create_chat_session(db_session: Session, user_id: Optional[str] = None) -> Dict[str, Any]:
        """创建新的聊天会话"""
        try:
            session_id = str(uuid4())

            # 创建初始系统消息
            system_message = ChatHistory(
                session_id=session_id,
                user_id=user_id,
                role='system',
                content='你是一个专业的测试助手，专门帮助用户进行软件测试相关的工作。请提供准确、有用的建议和指导。',
                created_time=datetime.now(timezone.utc)
            )

            db_session.add(system_message)
            db_session.commit()

            logger.info(f"创建聊天会话成功: {session_id}")

            return {
                'success': True,
                'session_id': session_id,
                'created_time': system_message.created_time.isoformat()
            }

        except Exception as e:
            logger.error(f"创建聊天会话失败: {str(e)}")
            db_session.rollback()
            return {
                'success': False,
                'message': f'创建聊天会话失败: {str(e)}'
            }

    def send_message(self, db_session: Session, session_id: str, message: str,
                     user_settings: Optional[Dict[str, Any]] = None, use_context: bool = True,
                     use_knowledge: bool = False, user_id: Optional[str] = None,
                     save_user_message: bool = True) -> Dict[str, Any]:
        """发送聊天消息（非流式）"""
        try:
            user_message_text = message

            # 保存用户消息，或复用路由层已保存的记录
            if save_user_message:
                user_message = ChatHistory(
                    session_id=session_id,
                    user_id=user_id,
                    role='user',
                    content=user_message_text,
                    created_time=datetime.now(timezone.utc)
                )
                db_session.add(user_message)
                db_session.flush()

            # 获取对话历史
            context_messages = []
            if use_context:
                context_messages = self._get_conversation_context(db_session, session_id)

            # 增强上下文（如果启用知识库）
            enhanced_context = message
            if use_knowledge and self.vector_db:
                enhanced_context = self._enhance_with_knowledge(message)

            # 构建消息列表（所有模型统一应用严格规则）
            messages = self._build_message_list(
                context_messages,
                enhanced_context,
                original_user_message=message
            )

            # 调用LLM生成响应
            llm_settings = self._prepare_llm_settings(user_settings)

            # Gemini 需要通过 generation_config 传递参数
            if self.llm.__class__.__name__ == 'ChatGoogleGenerativeAI':
                llm_settings = self._adapt_settings_for_gemini(llm_settings)

            response = self.llm.invoke(
                messages,
                **llm_settings
            )

            ai_response = response.content if hasattr(response, 'content') else str(response)
            tokens_used = self._extract_tokens_used(response, ai_response)
            model_name = self._resolve_model_name(user_settings, response)

            # 幻觉检测（如果启用）
            hallucination_result = None
            if getattr(settings, 'ENABLE_HALLUCINATION_DETECTION', True):
                try:
                    # 准备源文档
                    source_documents = []
                    if use_knowledge and self.vector_db:
                        # 获取知识库文档作为源
                        try:
                            knowledge_docs = self.vector_db.similarity_search(message, k=3)
                            for doc in knowledge_docs:
                                source_documents.append({
                                    'content': doc.page_content,
                                    'source': 'knowledge_base',
                                    'quality_score': 0.9
                                })
                        except Exception as e:
                            logger.debug(f"获取知识库文档失败: {e}")
                    
                    # 检测幻觉
                    hallucination_result = self.hallucination_detector.detect_hallucination(
                        ai_response, 
                        source_documents, 
                        context=message
                    )
                    
                    if hallucination_result.is_hallucination:
                        logger.warning(f"检测到潜在幻觉，置信度: {hallucination_result.confidence:.2f}")
                except Exception as e:
                    logger.warning(f"幻觉检测失败: {e}")

            # 保存AI响应
            ai_message = ChatHistory(
                session_id=session_id,
                user_id=user_id,
                role='assistant',
                content=ai_response,
                created_time=datetime.now(timezone.utc),
                tokens_used=tokens_used,
                model_name=model_name
            )
            db_session.add(ai_message)
            db_session.commit()

            # 生成回复建议
            conversation_context = self._get_conversation_context_for_suggestions(db_session, session_id)
            use_smart_reply = user_settings.get("use_smart_reply", False) if user_settings else False
            suggestions = self._generate_reply_suggestions(
                ai_response, 
                conversation_context=conversation_context,
                user_id=user_id,
                use_knowledge=use_knowledge,
                user_message=user_message_text,
                use_smart_reply=use_smart_reply
            ) if user_settings and user_settings.get('auto_suggest') else []

            logger.info(f"聊天消息处理成功: session={session_id}")

            result = {
                'success': True,
                'message': ai_response,
                'suggestions': suggestions,
                'timestamp': ai_message.created_time.isoformat(),
                'tokens_used': tokens_used,
                'model_name': model_name
            }
            
            # 添加幻觉检测结果
            if hallucination_result:
                result['hallucination_detection'] = {
                    'is_hallucination': hallucination_result.is_hallucination,
                    'confidence': hallucination_result.confidence,
                    'issues': hallucination_result.issues,
                    'suggestions': hallucination_result.suggestions
                }

            return result

        except Exception as e:
            logger.error(f"发送聊天消息失败: {str(e)}")
            db_session.rollback()
            normalized = normalize_provider_error(getattr(settings, 'DEFAULT_COMPANY', 'OPENAI'), e)
            return {
                'success': False,
                'message': normalized.get('message', '发送消息失败'),
                'error_code': normalized.get('error_code'),
                'retryable': bool(normalized.get('retryable', False))
            }

    def stream_message(
            self,
            db_session: Session,
            session_id: str,
            message: str,
            user_settings: Optional[Dict[str, Any]] = None,
            use_context: bool = True,
            use_knowledge: bool = False,
            user_id: Optional[str] = None,
            context_messages: Optional[List[Dict[str, Any]]] = None,  # ✅ 修改类型注解
    ) -> Generator[str, None, None]:
        from config.settings import settings as config_settings
        """发送聊天消息（流式响应）"""
        try:
            _ = user_id
            _ = db_session

            # 开始事件
            yield self._create_stream_event("start", {"session_id": session_id})

            # ✅ 使用预获取的上下文，不再访问数据库
            context_messages = context_messages if use_context else []

            # 知识增强
            enhanced_context = self._enhance_with_knowledge(message) if (use_knowledge and self.vector_db) else message

            # 构建消息列表（所有模型统一应用严格规则）
            messages = self._build_message_list(
                context_messages,
                enhanced_context,
                original_user_message=message
            )

            # LLM 设置
            llm_settings = self._prepare_llm_settings(user_settings)
            
            # Gemini 需要通过 generation_config 传递参数，且不接受 stream 参数
            if self.llm.__class__.__name__ == 'ChatGoogleGenerativeAI':
                llm_settings = self._adapt_settings_for_gemini(llm_settings, include_stream=True)
            else:
                # 其他模型需要 stream 参数
                llm_settings["stream"] = True

            # 调用 LLM（流式）
            full_response = ""
            if hasattr(self.llm, "stream"):
                try:
                    for chunk in self.llm.stream(messages, **llm_settings):
                        if hasattr(chunk, "content") and chunk.content:
                            # ✅ 确保内容编码正确
                            content = chunk.content
                            if isinstance(content, bytes):
                                content = content.decode('utf-8')
                            full_response += content
                            yield self._create_stream_event("chunk", {"content": content})
                except Exception as llm_error:
                    logger.error(f"LLM 流式生成失败: {str(llm_error)}")
                    normalized = normalize_provider_error(getattr(settings, 'DEFAULT_COMPANY', 'OPENAI'), llm_error)
                    yield self._create_stream_event("error", {
                        "message": normalized.get("message", "模型调用失败"),
                        "error_code": normalized.get("error_code"),
                        "retryable": bool(normalized.get("retryable", False)),
                        "status_code": normalized.get("status_code", 500)
                    })
                    return

            elif hasattr(self.llm, "chat") and hasattr(self.llm.chat, "completions"):
                try:
                    # 构建流式调用参数（GPT-5 不支持 temperature，所以不传）
                    stream_params = {
                        "model": llm_settings.get("model", "gpt-5"),
                        "messages": messages,
                        "stream": True,
                        "max_tokens": llm_settings.get("max_tokens", getattr(config_settings, 'MAX_TOKENS', 4000)),
                    }
                    # 只有当 temperature 存在且不是 GPT-5 时才添加
                    if "temperature" in llm_settings:
                        stream_params["temperature"] = llm_settings["temperature"]
                    
                    for chunk in self.llm.chat.completions.create(**stream_params):
                        delta = chunk.choices[0].delta.get("content", "")
                        if delta:
                            # ✅ 确保内容编码正确
                            if isinstance(delta, bytes):
                                delta = delta.decode('utf-8')
                            full_response += delta
                            yield self._create_stream_event("chunk", {"content": delta})
                except Exception as llm_error:
                    logger.error(f"OpenAI LLM 流式生成失败: {str(llm_error)}")
                    normalized = normalize_provider_error(getattr(settings, 'DEFAULT_COMPANY', 'OPENAI'), llm_error)
                    yield self._create_stream_event("error", {
                        "message": normalized.get("message", "模型调用失败"),
                        "error_code": normalized.get("error_code"),
                        "retryable": bool(normalized.get("retryable", False)),
                        "status_code": normalized.get("status_code", 500)
                    })
                    return

            # 回复建议
            suggestions = []
            model_name = self._resolve_model_name(user_settings)
            if user_settings and user_settings.get("auto_suggest"):
                conversation_context = self._get_conversation_context_for_suggestions(db_session, session_id)
                use_smart_reply = user_settings.get("use_smart_reply", False)
                suggestions = self._generate_reply_suggestions(
                    full_response,
                    conversation_context=conversation_context,
                    user_id=user_id,
                    use_knowledge=use_knowledge,
                    user_message=message,
                    use_smart_reply=use_smart_reply
                )

            # 幻觉检测（如果启用）
            hallucination_result = None
            if getattr(settings, 'ENABLE_HALLUCINATION_DETECTION', True):
                try:
                    # 准备源文档
                    source_documents = []
                    if use_knowledge and self.vector_db:
                        # 获取知识库文档作为源
                        try:
                            knowledge_docs = self.vector_db.similarity_search(message, k=3)
                            for doc in knowledge_docs:
                                source_documents.append({
                                    'content': doc.page_content,
                                    'source': 'knowledge_base',
                                    'quality_score': 0.9
                                })
                        except Exception as e:
                            logger.debug(f"获取知识库文档失败: {e}")
                    
                    # 检测幻觉
                    hallucination_result = self.hallucination_detector.detect_hallucination(
                        full_response, 
                        source_documents, 
                        context=message
                    )
                    
                    if hallucination_result.is_hallucination:
                        logger.warning(f"检测到潜在幻觉，置信度: {hallucination_result.confidence:.2f}")
                except Exception as e:
                    logger.warning(f"幻觉检测失败: {e}")

            # 结束事件 - 返回完整响应供外部保存
            tokens_used = self._estimate_tokens(full_response)
            end_data = {
                "suggestions": suggestions,
                "full_response": full_response,  # ✅ 返回完整响应供外部保存
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tokens_used": tokens_used,
                "model_name": model_name
            }
            
            # 添加幻觉检测结果
            if hallucination_result:
                end_data['hallucination_detection'] = {
                    'is_hallucination': hallucination_result.is_hallucination,
                    'confidence': hallucination_result.confidence,
                    'issues': hallucination_result.issues,
                    'suggestions': hallucination_result.suggestions
                }
            
            yield self._create_stream_event("end", end_data)

            logger.info(f"流式聊天消息处理成功: session={session_id}")

        except Exception as e:
            logger.error(f"流式聊天消息失败: {str(e)}")
            normalized = normalize_provider_error(getattr(settings, 'DEFAULT_COMPANY', 'OPENAI'), e)
            yield self._create_stream_event("error", {
                "message": normalized.get("message", "模型调用失败"),
                "error_code": normalized.get("error_code"),
                "retryable": bool(normalized.get("retryable", False)),
                "status_code": normalized.get("status_code", 500)
            })

    @staticmethod
    def _create_stream_event(event_type: str, data: Dict[str, Any]) -> str:
        """创建流式事件"""
        event_data = {
            'type': event_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **data
        }
        # ✅ 修复：确保UTF-8编码
        return f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

    @staticmethod
    def _get_conversation_context(db_session: Session, session_id: str,
                                  limit: int = 20) -> List[Dict[str, Any]]:
        """获取对话上下文（排除 system 消息）"""
        try:
            from models.models import ChatHistory
            
            # 获取最近的对话历史（排除 system 消息）
            recent_messages = db_session.query(ChatHistory).filter(
                and_(
                    ChatHistory.session_id == str(session_id),  # type: ignore
                    ChatHistory.role != 'system'  # 排除 system 消息
                )
            ).order_by(ChatHistory.created_time.desc()).limit(limit).all()
            
            # 转换为字典格式
            context = []
            for msg in reversed(recent_messages):  # 按时间正序
                context.append({
                    'role': msg.role,
                    'content': msg.content
                })
            
            return context

        except Exception as e:
            logger.error(f"获取对话上下文失败: {str(e)}")
            return []

    def _enhance_with_knowledge(self, message: str, top_k: int = None, use_smart_retrieval: bool = True) -> str:
        """使用知识库增强消息（支持智能检索）"""
        try:
            # 使用 settings 中的默认值
            if top_k is None:
                top_k = getattr(settings, 'RAG_TOP_K', 3)
                
            if not self.vector_db:
                return message
            if not self._is_valid_retrieval_query(message):
                logger.debug("跳过知识检索：查询文本为空或无有效字符")
                return message

            # 记录开始时间
            start_time = time.time()
            
            if use_smart_retrieval:
                # 使用智能检索策略
                try:
                    smart_results = self.smart_retrieval.retrieve(
                        query=message,
                        vector_db=self.vector_db,
                        context=None  # 可以传入对话上下文
                    )
                except ValueError as retrieval_error:
                    logger.debug(f"跳过知识检索（参数无效）: {retrieval_error}")
                    return message
                
                # 转换为文档格式
                relevant_docs = []
                for result in smart_results[:top_k]:
                    # 创建模拟的文档对象
                    class MockDoc:
                        def __init__(self, content, metadata):
                            self.page_content = content
                            self.metadata = metadata
                    
                    relevant_docs.append(MockDoc(result.content, result.metadata))
                
                # 记录搜索耗时（用于性能监控）
                search_duration = time.time() - start_time
                logger.debug(f"智能检索耗时: {search_duration:.3f}秒")
                
            else:
                # 使用传统搜索
                try:
                    relevant_docs = self.vector_db.similarity_search(message, k=top_k)
                except ValueError as retrieval_error:
                    logger.debug(f"跳过知识检索（参数无效）: {retrieval_error}")
                    return message
                search_duration = time.time() - start_time
                
                # 记录embedding性能指标
                try:
                    from utils.utils_ai_models.embedding_monitor import get_embedding_monitor
                    embedding_monitor = get_embedding_monitor()
                    embedding_monitor.record_call(
                        tokens=len(message.split()),
                        duration=search_duration,
                        success=True,
                        cache_hit=False,
                        model_name="sentence-transformers",
                        device="auto"
                    )
                except Exception as monitor_error:
                    logger.debug(f"记录embedding性能指标失败: {monitor_error}")

            if not relevant_docs:
                return message

            # 构建增强的上下文
            knowledge_context = "\n".join([
                f"参考资料{i + 1}: {doc.page_content}"
                for i, doc in enumerate(relevant_docs)
            ])

            enhanced_message = f"""用户问题: {message}

相关参考资料:
{knowledge_context}

请基于以上参考资料回答用户问题，如果参考资料不相关，请直接回答用户问题。"""

            return enhanced_message

        except Exception as e:
            logger.error(f"知识库增强失败: {str(e)}")
            return message

    @staticmethod
    def _infer_language_instruction(text: str) -> str:
        """
        根据用户输入粗略判断主体语言，返回输出语言约束。
        优先按主体语言输出，避免中英混杂。
        """
        content = (text or "").strip()
        if not content:
            return "默认使用中文输出。"

        # 语言判定时剔除代码片段/代码行，避免“中文问题 + 英文代码”被误判为英文输出
        sanitized = re.sub(r'```[\s\S]*?```', ' ', content)
        sanitized = re.sub(r'`[^`]*`', ' ', sanitized)
        sanitized = re.sub(r'https?://\S+', ' ', sanitized)

        non_code_lines = []
        for line in sanitized.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # 常见代码特征：包含大量符号且几乎无中文
            symbol_count = len(re.findall(r'[{}();=<>\[\]#:_/\\]', stripped))
            zh_in_line = len(re.findall(r'[\u4e00-\u9fff]', stripped))
            if symbol_count >= 2 and zh_in_line == 0:
                continue
            non_code_lines.append(stripped)

        language_sample = ' '.join(non_code_lines) if non_code_lines else sanitized
        zh_count = len(re.findall(r'[\u4e00-\u9fff]', language_sample))
        en_count = len(re.findall(r'[A-Za-z]', language_sample))

        if zh_count > en_count:
            return "请使用简体中文回答；除专有名词、代码、接口名外，不要夹杂英文句子。"
        if en_count > zh_count:
            return "Please answer in English; avoid mixing Chinese sentences except for fixed proper nouns."
        return "请跟随用户输入的主体语言作答，避免中英混杂。"

    @staticmethod
    def _build_message_list(
        context_messages: List[Dict[str, Any]],
        current_message: str,
        original_user_message: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        构建消息列表（统一适配 OpenAI / Gemini / DeepSeek / Qwen 等所有模型）
        所有模型统一应用：强制角色 prompt、消息去重、user-assistant 成对规则
        """
        # 统一系统提示词 —— 所有模型使用同等强约束
        language_source = (original_user_message or current_message or "").strip()
        language_instruction = ChatService._infer_language_instruction(language_source)

        system_prompt = f"""你是一个专业的软件测试助手。你的身份和职责如下：

身份：专业的软件测试助手
职责：专门帮助用户进行软件测试相关的工作

重要规则：
1. 在任何情况下，你都必须以"专业的测试助手"的身份回答
2. 不要介绍自己是某个AI模型（如GPT、Gemini、DeepSeek、Qwen等），你只是"专业的测试助手"
3. 始终专注于软件测试相关的话题和建议
4. 提供准确、专业、有用的测试建议和指导
5. 输出语言必须遵循以下规则：{language_instruction}

请严格遵守以上规则，始终以专业测试助手的身份与用户交流。"""
        
        messages = [
            {"role": "system",
             "content": system_prompt}
        ]
        
        # 添加历史对话（过滤掉 system 消息和重复的当前消息）
        filtered_messages = []
        seen_contents = set()  # 用于去重
        last_role = None  # 跟踪上一条消息的角色
        
        for msg in context_messages[-10:]:  # 只取最近10条消息避免上下文过长
            role = msg.get('role', '').lower()
            content = msg.get('content', '').strip()
            
            # 跳过 system 消息（避免重复）
            if role == 'system':
                continue
            
            # 跳过空内容
            if not content:
                continue
            
            # 跳过与当前消息重复的消息
            if role == 'user' and content == language_source:
                continue
            
            # 去重：跳过内容完全相同的消息
            msg_key = (role, content)
            if msg_key in seen_contents:
                continue
            seen_contents.add(msg_key)
            
            # 所有模型统一应用严格的 user-assistant 成对规则
            if last_role is not None:
                if last_role == 'user' and role != 'assistant':
                    # 上一条是 user 但当前不是 assistant，跳过（避免连续 user）
                    continue
                elif last_role == 'assistant' and role != 'user':
                    # 上一条是 assistant 但当前不是 user，跳过（避免连续 assistant）
                    continue
            
            filtered_messages.append({
                "role": role,
                "content": content
            })
            last_role = role

        # 将过滤后的历史消息添加到列表
        messages.extend(filtered_messages)

        # 添加当前消息
        current_msg_stripped = current_message.strip()
        if current_msg_stripped:
            messages.append({
                "role": "user",
                "content": current_msg_stripped
            })

        return messages

    def _prepare_llm_settings(self, user_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        准备LLM设置（统一适配 OpenAI / Gemini / DeepSeek / Qwen 等所有模型）
        根据当前 LLM 类型自动决定参数集，避免产生无用的参数添加/移除
        """
        from config.settings import settings as config_settings
        
        # 判断当前是否为 Gemini 模型
        is_gemini = (self.llm and self.llm.__class__.__name__ == 'ChatGoogleGenerativeAI')
        
        # 判断当前是否为 GPT-5 模型（GPT-5 不支持自定义 temperature，只支持默认值 1）
        is_gpt5 = False
        if self.llm:
            model_name = None
            if hasattr(self.llm, 'model'):
                model_name = self.llm.model
            elif hasattr(self.llm, 'model_name'):
                model_name = self.llm.model_name
            elif user_settings and 'model' in user_settings:
                model_name = user_settings.get('model', '')
            
            if model_name and 'gpt-5' in str(model_name).lower():
                is_gpt5 = True
        
        default_settings = {
            'max_tokens': getattr(config_settings, 'MAX_TOKENS', 4000),
            'top_p': 1.0,
        }
        
        # frequency_penalty / presence_penalty 仅 OpenAI / DeepSeek / Qwen 支持，Gemini 不支持
        if not is_gemini:
            default_settings['frequency_penalty'] = 0.0
            default_settings['presence_penalty'] = 0.0

        if user_settings:
            # GPT-5 不支持自定义 temperature，只支持默认值 1，所以不设置 temperature 参数
            if not is_gpt5:
                user_temp = user_settings.get('temperature', 0.7)
                
                # 所有模型统一：temperature >= 0.7 时自动降到 0.3，提高 prompt 遵循度
                if user_temp >= 0.7:
                    default_settings['temperature'] = 0.3
                else:
                    default_settings['temperature'] = user_temp

            default_settings['max_tokens'] = user_settings.get(
                'max_tokens', getattr(config_settings, 'MAX_TOKENS', 4000)
            )

        return default_settings

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """粗略 token 估算（用于流式场景兜底）"""
        content = (text or '').strip()
        if not content:
            return 0
        # 英文约 4 chars/token，中文通常更稠密，取保守估算避免长期为 0
        return max(1, int(len(content) / 4))

    def _resolve_model_name(self, user_settings: Optional[Dict[str, Any]] = None, response: Any = None) -> str:
        """优先从响应元数据解析模型名，其次回退到 LLM 实例与用户设置。"""
        try:
            if response is not None:
                response_metadata = getattr(response, 'response_metadata', None)
                if isinstance(response_metadata, dict):
                    for key in ('model_name', 'model', 'model_id'):
                        value = response_metadata.get(key)
                        if value:
                            return str(value)
                for key in ('model_name', 'model', 'model_id'):
                    value = getattr(response, key, None)
                    if value:
                        return str(value)
        except (AttributeError, TypeError):
            pass

        try:
            if self.llm:
                if hasattr(self.llm, 'model') and getattr(self.llm, 'model'):
                    return str(getattr(self.llm, 'model'))
                if hasattr(self.llm, 'model_name') and getattr(self.llm, 'model_name'):
                    return str(getattr(self.llm, 'model_name'))
        except (AttributeError, TypeError):
            pass

        if user_settings and user_settings.get('model'):
            return str(user_settings.get('model'))
        return 'unknown'

    def _extract_tokens_used(self, response: Any, generated_text: str) -> int:
        """尽量读取模型真实 token 用量；缺失时做估算兜底。"""
        try:
            usage_metadata = getattr(response, 'usage_metadata', None)
            if isinstance(usage_metadata, dict):
                total = usage_metadata.get('total_tokens')
                if total is not None:
                    return max(0, int(total))
                output = usage_metadata.get('output_tokens') or usage_metadata.get('completion_tokens')
                if output is not None:
                    return max(0, int(output))
        except (AttributeError, TypeError, ValueError):
            pass

        try:
            response_metadata = getattr(response, 'response_metadata', None)
            if isinstance(response_metadata, dict):
                token_usage = response_metadata.get('token_usage')
                if isinstance(token_usage, dict):
                    total = token_usage.get('total_tokens')
                    if total is not None:
                        return max(0, int(total))
                    completion = token_usage.get('completion_tokens')
                    if completion is not None:
                        return max(0, int(completion))
        except (AttributeError, TypeError, ValueError):
            pass

        return self._estimate_tokens(generated_text)
    
    @staticmethod
    def _adapt_settings_for_gemini(llm_settings: Dict[str, Any],
                                   include_stream: bool = False) -> Dict[str, Any]:
        """
        将通用 LLM 参数映射为 Gemini generation_config 格式
        仅在 LLM 为 ChatGoogleGenerativeAI 时调用
        """
        if 'generation_config' not in llm_settings:
            llm_settings['generation_config'] = {}
        
        param_mapping = {
            'max_tokens': 'max_output_tokens',
            'top_p': 'top_p',
            'temperature': 'temperature',
            'top_k': 'top_k',
            'stop': 'stop_sequences'
        }
        
        for lc_param, gemini_param in param_mapping.items():
            if lc_param in llm_settings:
                value = llm_settings.pop(lc_param)
                if value is not None:
                    llm_settings['generation_config'][gemini_param] = value
        
        # 移除 Gemini 不支持的残留参数（防御性清理）
        for param in ['frequency_penalty', 'presence_penalty', 'stream'] if include_stream else ['frequency_penalty', 'presence_penalty']:
            llm_settings.pop(param, None)
        
        return llm_settings

    def _generate_reply_suggestions(self, ai_response: str, 
                                  conversation_context: List[Dict[str, str]] = None,
                                  user_id: str = None,
                                  use_knowledge: bool = False,
                                  user_message: str = None,
                                  use_smart_reply: bool = False) -> List[str]:
        """生成智能回复建议"""
        try:
            if use_smart_reply:
                # 使用智能生成器
                generator = SmartQuickReplyGenerator()
                
                # 获取知识库上下文（如果启用了知识库）
                knowledge_context = None
                if use_knowledge and user_message:
                    knowledge_context = self._get_knowledge_context_for_suggestions(user_message)
                
                suggestions_objects = generator.generate_suggestions(
                    ai_response=ai_response,
                    conversation_context=conversation_context,
                    user_id=user_id,
                    knowledge_context=knowledge_context,
                    max_suggestions=3
                )
                
                # 转换为字符串列表
                suggestions = [suggestion.text for suggestion in suggestions_objects]
                
                logger.debug(f"生成智能回复建议: {suggestions}")
                return suggestions
            else:
                # 使用模板生成建议
                return ChatService._generate_simple_suggestions(ai_response)
            
        except Exception as e:
            logger.error(f"生成智能回复建议失败: {str(e)}")
            # 回退到简单建议
            return ChatService._generate_simple_suggestions(ai_response)
    
    @staticmethod
    def _generate_simple_suggestions(ai_response: str) -> List[str]:
        """生成简单回复建议（备用方案）"""
        suggestions = []

        # 简单的关键词匹配生成建议
        if '测试用例' in ai_response:
            suggestions.extend([
                "如何优化这些测试用例？",
                "能否提供更多测试场景？",
                "这些用例的执行顺序如何安排？"
            ])

        if '测试策略' in ai_response:
            suggestions.extend([
                "这个策略适用于哪些项目类型？",
                "如何评估测试策略的效果？",
                "有什么风险需要注意？"
            ])

        if '自动化' in ai_response:
            suggestions.extend([
                "推荐哪些自动化测试工具？",
                "自动化测试的投入产出比如何？",
                "如何维护自动化测试脚本？"
            ])

        if '缺陷' in ai_response or '错误' in ai_response:
            suggestions.extend([
                "如何预防类似问题？",
                "这类缺陷的根本原因是什么？",
                "有什么最佳实践可以分享？"
            ])

        # 通用建议
        if not suggestions:
            suggestions = [
                "能否详细说明一下？",
                "有具体的例子吗？",
                "还有其他相关问题吗？"
            ]

        return suggestions[:3]  # 最多返回3个建议

    @staticmethod
    def _get_conversation_context_for_suggestions(db_session: Session, session_id: str, limit: int = 5) -> List[Dict[str, str]]:
        """获取对话上下文用于生成建议"""
        try:
            from models.models import ChatHistory
            
            # 获取最近的对话历史
            recent_messages = db_session.query(ChatHistory).filter(
                ChatHistory.session_id == str(session_id)  # type: ignore
            ).order_by(ChatHistory.created_time.desc()).limit(limit).all()
            
            # 转换为字典格式
            context = []
            for msg in reversed(recent_messages):  # 按时间正序
                context.append({
                    'role': msg.role,
                    'content': msg.content
                })
            
            return context
            
        except Exception as e:
            logger.error(f"获取对话上下文失败: {str(e)}")
            return []

    def _get_knowledge_context_for_suggestions(self, user_message: str) -> Optional[Dict[str, Any]]:
        """获取知识库上下文用于生成建议
        
        从以下三个来源检索相关信息：
        1. 向量数据库中的知识文档
        2. 测试用例数据库
        3. 需求文档数据库
        
        Args:
            user_message: 用户消息内容
            
        Returns:
            包含知识库上下文的字典，失败返回None
        """
        try:
            knowledge_context = {
                'knowledge_docs': [],
                'test_cases': [],
                'requirements': []
            }
            
            # 1. 从向量数据库检索相关文档
            if self.vector_db and self._is_valid_retrieval_query(user_message):
                try:
                    # 使用智能检索获取相关文档（最多3个）
                    if self.smart_retrieval:
                        smart_results = self.smart_retrieval.retrieve(
                            query=user_message,
                            vector_db=self.vector_db,
                            context=None
                        )
                        
                        knowledge_context['knowledge_docs'] = [
                            {
                                'content': result.content[:200],  # 只取前200字符作为摘要
                                'score': result.score,
                                'source': result.metadata.get('file_name', '未知') if result.metadata else '未知'
                            }
                            for result in smart_results[:3]
                        ]
                    else:
                        # 回退到普通检索
                        docs = self.vector_db.similarity_search(user_message, k=3)
                        knowledge_context['knowledge_docs'] = [
                            {
                                'content': doc.page_content[:200],
                                'source': doc.metadata.get('file_name', '未知') if hasattr(doc, 'metadata') else '未知'
                            }
                            for doc in docs
                        ]
                    
                    logger.debug(f"从向量数据库检索到 {len(knowledge_context['knowledge_docs'])} 个相关文档")
                except Exception as e:
                    logger.warning(f"从向量数据库检索失败: {e}")
            elif self.vector_db:
                logger.debug("跳过建议检索：查询文本为空或无有效字符")
            
            # 2. 从测试用例数据库获取相关用例（通过关键词匹配）
            try:
                from models.models import TestCase
                from sqlalchemy import or_
                
                # 提取关键词进行搜索（简单实现：分词）
                keywords = user_message.split()[:5]  # 取前5个词
                
                if keywords:
                    # 构建搜索条件
                    search_conditions = []
                    for keyword in keywords:
                        if len(keyword) > 1:  # 忽略单字符
                            search_conditions.append(TestCase.title.contains(keyword))
                            search_conditions.append(TestCase.description.contains(keyword))
                    
                    if search_conditions:
                        test_cases = TestCase.query.filter(
                            or_(*search_conditions),
                            TestCase.status == 'active'
                        ).limit(3).all()
                        
                        knowledge_context['test_cases'] = [
                            {
                                'case_id': tc.display_id or tc.case_id,
                                'title': tc.title,
                                'category': tc.category,
                                'priority': tc.priority
                            }
                            for tc in test_cases
                        ]
                    
                        logger.debug(f"从数据库检索到 {len(knowledge_context['test_cases'])} 个相关测试用例")
            except Exception as e:
                logger.warning(f"从测试用例数据库检索失败: {e}")
            
            # 3. 从需求文档中获取相关信息
            try:
                from models.models import Requirement
                from sqlalchemy import or_
                
                # 提取关键词进行搜索
                keywords = user_message.split()[:5]
                
                if keywords:
                    search_conditions = []
                    for keyword in keywords:
                        if len(keyword) > 1:
                            search_conditions.append(Requirement.title.contains(keyword))
                            search_conditions.append(Requirement.content.contains(keyword))
                    
                    if search_conditions:
                        requirements = Requirement.query.filter(
                            or_(*search_conditions),
                            Requirement.status == 'active'
                        ).limit(3).all()
                        
                        knowledge_context['requirements'] = [
                            {
                                'req_id': req.req_id,
                                'title': req.title,
                                'type': req.type,
                                'priority': req.priority
                            }
                            for req in requirements
                        ]
                    
                        logger.debug(f"从数据库检索到 {len(knowledge_context['requirements'])} 个相关需求")
            except Exception as e:
                logger.warning(f"从需求文档检索失败: {e}")
            
            # 统计总共获取的上下文数量
            total_items = (
                len(knowledge_context['knowledge_docs']) + 
                len(knowledge_context['test_cases']) + 
                len(knowledge_context['requirements'])
            )
            logger.info(f"获取知识库上下文成功，共 {total_items} 项 "
                       f"(文档:{len(knowledge_context['knowledge_docs'])}, "
                       f"用例:{len(knowledge_context['test_cases'])}, "
                       f"需求:{len(knowledge_context['requirements'])})")
            
            return knowledge_context
            
        except Exception as e:
            logger.error(f"获取知识库上下文失败: {str(e)}", exc_info=True)
            return None

    def get_chat_sessions(self, db_session: Session, user_id: Optional[str] = None,
                          limit: int = 50) -> Dict[str, Any]:
        """获取聊天会话列表"""
        try:
            query = db_session.query(
                ChatHistory.session_id,
                func.min(ChatHistory.created_time).label('created_time'),
                func.max(ChatHistory.created_time).label('updated_time'),
                func.count(ChatHistory.id).label('message_count')
            ).filter(
                ChatHistory.role != 'system'# type: ignore
            )

            if user_id is not None:
                query = query.filter(ChatHistory.user_id == user_id)

            sessions_data = query.group_by(
                ChatHistory.session_id
            ).order_by(
                func.max(ChatHistory.created_time).desc()
            ).limit(limit).all()

            sessions = []
            for session_data in sessions_data:
                # 获取会话的第一条用户消息作为标题
                first_message = db_session.query(ChatHistory).filter(
                    and_(
                        ChatHistory.session_id == session_data.session_id,
                        ChatHistory.role == 'user'
                    )
                ).order_by(ChatHistory.created_time).first()

                last_message = db_session.query(ChatHistory).filter(
                    and_(
                        ChatHistory.session_id == session_data.session_id,
                        ChatHistory.role.in_(['user', 'assistant'])
                    )
                ).order_by(ChatHistory.created_time.desc()).first()

                title = self._generate_session_title(first_message.content if first_message else "新会话")

                sessions.append({
                    'id': session_data.session_id,
                    'title': title,
                    'created_time': session_data.created_time.isoformat(),
                    'updated_time': session_data.updated_time.isoformat(),
                    'message_count': session_data.message_count,
                    'last_message': last_message.content[:100] + "..." if last_message and len(
                        last_message.content) > 100 else (last_message.content if last_message else "")
                })

            return {
                'success': True,
                'sessions': sessions
            }

        except Exception as e:
            logger.error(f"获取聊天会话列表失败: {str(e)}")
            return {
                'success': False,
                'message': f'获取会话列表失败: {str(e)}'
            }

    @staticmethod
    def _generate_session_title(first_message: str) -> str:
        """生成会话标题"""
        if len(first_message) <= 30:
            return first_message

        # 截取前30个字符并添加省略号
        return first_message[:30] + "..."


    @staticmethod
    def clear_chat_history(db_session: Session, session_id: str,
                           user_id: Optional[str] = None) -> Dict[str, Any]:
        """清空聊天历史（保留系统消息）"""
        try:
            query = db_session.query(ChatHistory).filter(
                and_(
                    ChatHistory.session_id == session_id,
                    ChatHistory.role.in_(['user', 'assistant'])
                )
            )

            if user_id is not None:
                query = query.filter(ChatHistory.user_id == user_id)# type: ignore

            deleted_count = query.delete()
            db_session.commit()

            logger.info(f"清空聊天历史成功: {session_id}, 删除消息数: {deleted_count}")

            return {
                'success': True,
                'cleared_messages': deleted_count
            }

        except Exception as e:
            logger.error(f"清空聊天历史失败: {str(e)}")
            db_session.rollback()
            return {
                'success': False,
                'message': f'清空聊天历史失败: {str(e)}'
            }

    @staticmethod
    def update_chat_session(db_session: Session, session_id: str,
                            update_data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """更新聊天会话信息
        
        支持更新会话元数据，如：
        - title: 会话标题
        - tags: 会话标签
        - is_deleted: 软删除标记
        
        Args:
            db_session: 数据库会话
            session_id: 会话ID
            update_data: 要更新的数据字典
            user_id: 用户ID（可选，用于权限验证）
            
        Returns:
            更新结果字典
        """
        try:
            from models.models import ChatSession
            
            logger.info(f"更新聊天会话: {session_id}, 数据: {update_data}")
            
            # 查找或创建会话记录
            chat_session = db_session.query(ChatSession).filter(
                ChatSession.session_id == str(session_id)  # type: ignore
            ).first()
            
            # 如果会话不存在，创建新记录
            if not chat_session:
                # 获取会话的第一条消息作为默认标题
                first_message = db_session.query(ChatHistory).filter(
                    and_(
                        ChatHistory.session_id == session_id,
                        ChatHistory.role == 'user'
                    )
                ).order_by(ChatHistory.created_time).first()
                
                default_title = first_message.content[:30] + "..." if (
                    first_message and len(first_message.content) > 30
                ) else (first_message.content if first_message else "新会话")
                
                chat_session = ChatSession(
                    session_id=session_id,
                    title=update_data.get('title', default_title),
                    user_id=user_id,
                    created_time=datetime.now(timezone.utc),
                    updated_time=datetime.now(timezone.utc),
                    is_deleted=False
                )
                db_session.add(chat_session)
                logger.info(f"创建新会话记录: {session_id}")
            
            # 权限验证（如果指定了user_id）
            if user_id is not None and chat_session.user_id != user_id:
                logger.warning(f"用户 {user_id} 无权更新会话 {session_id}")
                return {
                    'success': False,
                    'message': '无权更新此会话'
                }
            
            # 更新允许的字段
            updated_fields = []
            
            if 'title' in update_data:
                chat_session.title = update_data['title']
                updated_fields.append('title')
            
            if 'is_deleted' in update_data:
                chat_session.is_deleted = bool(update_data['is_deleted'])
                updated_fields.append('is_deleted')
            
            # 更新时间戳
            chat_session.updated_time = datetime.now(timezone.utc)
            
            # 提交更改
            db_session.commit()
            
            logger.info(f"会话更新成功: {session_id}, 更新字段: {', '.join(updated_fields)}")
            
            return {
                'success': True,
                'session_id': session_id,
                'updated_fields': updated_fields,
                'updated_data': {
                    'title': chat_session.title,
                    'is_deleted': chat_session.is_deleted,
                    'updated_time': chat_session.updated_time.isoformat()
                }
            }

        except Exception as e:
            logger.error(f"更新聊天会话失败: {str(e)}", exc_info=True)
            db_session.rollback()
            return {
                'success': False,
                'message': f'更新聊天会话失败: {str(e)}'
            }

    @staticmethod
    def get_chat_suggestions(db_session: Session, context: Optional[str] = None) -> Dict[str, Any]:
        """获取聊天建议"""
        try:
            # 基于上下文生成聊天建议
            suggestions = []

            if context:
                # 基于上下文的智能建议
                if '测试' in context:
                    suggestions.extend([
                        "如何设计有效的测试用例？",
                        "测试策略应该包含哪些要素？",
                        "如何进行自动化测试？"
                    ])
                elif '缺陷' in context or 'bug' in context.lower():
                    suggestions.extend([
                        "如何有效地报告缺陷？",
                        "缺陷的生命周期是怎样的？",
                        "如何预防缺陷的发生？"
                    ])
                elif '性能' in context:
                    suggestions.extend([
                        "性能测试的关键指标有哪些？",
                        "如何进行负载测试？",
                        "性能优化的常见方法？"
                    ])
            else:
                # 默认建议
                suggestions = [
                    "如何开始软件测试工作？",
                    "测试用例设计的最佳实践？",
                    "自动化测试工具推荐？",
                    "如何提高测试效率？",
                    "测试报告应该包含哪些内容？"
                ]

            # 使用 db_session 进行日志记录
            _ = db_session  # 标记参数已使用
            logger.info(f"获取聊天建议成功，数据库会话状态: 活跃")

            return {
                'success': True,
                'suggestions': suggestions[:5]  # 最多返回5个建议
            }

        except Exception as e:
            logger.error(f"获取聊天建议失败: {str(e)}")
            return {
                'success': False,
                'message': f'获取聊天建议失败: {str(e)}'
            }

    @staticmethod
    def get_chat_templates(
        db_session: Session,
        template_type: Optional[str] = None,
        locale: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取聊天模板"""
        try:
            normalized_locale = str(locale or 'zh-CN').strip().lower()
            is_english = normalized_locale.startswith('en')
            templates = {
                'test_strategy': {
                    'name': 'Test Strategy Consultation' if is_english else '测试策略咨询',
                    'content': (
                        'I need to define a test strategy. The project type is [describe project type], '
                        'the main features include [list main features]. Please help me design a suitable test strategy.'
                        if is_english else
                        '我需要制定一个测试策略，项目类型是[请描述项目类型]，主要功能包括[请列出主要功能]，请帮我分析应该采用什么测试策略？'
                    )
                },
                'case_review': {
                    'name': 'Test Case Review Advice' if is_english else '用例评审建议',
                    'content': (
                        'I need to review the following test cases:\n'
                        '[paste test cases]\n\n'
                        'Please evaluate whether these cases are complete and suggest improvements.'
                        if is_english else
                        '我有一些测试用例需要评审，用例内容如下：\n[请粘贴测试用例]\n\n请帮我分析这些用例是否完整，有什么改进建议？'
                    )
                },
                'bug_analysis': {
                    'name': 'Bug Analysis Guidance' if is_english else '缺陷分析指导',
                    'content': (
                        'I encountered a defect. The symptom is [describe symptom], and the reproduction steps are '
                        '[describe steps]. Please help analyze possible root causes and solutions.'
                        if is_english else
                        '我遇到了一个缺陷，现象是[请描述缺陷现象]，出现的步骤是[请描述重现步骤]，请帮我分析可能的原因和解决方案。'
                    )
                },
                'automation_advice': {
                    'name': 'Automation Advice' if is_english else '自动化建议',
                    'content': (
                        'I want to automate testing for [describe module]. The current tech stack is '
                        '[describe tech stack]. Please recommend an appropriate automation testing approach.'
                        if is_english else
                        '我想对[请描述功能模块]进行自动化测试，目前的技术栈是[请描述技术栈]，请推荐合适的自动化测试方案。'
                    )
                },
                'performance_test': {
                    'name': 'Performance Test Guidance' if is_english else '性能测试指导',
                    'content': (
                        'I need to run performance tests for [describe system], expected concurrent users are '
                        '[enter number]. Please help me draft a performance testing plan.'
                        if is_english else
                        '我需要对[请描述系统]进行性能测试，预期的用户并发量是[请填写数字]，请帮我制定性能测试方案。'
                    )
                }
            }

            _ = db_session
            
            if template_type and template_type in templates:
                template_name = templates[template_type]['name']
                logger.info(f"获取聊天模板成功，切换模板类型: {template_name} (类型: {template_type})，数据库会话状态: 活跃")
                return {
                    'success': True,
                    'templates': [templates[template_type]]
                }

            # 获取所有模板名称
            template_names = [t['name'] for t in templates.values()]
            logger.info(f"获取聊天模板成功，模板类型: {', '.join(template_names)}，数据库会话状态: 活跃")
            return {
                'success': True,
                'templates': templates
            }

        except Exception as e:
            logger.error(f"获取聊天模板失败: {str(e)}")
            return {
                'success': False,
                'message': f'获取聊天模板失败: {str(e)}'
            }

    @staticmethod
    def export_chat_history(db_session: Session, session_id: str,
                            export_format: str = 'json', user_id: Optional[str] = None) -> Dict[str, Any]:
        """导出聊天历史"""
        try:
            # 获取聊天历史
            query = db_session.query(ChatHistory).filter(
                and_(
                    ChatHistory.session_id == session_id,
                    ChatHistory.role.in_(['user', 'assistant'])
                )
            )

            if user_id is not None:
                query = query.filter(ChatHistory.user_id == user_id)# type: ignore

            messages = query.order_by(ChatHistory.created_time).all()

            if not messages:
                return {
                    'success': False,
                    'message': '没有找到聊天记录'
                }

            # 根据格式导出
            if export_format.lower() == 'json':
                export_data = {
                    'session_id': session_id,
                    'export_time': datetime.now(timezone.utc).isoformat(),
                    'message_count': len(messages),
                    'messages': [
                        {
                            'role': msg.role,
                            'content': msg.content,
                            'timestamp': msg.created_time.isoformat()
                        }
                        for msg in messages
                    ]
                }

                return {
                    'success': True,
                    'data': export_data,
                    'format': 'json'
                }

            elif export_format.lower() == 'txt':
                # 生成文本格式
                lines = [
                    f"聊天记录导出 - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
                    f"会话ID: {session_id}",
                    f"消息数量: {len(messages)}",
                    "=" * 50,
                    ""
                ]

                for msg in messages:
                    role_name = "用户" if msg.role == "user" else "助手"
                    timestamp = msg.created_time.strftime('%Y-%m-%d %H:%M:%S')
                    lines.extend([
                        f"[{timestamp}] {role_name}:",
                        msg.content,
                        ""
                    ])

                export_text = "\n".join(lines)

                return {
                    'success': True,
                    'data': export_text,
                    'format': 'txt'
                }

            else:
                return {
                    'success': False,
                    'message': f'不支持的导出格式: {export_format}'
                }

        except Exception as e:
            logger.error(f"导出聊天历史失败: {str(e)}")
            return {
                'success': False,
                'message': f'导出聊天历史失败: {str(e)}'
            }

    @staticmethod
    def get_chat_statistics(db_session: Session, days: int = 30) -> Dict[str, Any]:
        """获取聊天统计信息"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            # 总会话数
            total_sessions = db_session.query(
                func.count(func.distinct(ChatHistory.session_id))
            ).scalar() or 0

            # 总消息数
            total_messages = db_session.query(ChatHistory).filter(
                ChatHistory.role.in_(['user', 'assistant'])
            ).count()

            # 最近活动
            recent_sessions = db_session.query(
                func.count(func.distinct(ChatHistory.session_id))
            ).filter(
                ChatHistory.created_time >= cutoff_date
            ).scalar() or 0

            recent_messages = db_session.query(ChatHistory).filter(
                and_(
                    ChatHistory.created_time >= cutoff_date,
                    ChatHistory.role.in_(['user', 'assistant'])
                )
            ).count()

            # 平均会话长度
            avg_session_length = db_session.query(
                func.avg(func.count(ChatHistory.id))
            ).select_from(
                db_session.query(ChatHistory.session_id).filter(
                    ChatHistory.role.in_(['user', 'assistant'])
                ).group_by(ChatHistory.session_id).subquery()
            ).scalar() or 0

            return {
                'success': True,
                'statistics': {
                    'total_sessions': total_sessions,
                    'total_messages': total_messages,
                    'recent_sessions': recent_sessions,
                    'recent_messages': recent_messages,
                    'avg_session_length': round(float(avg_session_length), 2),
                    'period_days': days
                }
            }

        except Exception as e:
            logger.error(f"获取聊天统计失败: {str(e)}")
            return {
                'success': False,
                'message': f'获取聊天统计失败: {str(e)}'
            }


def delete_chat_session(db_session: Session, session_id: str,
                        user_id: Optional[str] = None) -> Dict[str, Any]:
    """删除聊天会话"""
    try:
        query = db_session.query(ChatHistory).filter(
            ChatHistory.session_id == session_id# type: ignore
        )

        if user_id is not None:
            query = query.filter(ChatHistory.user_id == user_id)

        deleted_count = query.delete()
        db_session.commit()

        logger.info(f"删除聊天会话成功: {session_id}, 删除消息数: {deleted_count}")

        return {
            'success': True,
            'deleted_messages': deleted_count
        }

    except Exception as e:
        logger.error(f"删除聊天会话失败: {str(e)}")
        db_session.rollback()
        return {
            'success': False,
            'message': f'删除聊天会话失败: {str(e)}'
        }
