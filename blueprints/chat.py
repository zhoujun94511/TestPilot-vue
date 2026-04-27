#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import uuid
from sqlalchemy import and_, func
from datetime import datetime, timezone
from werkzeug.exceptions import BadRequest
from flask import (
    Blueprint,
    request,
    jsonify,
    current_app,
    session,
    has_app_context,
)
from models.models import db, ChatHistory, ChatSession
from services.chat_service import ChatService
from services.action_message_service import build_compact_action_history_content
from utils.utils_ai_models.smart_quick_reply_generator import SmartQuickReplyGenerator
from utils.utils_ai_models.get_llm import get_llm
from utils.utils_core.api_error_handler import check_api_key_configuration, get_service_name
from utils.utils_core.api_error_handler import build_internal_error_result
from config.settings import settings as config_settings

# 创建蓝图
chat_bp = Blueprint('chat', __name__)

# 初始化服务
chat_service = ChatService()


def get_session_id():
    """获取或创建会话ID"""
    if 'chat_session_id' not in session:
        session['chat_session_id'] = str(uuid.uuid4())
    return session['chat_session_id']

def get_flask_app():
    if has_app_context():
        return current_app
    raise RuntimeError("No Flask application context available")


@chat_bp.route('/message', methods=['POST'])
def send_message():
    """发送聊天消息"""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("请求数据不能为空")

        user_message = data.get('message', '').strip()
        if not user_message:
            raise BadRequest("消息内容不能为空")

        mode = str(data.get('mode', 'chat')).strip().lower()
        if mode == 'action':
            if not getattr(config_settings, 'ENABLE_EXPERIMENTAL_ACTIONS', False):
                return jsonify({
                    'success': False,
                    'message': '实验动作功能未启用',
                    'error': 'feature_disabled'
                }), 403
            session_id = data.get('session_id') or get_session_id()
            message_type = data.get('type', 'chat')
            chat_session = ChatSession.query.filter_by(session_id=session_id).first()
            if not chat_session:
                session_title = user_message[:50] + '...' if len(user_message) > 50 else user_message
                if not session_title.strip():
                    session_title = '新会话'
                chat_session = ChatSession(
                    session_id=session_id,
                    title=session_title,
                    created_time=datetime.now(timezone.utc),
                    updated_time=datetime.now(timezone.utc),
                    is_deleted=False
                )
                db.session.add(chat_session)
            elif chat_session.is_deleted:
                chat_session.is_deleted = False
            user_msg = ChatHistory(
                session_id=session_id,
                role="user",
                content=user_message,
                message_type=message_type,
                created_time=datetime.now(timezone.utc)
            )
            db.session.add(user_msg)
            chat_session.updated_time = datetime.now(timezone.utc)
            db.session.commit()

            from experiments.action_runtime.orchestrator import ExperimentalActionOrchestrator
            from experiments.action_runtime.schemas import ActionRequest
            action_orchestrator = ExperimentalActionOrchestrator()
            action_result = action_orchestrator.run(ActionRequest(
                query=user_message,
                session_id=session_id,
                user_id=data.get('user_id'),
                require_confirmation=bool(data.get('require_confirmation', True)),
                metadata=data.get('metadata') if isinstance(data.get('metadata'), dict) else {}
            ))
            action_response_text = build_compact_action_history_content(action_result)
            action_msg = ChatHistory(
                session_id=session_id,
                role="system",
                content=action_response_text,
                message_type=message_type,
                created_time=datetime.now(timezone.utc),
                tokens_used=0,
                model_name='experimental-action'
            )
            db.session.add(action_msg)
            if chat_session:
                chat_session.updated_time = datetime.now(timezone.utc)
            db.session.commit()
            return jsonify({
                'success': action_result.success,
                'mode': 'action',
                'session_id': session_id,
                'execution_id': action_result.execution_id,
                'status': action_result.status,
                'message': action_result.message,
                'action_plan': {
                    'intent': action_result.plan.intent if action_result.plan else None,
                    'tool_name': action_result.plan.tool_name if action_result.plan else None,
                    'args': action_result.plan.args if action_result.plan else None,
                    'risk_level': action_result.plan.risk_level if action_result.plan else None,
                    'requires_confirmation': action_result.plan.requires_confirmation if action_result.plan else None,
                    'reason': action_result.plan.reason if action_result.plan else None,
                } if action_result.plan else None,
                'tool_results': action_result.tool_output,
                'error': action_result.error,
                'timestamp': action_result.created_at
            }), (200 if action_result.success else 500)

        # 获取会话参数
        session_id = data.get('session_id') or get_session_id()
        message_type = data.get('type', 'chat')  # chat, test_case, requirement_analysis
        temperature = data.get('temperature', 0.7)

        # 从前端参数读取；无向量库模式时强制关闭 RAG/知识库增强
        use_context = bool(data.get('use_context', False))
        use_knowledge = bool(data.get('use_knowledge', False))
        use_rag = bool(data.get('use_rag', False))
        if not getattr(config_settings, 'ENABLE_VECTOR_STORE', True):
            use_rag = False
            use_knowledge = False

        chat_session = ChatSession.query.filter_by(session_id=session_id).first()
        if not chat_session:
            session_title = user_message[:50] + '...' if len(user_message) > 50 else user_message
            if not session_title.strip():
                session_title = '新会话'

            chat_session = ChatSession(
                session_id=session_id,
                title=session_title,
                created_time=datetime.now(timezone.utc),
                updated_time=datetime.now(timezone.utc),
                is_deleted=False
            )
            db.session.add(chat_session)

        user_msg = ChatHistory(
            session_id=session_id,
            role="user",
            content=user_message,
            message_type=message_type,
            created_time=datetime.now(timezone.utc)
        )
        db.session.add(user_msg)

        if chat_session:
            chat_session.updated_time = datetime.now(timezone.utc)

        db.session.commit()

        if not hasattr(chat_service, 'llm') or chat_service.llm is None:
            flask_app = get_flask_app()
            llm = getattr(flask_app, 'llm', None)
            vector_db = getattr(flask_app, 'vector_db', None)

            init_error_message = ''
            if llm is None:
                try:
                    llm = get_llm(config_settings.DEFAULT_COMPANY, use_case='chat')
                    flask_app.llm = llm
                except Exception as init_error:
                    current_app.logger.error(f"聊天LLM延迟初始化失败: {init_error}")
                    init_error_message = str(init_error)
                    llm = None

            if llm is None:
                message = '聊天模型尚未初始化，请检查配置中心中的模型服务商与 API Key 后重试'
                if init_error_message:
                    message = f'{message}（{init_error_message}）'
                return jsonify({
                    'success': False,
                    'message': message,
                    'error': 'llm_not_initialized',
                    'details': 'llm_not_initialized',
                    'session_id': session_id
                }), 503

            chat_service.initialize(llm, vector_db)

        # 构建设置参数
        settings = {
            'temperature': temperature,
            'max_tokens': data.get('max_tokens', getattr(config_settings, 'MAX_TOKENS', 4000)),
            'use_rag': use_rag,
            'message_type': message_type,
            'use_smart_reply': bool(data.get('use_smart_reply', False)),
            'auto_suggest': bool(data.get('auto_suggest', True))
        }

        # 发送消息给AI助手
        result = chat_service.send_message(
            db_session=db.session,
            session_id=session_id,
            message=user_message,
            user_settings=settings,
            use_context=use_context,
            use_knowledge=use_knowledge,
            save_user_message=False
        )

        if result.get('success'):
            response_text = result.get('message') or result.get('response')
            return jsonify({
                'success': True,
                'response': response_text,
                'session_id': session_id,
                'message_id': result.get('message_id'),
                'tokens_used': result.get('tokens_used', 0),
                'model_name': result.get('model_name'),
                'timestamp': result.get('timestamp'),
                'suggestions': result.get('suggestions', [])
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', '消息发送失败'),
                'error': result.get('error')
            }), 500

    except BadRequest as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'error': 'bad_request'
        }), 400
    except Exception as e:
        current_app.logger.error(f"发送聊天消息失败: {e}")
        error_payload = build_internal_error_result(message='发送消息失败')
        return jsonify({
            'success': False,
            'message': error_payload['message'],
            'error': error_payload['error'],
            'error_code': error_payload['error_code'],
            'retryable': error_payload['retryable']
        }), error_payload['status_code']


