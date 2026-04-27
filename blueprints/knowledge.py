#!/usr/bin/python
# -*- coding: utf-8 -*-
import ast
import uuid
from pathlib import Path
from datetime import datetime
from werkzeug.exceptions import BadRequest
from models.models import db, RagFileRecord
from services.knowledge_service import KnowledgeService
from flask import Blueprint, request, jsonify, current_app
from utils.utils_core.path_helper import get_knowledge_uploads_path
from config.settings import settings as config_settings

# 创建蓝图
knowledge_bp = Blueprint('knowledge', __name__)

# 初始化服务
knowledge_service = KnowledgeService()


@knowledge_bp.before_request
def _disable_knowledge_when_vector_store_off():
    """
    ENABLE_VECTOR_STORE=false 时禁用知识库相关接口。
    知识库属于强关联模块：无向量库时仅允许其他模块降级运行。
    """
    if not getattr(config_settings, 'ENABLE_VECTOR_STORE', True):
        return jsonify({
            'success': False,
            'message': '知识库功能已禁用（ENABLE_VECTOR_STORE=false）',
            'error': 'vector_store_disabled'
        }), 403
    return None  # 继续执行后续路由


def allowed_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def _safe_filename(input_filename: str) -> str:
    """创建安全的文件名，保留中文字符"""
    import os
    import re

    name, ext = os.path.splitext(input_filename)
    safe_name = re.sub(r'[^\w\u4e00-\u9fff\-_]', '_', name)
    safe_name = re.sub(r'_+', '_', safe_name)
    safe_name = safe_name.strip('_')
    if not safe_name:
        safe_name = 'document'
    return safe_name + ext


def _safe_folder_name(folder_name: str) -> str:
    """创建安全的文件夹名称"""
    import re

    safe_name = re.sub(r'[^\w\u4e00-\u9fff\-_]', '_', folder_name)
    safe_name = re.sub(r'_+', '_', safe_name)
    safe_name = safe_name.strip('_')
    return safe_name if safe_name else 'folder'


def _save_uploaded_file(file, file_path: Path) -> None:
    """保存上传文件并确保文件可访问"""
    import os
    import time

    if hasattr(file, 'seek'):
        file.seek(0)
    file.save(str(file_path))

    # Windows 环境下尽量确保文件已刷新到磁盘
    try:
        file.flush()
        if hasattr(file, 'stream') and hasattr(file.stream, 'flush'):
            file.stream.flush()
    except (AttributeError, OSError):
        pass

    retry_count = 3
    for i in range(retry_count):
        if file_path.exists() and file_path.stat().st_size > 0:
            break
        if i < retry_count - 1:
            time.sleep(0.1)


def _process_knowledge_upload(file, description: str, category: str, relative_path: str = ''):
    """处理单个知识库文件上传，返回 (result, status_code)"""
    if not file or file.filename == '':
        raise BadRequest("未选择文件")

    original_filename = file.filename
    if '/' in original_filename or '\\' in original_filename:
        original_filename = original_filename.replace('\\', '/').split('/')[-1]

    if not allowed_file(original_filename):
        raise BadRequest("不支持的文件类型")

    file_ext = ''
    if '.' in original_filename:
        file_ext = '.' + original_filename.rsplit('.', 1)[1].lower()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_id = str(uuid.uuid4())[:8]
    safe_original = _safe_filename(original_filename)
    new_filename = f"{timestamp}_{file_id}_{safe_original}"
    if not new_filename.endswith(file_ext) and file_ext:
        new_filename = new_filename.rsplit('.', 1)[0] + file_ext

    file_hash = knowledge_service.calculate_file_hash(file_stream=file)
    if file_hash:
        existing_record = RagFileRecord.query.filter_by(
            file_hash=file_hash,
            status='active'
        ).first()

        if existing_record:
            doc_ids = []
            if existing_record.ids:
                try:
                    doc_ids = ast.literal_eval(existing_record.ids)
                    if not isinstance(doc_ids, list):
                        doc_ids = []
                except (ValueError, SyntaxError):
                    doc_ids = []

            current_app.logger.info(
                f"检测到重复文件（哈希: {file_hash[:8]}...），跳过上传: {original_filename}"
            )
            return {
                'success': True,
                'message': '文件已存在（相同哈希值），已跳过上传',
                'file_info': {
                    'id': existing_record.id,
                    'filename': existing_record.file_name,
                    'file_size': existing_record.file_size,
                    'file_type': existing_record.file_type,
                    'document_count': len(doc_ids),
                    'created_time': existing_record.created_time.isoformat() if existing_record.created_time else None,
                    'is_duplicate': True
                }
            }, 200

    upload_dir = get_knowledge_uploads_path()
    upload_dir.mkdir(parents=True, exist_ok=True)

    if relative_path:
        safe_path_parts = []
        for part in relative_path.split('/'):
            if part:
                safe_part = _safe_folder_name(part)
                if safe_part:
                    safe_path_parts.append(safe_part)

        sub_dir = upload_dir
        for part in safe_path_parts:
            sub_dir = sub_dir / part
            sub_dir.mkdir(parents=True, exist_ok=True)
        file_path = sub_dir / new_filename
    else:
        file_path = upload_dir / new_filename

    _save_uploaded_file(file, file_path)

    upload_result = knowledge_service.upload_knowledge_file_with_deduplication(
        file_path=str(file_path),
        original_filename=original_filename,
        description=description,
        category=category,
        upload_folder=Path(current_app.config['UPLOAD_FOLDER']),
        vector_db=getattr(current_app, 'vector_db', None)  # type: ignore
    )

    if upload_result['success']:
        return {
            'success': True,
            'message': upload_result['message'],
            'file_info': upload_result['file_info']
        }, 200

    if file_path.exists():
        file_path.unlink()
    return {
        'success': False,
        'message': upload_result.get('message', '知识库文件处理失败'),
        'error': upload_result.get('error')
    }, 500