@chat_bp.route('/stream', methods=['GET', 'POST'])
def send_stream_message():
    """发送流式聊天消息 (SSE)"""
    try:
        # 解析输入参数
        if request.method == 'GET':
            data = {
                'message': request.args.get('message', ''),
                'session_id': request.args.get('session_id'),
                'type': request.args.get('type', 'chat'),
                'use_rag': request.args.get('use_rag', 'false').lower() == 'true',
                'use_context': request.args.get('use_context', 'false').lower() == 'true',
                'use_knowledge': request.args.get('use_knowledge', 'false').lower() == 'true',
                'use_smart_reply': request.args.get('use_smart_reply', 'false').lower() == 'true',
                'auto_suggest': request.args.get('auto_suggest', 'true').lower() == 'true',
                'temperature': float(request.args.get('temperature', 0.7))
            }
            try:
                settings = json.loads(request.args.get('settings', '{}'))
                if not isinstance(settings, dict):
                    settings = {}
            except Exception as e:
                current_app.logger.warning(f"解析settings参数失败: {e}")
                settings = {}
        else:
            data = request.get_json() or {}
            settings = data.get('settings', {})

        user_message = data.get('message', '').strip()
        if not user_message:
            raise BadRequest("消息内容不能为空")

        session_id = data.get('session_id') or get_session_id()
        message_type = data.get('type', 'chat')
        use_context = bool(data.get('use_context', False))
        use_knowledge = bool(data.get('use_knowledge', False))
        use_smart_reply = bool(data.get('use_smart_reply', False))
        temperature = data.get('temperature', 0.7)

        settings.update({
            "temperature": temperature,
            "use_rag": data.get("use_rag", False),
            "message_type": message_type,
            "use_smart_reply": use_smart_reply,
            "auto_suggest": bool(data.get("auto_suggest", True))
        })

        # 在生成器外部初始化服务并保存用户消息
        if not hasattr(chat_service, 'llm') or chat_service.llm is None:
            llm = getattr(current_app, 'llm', None)
            vector_db = getattr(current_app, 'vector_db', None)
            init_error_message = ""
            if llm is None:
                current_company = str(getattr(config_settings, 'DEFAULT_COMPANY', 'OPENAI') or 'OPENAI').upper()
                key_ok, key_message = check_api_key_configuration(current_company)
                if not key_ok:
                    provider_name = get_service_name(current_company.lower())
                    return jsonify({
                        "success": False,
                        "message": f"{provider_name} 配置异常：{key_message}",
                        "error": "llm_not_initialized",
                        "details": "api_key_invalid_or_missing",
                        "session_id": session_id
                    }), 503
                try:
                    llm = get_llm(current_company, use_case='chat')
                    current_app.llm = llm
                except Exception as init_error:
                    current_app.logger.error(f"流式聊天LLM延迟初始化失败: {init_error}")
                    init_error_message = str(init_error)
                    llm = None

            if llm is None:
                message = "聊天模型尚未初始化，请检查配置中心中的模型服务商与 API Key 后重试"
                if init_error_message:
                    message = f"{message}（{init_error_message}）"
                return jsonify({
                    "success": False,
                    "message": message,
                    "error": "llm_not_initialized",
                    "details": "llm_not_initialized",
                    "session_id": session_id
                }), 503
            chat_service.initialize(llm, vector_db)

        # 在生成器外部保存用户消息
        # 双保险：若会话不存在则创建；若会话被软删除则自动恢复
        chat_session = ChatSession.query.filter_by(session_id=session_id).first()
        if not chat_session:
            # 生成会话标题（使用用户消息的前50个字符）
            session_title = user_message[:50] + '...' if len(user_message) > 50 else user_message
            if not session_title.strip():
                session_title = '新会话'

            chat_session = ChatSession(
                session_id=session_id,
                title=session_title,
                created_time=datetime.now(timezone.utc),
                updated_time=datetime.now(timezone.utc),
                is_deleted=False
            )
            db.session.add(chat_session)
        elif chat_session.is_deleted:
            # 软删除会话被再次使用时恢复
            chat_session.is_deleted = False
            if not (chat_session.title or '').strip():
                chat_session.title = user_message[:50] + '...' if len(user_message) > 50 else (user_message or '新会话')
            chat_session.updated_time = datetime.now(timezone.utc)

        # 在生成器外部保存用户消息
        user_msg = ChatHistory(
            session_id=session_id,
            role="user",
            content=user_message,
            message_type=message_type,
            created_time=datetime.now(timezone.utc)
        )
        db.session.add(user_msg)
        
        # 更新会话的最后更新时间
        if chat_session:
            chat_session.updated_time = datetime.now(timezone.utc)
        
        db.session.commit()

        # 在用户消息保存后获取上下文 - 转换为字典避免会话绑定问题
        context_messages = []
        if use_context:
            try:
                context_objects = db.session.query(ChatHistory).filter(
                    and_(
                        ChatHistory.session_id == session_id,
                        ChatHistory.role.in_(['user', 'assistant'])
                    )
                ).order_by(ChatHistory.created_time.desc()).limit(20).all()

                # 转换为字典，避免会话绑定问题
                context_messages = [
                    {
                        'role': msg.role,
                        'content': msg.content,
                        'created_time': msg.created_time
                    }
                    for msg in reversed(context_objects)
                ]
            except Exception as e:
                current_app.logger.error(f"获取对话上下文失败: {str(e)}")
                context_messages = []

        # 在生成器外部收集AI响应内容
        ai_response_content = ""
        ai_tokens_used = 0
        ai_model_name = "unknown"

        def generate_response():
            """生成器函数 - 仅负责流式输出"""
            nonlocal ai_response_content, ai_tokens_used, ai_model_name

            try:
                # 传递已获取的上下文
                response_generator = chat_service.stream_message(
                    db_session=db.session,
                    session_id=session_id,
                    message=user_message,
                    user_settings=settings,
                    use_context=use_context,
                    use_knowledge=use_knowledge,
                    context_messages=context_messages
                )

                if response_generator is None:
                    yield "data: {\"type\": \"error\", \"message\": \"服务未返回生成器\"}\n\n"
                    return

                # 直接转发流式事件，同时收集AI响应内容
                for stream_chunk in response_generator:
                    # 解析chunk内容，提取AI响应
                    if stream_chunk.startswith("data: "):
                        try:
                            chunk_data = json.loads(stream_chunk[6:])  # 去掉"data: "前缀
                            if chunk_data.get("type") == "chunk" and "content" in chunk_data:
                                ai_response_content += chunk_data["content"]
                            elif chunk_data.get("type") == "end":
                                ai_tokens_used = int(chunk_data.get("tokens_used", 0) or 0)
                                ai_model_name = str(chunk_data.get("model_name") or "unknown")
                        except (json.JSONDecodeError, KeyError, TypeError):
                            pass  # 忽略解析错误
                    yield stream_chunk

            except Exception as stream_error:
                yield f"data: {json.dumps({'type': 'error', 'message': str(stream_error)}, ensure_ascii=False)}\n\n"

        # 执行生成器并收集所有响应
        response_chunks = []
        for response_chunk in generate_response():
            response_chunks.append(response_chunk)

        # 在应用上下文中保存AI消息
        if ai_response_content.strip():
            try:
                ai_message = ChatHistory(
                    session_id=session_id,
                    role="assistant",
                    content=ai_response_content,
                    message_type=message_type,
                    created_time=datetime.now(timezone.utc),
                    tokens_used=ai_tokens_used,
                    model_name=ai_model_name
                )
                db.session.add(ai_message)
                db.session.commit()
                current_app.logger.info(f"AI消息已保存: session_id={session_id}")
            except Exception as save_error:
                current_app.logger.error(f"保存AI消息失败: {save_error}")

        # 返回收集到的所有响应块
        def final_generator():
            for final_chunk in response_chunks:
                yield final_chunk

        return current_app.response_class(
            final_generator(),
            mimetype="text/event-stream; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Content-Type": "text/event-stream; charset=utf-8"
            }
        )

    except BadRequest as e:
        return jsonify({"success": False, "message": str(e), "error": "bad_request"}), 400
    except Exception as e:
        current_app.logger.error(f"流式聊天消息处理失败: {e}")
        error_payload = build_internal_error_result(message='流式聊天消息处理失败')
        return jsonify({
            "success": False,
            "message": error_payload["message"],
            "error": error_payload["error"],
            "error_code": error_payload["error_code"],
            "retryable": error_payload["retryable"]
        }), error_payload["status_code"]