@knowledge_bp.route('/upload', methods=['POST'])
def upload_knowledge_file():
    """上传知识库文件（支持单文件和多文件）"""
    try:
        upload_files = []
        if 'files' in request.files:
            upload_files = [f for f in request.files.getlist('files') if f and f.filename]
        elif 'file' in request.files:
            single_file = request.files['file']
            upload_files = [single_file] if single_file and single_file.filename else []

        if not upload_files:
            raise BadRequest("没有找到上传文件")

        description = request.form.get('description', '')
        category = request.form.get('category', 'other')
        relative_path = request.form.get('relative_path', '')
        relative_paths = request.form.getlist('relative_paths')

        # 兼容旧行为：单文件时返回与历史一致的响应结构
        if len(upload_files) == 1:
            result, status_code = _process_knowledge_upload(
                upload_files[0], description, category, relative_path
            )
            return jsonify(result), status_code

        results = []
        success_count = 0
        failed_count = 0

        for idx, file in enumerate(upload_files):
            file_relative_path = relative_paths[idx] if idx < len(relative_paths) else relative_path
            try:
                result, status_code = _process_knowledge_upload(
                    file, description, category, file_relative_path
                )
                if status_code == 200 and result.get('success'):
                    success_count += 1
                else:
                    failed_count += 1
                results.append({
                    'filename': file.filename,
                    'status_code': status_code,
                    **result
                })
            except BadRequest as e:
                failed_count += 1
                results.append({
                    'filename': file.filename,
                    'success': False,
                    'status_code': 400,
                    'message': str(e),
                    'error': 'bad_request'
                })
            except (OSError, IOError) as e:
                failed_count += 1
                current_app.logger.error(f"知识库文件上传失败: {e}")
                results.append({
                    'filename': file.filename,
                    'success': False,
                    'status_code': 500,
                    'message': '文件上传失败',
                    'error': 'INTERNAL_SERVER_ERROR',
                    'error_code': 'INTERNAL_SERVER_ERROR',
                    'retryable': False
                })

        return jsonify({
            'success': failed_count == 0,
            'message': f'批量上传完成，成功 {success_count} 个，失败 {failed_count} 个',
            'summary': {
                'total': len(upload_files),
                'success_count': success_count,
                'failed_count': failed_count
            },
            'results': results
        }), 200 if failed_count == 0 else 207

    except BadRequest as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'error': 'bad_request'
        }), 400
    except (OSError, IOError) as e:
        current_app.logger.error(f"知识库文件上传失败: {e}")
        return jsonify({
            'success': False,
            'message': '文件上传失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@knowledge_bp.route('/search', methods=['POST'])
def search_knowledge():
    """搜索知识库"""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("请求数据不能为空")

        query = data.get('query', '').strip()
        if not query:
            raise BadRequest("搜索查询不能为空")

        # 搜索参数（支持 top_k 和 limit 两种参数名）
        top_k = data.get('top_k') or data.get('limit', current_app.config.get('RAG_TOP_K', 5))
        score_threshold = data.get('score_threshold', current_app.config.get('RAG_SCORE_THRESHOLD', 0.7))
        page = data.get('page', 1)
        per_page = data.get('per_page', 10)
        
        # 确保 top_k 是整数
        try:
            top_k = int(top_k)
        except (ValueError, TypeError):
            top_k = current_app.config.get('RAG_TOP_K', 5)

        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1
        if page < 1:
            page = 1

        try:
            per_page = int(per_page)
        except (ValueError, TypeError):
            per_page = 10
        if per_page < 1:
            per_page = 10

        # 分页查询至少需要拿到当前页范围的数据
        required_top_k = page * per_page
        top_k = max(top_k, required_top_k)
        # 防止一次性拉取过多向量结果，避免对服务造成压力
        top_k = min(top_k, 200)
        
        current_app.logger.debug(f"知识库搜索参数: query={query}, top_k={top_k}, score_threshold={score_threshold}")

        # 执行搜索
        result = knowledge_service.search_knowledge(
            query=query,
            vector_db=getattr(current_app, 'vector_db', None),  # type: ignore
            top_k=top_k,
            score_threshold=score_threshold
        )

        if result['success']:
            # 补充文件信息：如果metadata为空，通过内容查找文件
            documents = result['documents']
            enriched_documents = knowledge_service.enrich_search_results_with_file_info(
                documents, current_app
            )
            
            total = len(enriched_documents)
            total_pages = (total + per_page - 1) // per_page if total > 0 else 0
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paged_documents = enriched_documents[start_idx:end_idx]

            # 脱敏处理：搜索结果不返回本地绝对路径
            sanitized_documents = []
            for item in paged_documents:
                if isinstance(item, dict):
                    next_item = dict(item)
                    raw_source = str(next_item.get('source', '') or '')
                    if raw_source:
                        source_name = Path(raw_source.replace('\\', '/')).name
                        next_item['source'] = source_name or raw_source
                        if not next_item.get('file_name'):
                            next_item['file_name'] = source_name or raw_source
                    sanitized_documents.append(next_item)
                else:
                    sanitized_documents.append(item)

            return jsonify({
                'success': True,
                'message': f'找到{total}个相关文档',
                'documents': sanitized_documents,
                'total': total,
                'query': query,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': total_pages,
                    'has_prev': page > 1,
                    'has_next': page < total_pages
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', '知识库搜索失败'),
                'error': result.get('error')
            }), 500

    except BadRequest as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'error': 'bad_request'
        }), 400
    except (ValueError, TypeError) as e:
        current_app.logger.error(f"知识库搜索失败: {e}")
        return jsonify({
            'success': False,
            'message': '搜索失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@knowledge_bp.route('/list', methods=['GET'])
def list_knowledge_files():
    """获取知识库文件列表"""
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        file_type = request.args.get('file_type')
        category = request.args.get('category', '').strip()
        status = request.args.get('status', 'active')
        search = request.args.get('search', '').strip()

        # 构建查询
        query = RagFileRecord.query

        # 添加筛选条件
        if file_type:
            query = query.filter(RagFileRecord.file_type == file_type)
        if category:
            query = query.filter(RagFileRecord.category == category)
        if status:
            query = query.filter(RagFileRecord.status == status)
        if search:
            query = query.filter(
                RagFileRecord.file_name.contains(search) |
                RagFileRecord.description.contains(search)
            )

        # 排序和分页
        query = query.order_by(RagFileRecord.created_time.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # 转换为字典格式
        files = []
        for record in pagination.items:
            file_dict = record.to_dict()
            # 计算文档数量
            if record.ids:
                try:
                    doc_ids = ast.literal_eval(record.ids)
                    file_dict['document_count'] = len(doc_ids) if isinstance(doc_ids, list) else 1
                except (ValueError, SyntaxError):
                    file_dict['document_count'] = 0
            else:
                file_dict['document_count'] = 0
            files.append(file_dict)

        return jsonify({
            'success': True,
            'files': files,
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
        current_app.logger.error(f"获取知识库文件列表失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取文件列表失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@knowledge_bp.route('/<int:file_id>', methods=['GET'])
def get_knowledge_file(file_id):
    """获取知识库文件详情"""
    try:
        record = RagFileRecord.query.get(file_id)
        if not record:
            return jsonify({
                'success': False,
                'message': '文件不存在'
            }), 404

        file_dict = record.to_dict()
        
        # 计算文档块数
        if record.ids:
            try:
                import ast
                # record.ids 是Python列表的字符串表示，使用ast.literal_eval解析
                ids_list = ast.literal_eval(record.ids) if isinstance(record.ids, str) else record.ids
                file_dict['chunk_count'] = len(ids_list) if ids_list else 0
            except Exception as e:
                current_app.logger.warning(f"解析文档块数失败: {e}")
                file_dict['chunk_count'] = 0
        else:
            file_dict['chunk_count'] = 0

        # 获取文档内容预览 - 使用通用预览工具支持多种格式
        try:
            from utils.utils_core.path_helper import get_uploads_path
            from pathlib import Path as FilePath
            from utils.utils_document_processing.file_preview import get_file_preview
            
            # 构建文件完整路径 - record.file_path 已经包含了 knowledge/ 前缀
            # 使用Path对象确保跨平台兼容性和子文件夹支持
            file_path = FilePath(get_uploads_path()) / record.file_path
            
            if file_path.exists():
                # 使用通用预览工具，支持PDF、DOCX、JSON、CSV等多种格式
                preview_result = get_file_preview(str(file_path), max_length=3000)
                file_dict['preview'] = preview_result.get('content', '无法预览')
                file_dict['preview_type'] = preview_result.get('content_type', 'text')  # text, html, json
                file_dict['preview_truncated'] = preview_result.get('is_truncated', False)
            else:
                # 脱敏处理：只显示文件名，不显示完整路径
                file_name = FilePath(record.file_path).name if record.file_path else record.file_name
                file_dict['preview'] = f'文件不存在: {file_name}'
                file_dict['preview_type'] = 'text'
                file_dict['preview_truncated'] = False
                current_app.logger.warning(f"知识库文件不存在: {file_path}")
        except Exception as e:
            current_app.logger.warning(f"获取文件预览失败: {e}", exc_info=True)
            file_dict['preview'] = f'获取预览失败: {str(e)}'
            file_dict['preview_type'] = 'text'
            file_dict['preview_truncated'] = False

        return jsonify({
            'success': True,
            'file_detail': file_dict
        })

    except Exception as e:
        current_app.logger.error(f"获取知识库文件详情失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取文件详情失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@knowledge_bp.route('/<int:file_id>', methods=['DELETE'])
def delete_knowledge_file(file_id):
    """删除知识库文件"""
    try:
        record = RagFileRecord.query.get(file_id)
        if not record:
            return jsonify({
                'success': False,
                'message': '文件不存在'
            }), 404

        # 从向量数据库中删除文档
        if record.ids:
            try:
                doc_ids = ast.literal_eval(record.ids)
                if isinstance(doc_ids, list) and doc_ids:
                    delete_result = knowledge_service.delete_documents(
                        document_ids=doc_ids,
                        vector_db=getattr(current_app, 'vector_db', None)  # type: ignore
                    )
                    if not delete_result['success']:
                        current_app.logger.warning(f"向量数据库删除失败: {delete_result.get('message')}")
            except (ValueError, SyntaxError) as e:
                current_app.logger.error(f"删除向量数据库文档失败: {e}")

        # 删除物理文件（仅限知识库目录）
        if record.file_path:
            try:
                from pathlib import Path
                file_path = Path(current_app.config['UPLOAD_FOLDER']) / record.file_path
                knowledge_dir = get_knowledge_uploads_path()
                
                # 安全检查：确保文件在知识库目录内
                if file_path.exists() and str(knowledge_dir) in str(file_path.resolve()):
                    file_path.unlink()
                elif file_path.exists():
                    current_app.logger.warning(f"拒绝删除非知识库目录文件: {file_path}")
            except (OSError, IOError) as e:
                current_app.logger.warning(f"删除物理文件失败: {e}")

        # 从数据库删除记录
        db.session.delete(record)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '知识库文件删除成功'
        })

    except Exception as e:
        current_app.logger.error(f"删除知识库文件失败: {e}")
        return jsonify({
            'success': False,
            'message': '删除文件失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@knowledge_bp.route('/<int:file_id>', methods=['PUT'])
def update_knowledge_file(file_id):
    """更新知识库文件元信息"""
    try:
        record = RagFileRecord.query.get(file_id)
        if not record:
            return jsonify({
                'success': False,
                'message': '文件不存在'
            }), 404

        # 获取更新数据
        data = request.get_json()
        if not data:
            raise BadRequest("缺少更新数据")

        # 可更新的字段
        updatable_fields = ['description', 'category']
        updated = False

        for field in updatable_fields:
            if field in data:
                # 验证category值
                if field == 'category':
                    valid_categories = ['requirements', 'test_cases', 'business_rules', 
                                       'best_practices', 'templates', 'other']
                    if data[field] not in valid_categories:
                        return jsonify({
                            'success': False,
                            'message': f'无效的分类: {data[field]}'
                        }), 400
                
                setattr(record, field, data[field])
                updated = True

        if not updated:
            return jsonify({
                'success': False,
                'message': '没有可更新的字段'
            }), 400

        # 更新修改时间
        record.updated_at = datetime.now()
        
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '文件信息更新成功',
            'data': {
                'id': record.id,
                'description': record.description,
                'category': record.category,
                'updated_at': record.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })

    except BadRequest as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"更新知识库文件失败: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '更新文件信息失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@knowledge_bp.route('/config', methods=['GET'])
def get_knowledge_config():
    """获取知识库上传配置（文件大小限制、允许的文件类型等）"""
    try:
        max_content_length = current_app.config.get('MAX_CONTENT_LENGTH', 3072 * 1024 * 1024)
        allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'txt', 'csv', 'docx', 'pdf', 'json', 'md'})
        
        # 单个文件限制建议为总限制的1/6，但最小500MB，最大500MB（当前后端没有单独限制）
        max_file_size = min(500 * 1024 * 1024, max_content_length // 6)
        
        return jsonify({
            'success': True,
            'config': {
                'max_file_size': max_file_size,  # 单个文件最大大小（字节）
                'max_total_size': max_content_length,  # 批量上传总大小限制（字节）
                'allowed_extensions': list(allowed_extensions)  # 允许的文件类型
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取知识库配置失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取配置失败: {str(e)}',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@knowledge_bp.route('/stats', methods=['GET'])
def get_knowledge_stats():
    """获取知识库统计信息"""
    try:
        # 文件总数
        total_files = RagFileRecord.query.filter(RagFileRecord.status == 'active').count()

        # 按分类统计
        category_stats = db.session.query(
            RagFileRecord.category,
            db.func.count(RagFileRecord.id)
        ).filter(RagFileRecord.status == 'active').group_by(RagFileRecord.category).all()

        # 计算总文档数量和总文件大小
        active_records = RagFileRecord.query.filter(RagFileRecord.status == 'active').all()
        total_chunks = 0
        storage_size = 0
        last_update = None

        for record in active_records:
            if record.file_size:
                storage_size += record.file_size
            if record.ids:
                try:
                    doc_ids = ast.literal_eval(record.ids)
                    if isinstance(doc_ids, list):
                        total_chunks += len(doc_ids)
                    else:
                        total_chunks += 1
                except (ValueError, SyntaxError):
                    pass
            # 获取最后更新时间
            if record.created_time and (last_update is None or record.created_time > last_update):
                last_update = record.created_time

        # 按日期统计上传趋势（最近7天）
        from datetime import datetime, timedelta
        upload_trend = []
        today = datetime.now().date()
        for i in range(6, -1, -1):
            target_date = today - timedelta(days=i)
            count = RagFileRecord.query.filter(
                RagFileRecord.status == 'active',
                db.func.date(RagFileRecord.created_time) == target_date
            ).count()
            upload_trend.append({
                'date': target_date.isoformat(),
                'count': count
            })

        return jsonify({
            'success': True,
            'stats': {
                'total_files': total_files,
                'total_chunks': total_chunks,
                'storage_size': storage_size,
                'last_update': last_update.isoformat() if last_update else None,
                'category_distribution': dict(category_stats),
                'upload_trend': upload_trend
            }
        })

    except Exception as e:
        current_app.logger.error(f"获取知识库统计失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取统计信息失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@knowledge_bp.route('/batch-delete', methods=['POST'])
def batch_delete_knowledge_files():
    """批量删除知识库文件"""
    try:
        data = request.get_json()
        if not data or 'file_ids' not in data:
            raise BadRequest("请提供要删除的文件ID列表")

        file_ids = data.get('file_ids', [])
        if not isinstance(file_ids, list) or len(file_ids) == 0:
            raise BadRequest("文件ID列表不能为空")

        deleted_count = 0
        failed_count = 0

        for file_id in file_ids:
            try:
                record = RagFileRecord.query.get(file_id)
                if not record:
                    failed_count += 1
                    continue

                # 从向量数据库中删除文档
                if record.ids:
                    try:
                        doc_ids = ast.literal_eval(record.ids)
                        if isinstance(doc_ids, list) and doc_ids:
                            delete_result = knowledge_service.delete_documents(
                                document_ids=doc_ids,
                                vector_db=getattr(current_app, 'vector_db', None)  # type: ignore
                            )
                            if not delete_result['success']:
                                current_app.logger.warning(f"向量数据库删除失败: {delete_result.get('message')}")
                    except (ValueError, SyntaxError) as e:
                        current_app.logger.error(f"删除向量数据库文档失败: {e}")

                # 删除物理文件（仅限知识库目录）
                if record.file_path:
                    try:
                        from pathlib import Path
                        file_path = Path(current_app.config['UPLOAD_FOLDER']) / record.file_path
                        knowledge_dir = get_knowledge_uploads_path()
                        
                        # 安全检查：确保文件在知识库目录内
                        if file_path.exists() and str(knowledge_dir) in str(file_path.resolve()):
                            file_path.unlink()
                        elif file_path.exists():
                            current_app.logger.warning(f"拒绝删除非知识库目录文件: {file_path}")
                    except (OSError, IOError) as e:
                        current_app.logger.warning(f"删除物理文件失败: {e}")

                # 从数据库删除记录
                db.session.delete(record)
                deleted_count += 1

            except Exception as e:
                current_app.logger.error(f"删除文件{file_id}失败: {e}")
                failed_count += 1

        # 提交所有删除操作
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'成功删除{deleted_count}个文件' + (f'，{failed_count}个失败' if failed_count > 0 else ''),
            'deleted_count': deleted_count,
            'failed_count': failed_count
        })

    except BadRequest as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'error': 'bad_request'
        }), 400
    except Exception as e:
        current_app.logger.error(f"批量删除知识库文件失败: {e}")
        return jsonify({
            'success': False,
            'message': '批量删除文件失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@knowledge_bp.route('/rebuild', methods=['POST'])
def rebuild_knowledge_base():
    """重建知识库"""
    try:
        data = request.get_json() or {}
        force_rebuild = data.get('force', False)
        clear_all = data.get('clear_all', False)  # 是否完全清空向量数据库

        # 执行重建
        result = knowledge_service.rebuild_knowledge_base(
            vector_db=getattr(current_app, 'vector_db', None),  # type: ignore
            force=force_rebuild,
            clear_all=clear_all
        )

        if result['success']:
            return jsonify({
                'success': True,
                'message': '知识库重建成功',
                'rebuild_info': result.get('info', {})
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', '知识库重建失败'),
                'error': result.get('error')
            }), 500

    except Exception as e:
        current_app.logger.error(f"知识库重建失败: {e}")
        return jsonify({
            'success': False,
            'message': '重建知识库失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500