@chat_bp.route('/history', methods=['GET'])
def get_chat_history():
    """获取聊天历史"""
    try:
        # 获取查询参数
        session_id = request.args.get('session_id') or get_session_id()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        message_type = request.args.get('type')

        # 构建查询
        query = ChatHistory.query.filter(ChatHistory.session_id == session_id)

        if message_type:
            query = query.filter(ChatHistory.message_type == message_type)

        # 排序和分页
        query = query.order_by(ChatHistory.created_time.asc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # 转换为字典格式
        messages = [record.to_dict() for record in pagination.items]

        return jsonify({
            'success': True,
            'messages': messages,
            'session_id': session_id,
            'total_messages': pagination.total,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        })

    except Exception as e:
        current_app.logger.error(f"获取聊天历史失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取聊天历史失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@chat_bp.route('/clear', methods=['POST'])
def clear_chat_history():
    """清空聊天历史"""
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id') or get_session_id()

        # 删除指定会话的所有消息
        deleted_count = ChatHistory.query.filter(
            ChatHistory.session_id == session_id
        ).delete()

        db.session.commit()

        # 如果是当前会话，重新生成会话ID
        if session_id == session.get('chat_session_id'):
            session.pop('chat_session_id', None)

        return jsonify({
            'success': True,
            'message': f'已清空聊天历史，共删除{deleted_count}条消息',
            'deleted_count': deleted_count
        })

    except Exception as e:
        current_app.logger.error(f"清空聊天历史失败: {e}")
        return jsonify({
            'success': False,
            'message': '清空聊天历史失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@chat_bp.route('/session/<session_id>', methods=['DELETE'])
def delete_chat_session(session_id):
    """删除指定的聊天会话"""
    try:
        current_app.logger.info(f"开始删除会话: {session_id}")

        # 查找会话记录
        chat_session = ChatSession.query.filter_by(session_id=session_id).first()
        if not chat_session:
            return jsonify({
                'success': False,
                'message': '会话不存在'
            }), 404

        # 软删除：标记为已删除，不删除消息记录
        chat_session.is_deleted = True
        chat_session.updated_time = datetime.now(timezone.utc)

        db.session.commit()

        current_app.logger.info(f"会话 {session_id} 已标记为删除")

        return jsonify({
            'success': True,
            'message': '会话删除成功',
            'deleted_count': 1
        })

    except Exception as e:
        current_app.logger.error(f"删除聊天会话失败: {e}")
        return jsonify({
            'success': False,
            'message': '删除会话失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@chat_bp.route('/session/<session_id>', methods=['PUT'])
def update_chat_session(session_id):
    """更新聊天会话"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400

        # 查找会话记录
        chat_session = ChatSession.query.filter_by(session_id=session_id).first()
        if not chat_session:
            return jsonify({
                'success': False,
                'message': '会话不存在'
            }), 404

        # 更新会话信息
        if 'title' in data:
            chat_session.title = data['title']

        chat_session.updated_time = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '会话更新成功',
            'session': {
                'session_id': session_id,
                'title': chat_session.title,
                'updated_time': chat_session.updated_time.isoformat()
            }
        })

    except Exception as e:
        current_app.logger.error(f"更新聊天会话失败: {e}")
        return jsonify({
            'success': False,
            'message': '更新会话失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@chat_bp.route('/suggestions', methods=['POST'])
def get_chat_suggestions():
    """获取聊天建议"""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("请求数据不能为空")

        context = data.get('context', '')

        # 获取建议
        result = chat_service.get_chat_suggestions(
            db_session=db.session,
            context=context
        )

        if result['success']:
            return jsonify({
                'success': True,
                'suggestions': result['suggestions']
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', '获取建议失败'),
                'error': result.get('error')
            }), 500

    except BadRequest as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'error': 'bad_request'
        }), 400
    except Exception as e:
        current_app.logger.error(f"获取聊天建议失败: {e}")
        return jsonify({
                'success': False,
                'message': '获取建议失败',
                'error': 'INTERNAL_SERVER_ERROR',
                'error_code': 'INTERNAL_SERVER_ERROR',
                'retryable': False
        }), 500


@chat_bp.route('/quick-reply/feedback', methods=['POST'])
def track_quick_reply_feedback():
    """跟踪快速回复的用户反馈"""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("请求数据不能为空")

        suggestion_text = data.get('suggestion_text', '').strip()
        was_clicked = data.get('was_clicked', False)
        user_id = data.get('user_id', 'anonymous')
        session_id = data.get('session_id', '')

        if not suggestion_text:
            raise BadRequest("建议文本不能为空")

        # 更新用户偏好
        generator = SmartQuickReplyGenerator()
        generator.update_user_preferences(user_id, suggestion_text, was_clicked)

        current_app.logger.info(f"快速回复反馈记录: user={user_id}, session={session_id}, suggestion='{suggestion_text}', clicked={was_clicked}")

        return jsonify({
            'success': True,
            'message': '反馈记录成功'
        })

    except BadRequest as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'error': 'bad_request'
        }), 400
    except Exception as e:
        current_app.logger.error(f"快速回复反馈记录失败: {e}")
        return jsonify({
            'success': False,
            'message': '反馈记录失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@chat_bp.route('/quick-reply/stats', methods=['GET'])
def get_quick_reply_stats():
    """获取快速回复统计信息"""
    try:
        
        generator = SmartQuickReplyGenerator()
        stats = generator.get_suggestion_statistics()

        return jsonify({
            'success': True,
            'statistics': stats
        })

    except Exception as e:
        current_app.logger.error(f"获取快速回复统计失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取统计信息失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@chat_bp.route('/templates', methods=['GET'])
def get_chat_templates():
    """获取聊天模板"""
    try:
        message_type = request.args.get('type', 'chat')
        locale = request.args.get('locale') or request.headers.get('Accept-Language', 'zh-CN')

        # 获取模板
        result = chat_service.get_chat_templates(
            db_session=db.session,
            template_type=message_type,
            locale=locale
        )

        if result['success']:
            return jsonify({
                'success': True,
                'templates': result['templates']
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', '获取模板失败'),
                'error': result.get('error')
            }), 500

    except Exception as e:
        current_app.logger.error(f"获取聊天模板失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取模板失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@chat_bp.route('/sessions', methods=['GET', 'POST'])
def handle_sessions():
    """处理聊天会话的获取和创建"""
    if request.method == 'GET':
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            
            # 防止除零错误：确保 per_page 至少为 1
            if per_page <= 0:
                per_page = 20  # 使用默认值
            
            # 防止 page 为负数或0
            if page < 1:
                page = 1

            # 基于会话表分页，避免在会话列表接口中全量扫描 ChatHistory
            base_query = ChatSession.query.filter(
                ChatSession.is_deleted == False
            ).order_by(ChatSession.updated_time.desc())

            # 如果请求大数量（如1000），则返回所有会话
            if per_page >= 1000:
                sessions_data = base_query.all()
                total_sessions = len(sessions_data)
                page = 1
                per_page = max(total_sessions, 1)
                offset = 0
            else:
                offset = (page - 1) * per_page
                sessions_data = base_query.offset(offset).limit(per_page).all()
                total_sessions = base_query.count()

            session_ids = [item.session_id for item in sessions_data]
            message_count_map = {}
            first_message_map = {}

            if session_ids:
                # 批量获取当前页每个会话的消息数
                count_rows = db.session.query(
                    ChatHistory.session_id,
                    func.count(ChatHistory.id).label('message_count')
                ).filter(
                    ChatHistory.session_id.in_(session_ids)
                ).group_by(ChatHistory.session_id).all()
                message_count_map = {row.session_id: int(row.message_count or 0) for row in count_rows}

                # 批量获取当前页每个会话的首条消息内容（用于展示标题）
                first_message_subquery = db.session.query(
                    ChatHistory.session_id,
                    func.min(ChatHistory.created_time).label('first_message_time')
                ).filter(
                    ChatHistory.session_id.in_(session_ids)
                ).group_by(ChatHistory.session_id).subquery()

                first_rows = db.session.query(
                    ChatHistory.session_id,
                    ChatHistory.content
                ).join(
                    first_message_subquery,
                    and_(
                        ChatHistory.session_id == first_message_subquery.c.session_id,
                        ChatHistory.created_time == first_message_subquery.c.first_message_time
                    )
                ).all()
                first_message_map = {row.session_id: row.content for row in first_rows if row.content}

            session_list = []
            for chat_session in sessions_data:
                title_raw = first_message_map.get(chat_session.session_id) or chat_session.title or '新会话'
                title = (title_raw[:50] + '...') if len(title_raw) > 50 else title_raw

                formatted_time = None
                if chat_session.updated_time:
                    formatted_time = chat_session.updated_time.replace(tzinfo=timezone.utc).isoformat()

                session_list.append({
                    'session_id': chat_session.session_id,
                    'title': title,
                    'last_activity': formatted_time,
                    'message_count': message_count_map.get(chat_session.session_id, 0),
                    'total_tokens': 0  # 暂时设为0
                })

            # 安全计算总页数：防止除零错误
            if per_page > 0:
                total_pages = (total_sessions + per_page - 1) // per_page
            else:
                total_pages = 1 if total_sessions > 0 else 0
            
            return jsonify({
                'success': True,
                'sessions': session_list,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_sessions,
                    'pages': total_pages,
                    'has_prev': page > 1,
                    'has_next': offset + per_page < total_sessions if per_page > 0 else False
                }
            })

        except Exception as e:
            current_app.logger.error(f"获取聊天会话列表失败: {e}")
            return jsonify({
                'success': False,
                'message': '获取会话列表失败',
                'error': 'INTERNAL_SERVER_ERROR',
                'error_code': 'INTERNAL_SERVER_ERROR',
                'retryable': False
            }), 500

    elif request.method == 'POST':
        # 创建新聊天会话（保持你原有返回结构）
        try:
            data = request.get_json() or {}
            session_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            # 真实落库，避免前端拿到 session_id 但会话列表查询不到
            chat_session = ChatSession(
                session_id=session_id,
                title=data.get('title', '新会话') or '新会话',
                created_time=now,
                updated_time=now,
                is_deleted=False
            )
            db.session.add(chat_session)
            db.session.commit()

            new_session = {
                'session_id': session_id,
                'title': chat_session.title,
                'created_time': now.isoformat(),
                'message_count': 0,
                'total_tokens': 0
            }

            return jsonify({
                'success': True,
                'session_id': session_id,
                'session': new_session
            })

        except Exception as e:
            current_app.logger.error(f"创建聊天会话失败: {e}")
            return jsonify({
                'success': False,
                'message': '创建会话失败',
                'error': 'INTERNAL_SERVER_ERROR',
                'error_code': 'INTERNAL_SERVER_ERROR',
                'retryable': False
            }), 500

    else:
        return jsonify({
            'success': False,
            'message': '不支持的HTTP方法',
            'error': f'方法 {request.method} 不被支持'
        }), 405


@chat_bp.route('/template/<template_type>', methods=['GET'])
def get_chat_template(template_type):
    """获取单个聊天模板"""
    try:
        locale = request.args.get('locale') or request.headers.get('Accept-Language', 'zh-CN')
        result = chat_service.get_chat_templates(
            db_session=db.session,
            template_type=template_type,
            locale=locale
        )

        if result['success'] and result['templates']:
            template = result['templates'][0]
            return jsonify({
                'success': True,
                'template': template
            })
        else:
            return jsonify({
                'success': False,
                'message': '模板不存在',
                'error': 'template_not_found'
            }), 404

    except Exception as e:
        current_app.logger.error(f"获取聊天模板失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取模板失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@chat_bp.route('/config', methods=['GET'])
def get_chat_config():
    """获取聊天配置"""
    try:
        from config.settings import settings

        return jsonify({
            'success': True,
            'config': {
                'company': settings.DEFAULT_COMPANY,
                'default_model': settings.current_model,
                'available_models': settings.available_models,
                'capabilities': settings.model_capabilities,
                'default_temperature': 0.7,
                'default_max_tokens': getattr(settings, 'MAX_TOKENS', 4000),
                'experimental_actions_enabled': bool(getattr(settings, 'ENABLE_EXPERIMENTAL_ACTIONS', False))
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取聊天配置失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取配置失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@chat_bp.route('/save-ai-message', methods=['POST'])
def save_ai_message():
    """保存AI响应消息（在有应用上下文的环境中执行）"""
    try:
        print("=== 开始保存AI消息 ===")
        data = request.get_json()
        print(f"接收到的数据: {data}")

        session_id = data.get('session_id')
        content = data.get('content', '')
        print(f"session_id: {session_id}, content_length: {len(content)}")

        current_app.logger.info(f"保存AI消息: session_id={session_id}, content_length={len(content)}")

        if not session_id or not content:
            print("参数不完整")
            current_app.logger.warning(f"参数不完整: session_id={session_id}, content_length={len(content)}")
            return jsonify({'success': False, 'message': '参数不完整'}), 400

        print("开始创建ChatHistory对象")
        ai_msg = ChatHistory(
            session_id=session_id,
            role="assistant",
            content=content,
            message_type=data.get('message_type', 'chat'),
            tokens_used=data.get('tokens_used', 0),
            model_name=data.get('model_name', 'unknown'),
            created_time=datetime.now(timezone.utc)
        )
        print("ChatHistory对象创建成功")

        print("开始添加到数据库")
        db.session.add(ai_msg)
        
        # 更新会话的最后更新时间
        chat_session = ChatSession.query.filter_by(session_id=session_id).first()
        if chat_session:
            chat_session.updated_time = datetime.now(timezone.utc)
        
        print("开始提交事务")
        db.session.commit()
        print("事务提交成功")

        current_app.logger.info(f"AI消息保存成功: message_id={ai_msg.id}")
        print(f"=== AI消息保存成功: message_id={ai_msg.id} ===")
        return jsonify({'success': True, 'message_id': ai_msg.id})

    except Exception as e:
        print(f"=== 保存AI消息失败: {e} ===")
        current_app.logger.error(f"保存AI消息失败: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
