#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Config center API routes."""

from flask import Blueprint, request, current_app
from utils.utils_core.api_response import api_success, api_error, normalize_message_response
from utils.utils_core.common_utils import normalize_language

from services.config_center_service import (
    SENSITIVE_VALUE_MASK,
    config_center_service,
)
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)

config_center_bp = Blueprint('config_center', __name__, url_prefix='/api/config')


@config_center_bp.before_request
def _config_center_auth():
    from services.auth_service import auth_required, current_user

    if not auth_required():
        return None
    user = current_user()
    if user is None:
        return api_error(
            'UNAUTHORIZED',
            message_key='common.errors.http401',
            message='未登录或会话已过期',
            status=401,
        )
    if user.get('role') != 'super_admin':
        return api_error(
            'FORBIDDEN',
            message_key='common.errors.http403',
            message='仅超级管理员可访问配置中心',
            status=403,
        )
    return None


def _operator() -> str:
    """审计里的操作人取登录用户；只有关闭认证时才接受 X-Operator 请求头。"""
    from services.auth_service import auth_required, current_user

    if auth_required():
        user = current_user() or {}
        return str(user.get('username') or user.get('id') or 'unknown')
    return (request.headers.get('X-Operator') or 'admin').strip()[:64] or 'admin'


def _is_english_locale() -> bool:
    return normalize_language(request.headers.get('Accept-Language', 'zh-CN')) == 'en'


def _t(zh: str, en: str) -> str:
    return en if _is_english_locale() else zh


def _translate_service_message(message: str) -> str:
    if not _is_english_locale() or not message:
        return message

    exact_map = {
        '配置更新成功': 'Configuration updated successfully',
        '配置删除成功': 'Configuration deleted successfully',
        '配置值验证通过': 'Configuration value validated successfully',
        '没有上传文件': 'No file was uploaded',
        '没有选择文件': 'No file was selected',
        '请求数据格式错误': 'Invalid request payload',
        '不支持的文件格式，请上传 JSON 或 YAML 文件': 'Unsupported file format. Please upload a JSON or YAML file',
    }
    if message in exact_map:
        return exact_map[message]

    prefix_map = {
        '设置配置值失败: ': 'Failed to save configuration: ',
        '导出配置失败: ': 'Failed to export configuration: ',
        '导入配置失败: ': 'Failed to import configuration: ',
        '获取分类配置失败: ': 'Failed to load category configuration: ',
        '获取配置项失败: ': 'Failed to load configuration item: ',
        '更新配置失败: ': 'Failed to update configuration: ',
        '删除配置失败: ': 'Failed to delete configuration: ',
        '获取审计日志失败: ': 'Failed to load audit logs: ',
        '验证配置失败: ': 'Failed to validate configuration: ',
    }
    for zh_prefix, en_prefix in prefix_map.items():
        if message.startswith(zh_prefix):
            return en_prefix + message[len(zh_prefix):]

    return message


def _config_success(data=None, code='CONFIG_SUCCESS', message_key='config.message.success', message='Configuration completed successfully', **extra):
    return api_success(data=data, code=code, message_key=message_key, message=message, **extra)


def _config_error(code, message_key, message, status=400, message_params=None, details=None, **extra):
    return api_error(
        code=code,
        message_key=message_key,
        message=message,
        status=status,
        message_params=message_params,
        details=details,
        **extra
    )


_PROVIDER_ENABLE_KEYS = {
    'OPENAI': 'ENABLE_OPENAI',
    'DEEPSEEK': 'ENABLE_DEEPSEEK',
    'OLLAMA': 'ENABLE_OLLAMA',
    'GEMINI': 'ENABLE_GEMINI',
    'QWEN': 'ENABLE_QWEN',
    'ANTHROPIC': 'ENABLE_ANTHROPIC',
}


def _bool_text(enabled: bool) -> str:
    return 'true' if enabled else 'false'


def enforce_single_active_provider(configs):
    """保存时只打开默认提供商的开关，其余关掉。密钥项保持原样。"""
    present = {}
    for config in configs:
        if isinstance(config, dict) and config.get('key'):
            present[str(config['key'])] = config
    if 'DEFAULT_COMPANY' in present:
        company = str(present['DEFAULT_COMPANY'].get('value') or '').strip().upper()
    else:
        company = str(config_center_service.get_config_value('DEFAULT_COMPANY') or '').strip().upper()
    if company not in _PROVIDER_ENABLE_KEYS:
        return
    for provider_name, enable_key in _PROVIDER_ENABLE_KEYS.items():
        enabled = provider_name == company
        if enable_key in present:
            present[enable_key]['value'] = _bool_text(enabled)
            present[enable_key]['value_type'] = 'bool'
            continue
        stored = config_center_service.get_config_value(enable_key)
        stored_enabled = str(stored).strip().lower() in ('true', '1', 'yes', 'on')
        if stored is not None and stored_enabled == enabled:
            continue
        configs.append({
            'key': enable_key,
            'value': _bool_text(enabled),
            'value_type': 'bool',
            'category': 'ai_model',
            'is_sensitive': False,
        })


def validate_ai_model_configs(configs) -> None:
    """空密钥和占位符可以保存。多家开关同时打开时，收成默认提供商这一家。"""
    from utils.utils_core.api_error_handler import is_placeholder_secret

    for config in configs:
        key = str(config.get('key') or '')
        if not key.endswith('_API_KEY'):
            continue
        raw = config.get('value')
        if raw == SENSITIVE_VALUE_MASK:
            continue
        if is_placeholder_secret(raw):
            config['value'] = ''
    enforce_single_active_provider(configs)


def _reload_ai_runtime():
    """Reload in-memory AI runtime after config updates."""
    try:
        from config.settings import settings
        from utils.utils_ai_models.get_llm import clear_llm_cache, get_llm

        from utils.utils_performance_monitoring.token_monitor import refresh_token_monitor_session_limits

        settings.load_from_config_center()
        refresh_token_monitor_session_limits()
        logger.info('Config center updated, reloading AI runtime with provider %s', settings.DEFAULT_COMPANY)

        clear_llm_cache()
        logger.info('LLM cache cleared')

        try:
            current_app.llm = get_llm(settings.DEFAULT_COMPANY, use_case='chat')
            current_app.llm_case_generation = get_llm(settings.DEFAULT_COMPANY, use_case='case_generation')
            current_app.llm_requirement_analysis = get_llm(settings.DEFAULT_COMPANY, use_case='requirement_analysis')
            logger.info('Flask LLM instances refreshed: %s', settings.DEFAULT_COMPANY)
        except Exception as llm_error:
            logger.error('Failed to refresh LLM instances: %s', llm_error)

        # 远程探测可能阻塞十秒，保存时只作废缓存，由 /api/model-status 下次请求时重新检查
        current_app.config.pop('MODEL_STATUS', None)

    except Exception as reload_error:
        logger.warning('Failed to reload config center runtime: %s', reload_error)


def _reload_runtime_flags():
    """Reload lightweight runtime flags from config center."""
    try:
        from config.settings import settings
        from utils.utils_performance_monitoring.token_monitor import refresh_token_monitor_session_limits

        settings.load_from_config_center()
        refresh_token_monitor_session_limits()
        _sync_vector_store_runtime(settings)
    except Exception as reload_error:
        logger.warning('Failed to reload runtime flags: %s', reload_error)


def _sync_vector_store_runtime(settings):
    """ENABLE_VECTOR_STORE 在运行中打开时补建向量库，否则要重启才生效。"""
    if not getattr(settings, 'ENABLE_VECTOR_STORE', True):
        return
    if getattr(current_app, 'vector_db', None) is not None:
        return
    from utils.utils_ai_models.embeddings import create_vector_db

    try:
        current_app.vector_db = create_vector_db()
        logger.info('ENABLE_VECTOR_STORE turned on, vector store created')
    except Exception as exc:
        logger.error('Failed to create vector store after enabling: %s', exc)


_AI_RUNTIME_KEYS = {
    'OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_MODEL', 'TR_OPENAI_MAX_TOKENS',
    'DEEPSEEK_API_KEY', 'DEEPSEEK_BASE_URL', 'DEEPSEEK_MODEL', 'TR_DEEPSEEK_MAX_TOKENS',
    'OLLAMA_BASE_URL', 'OLLAMA_MODEL',
    'GEMINI_API_KEY', 'GEMINI_BASE_URL', 'GEMINI_MODEL', 'TR_GEMINI_MAX_TOKENS',
    'QWEN_API_KEY', 'QWEN_BASE_URL', 'QWEN_MODEL', 'QWEN_TEMPERATURE', 'TR_QWEN_MAX_TOKENS', 'QWEN_TIMEOUT',
    'ANTHROPIC_API_KEY', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_MODEL', 'TR_ANTHROPIC_MAX_TOKENS',
    'MAX_TOKENS', 'TR_MAX_TOKENS', 'TOKEN_MAX_PER_SESSION', 'TOKEN_MAX_CALLS_PER_SESSION',
    'DEFAULT_COMPANY', 'GPT5_VERBOSITY', 'GPT5_REASONING_EFFORT',
    'ENABLE_OPENAI', 'ENABLE_DEEPSEEK', 'ENABLE_OLLAMA', 'ENABLE_GEMINI', 'ENABLE_QWEN', 'ENABLE_ANTHROPIC',
}


def _reload_after_config_change(keys, category=None):
    """AI 相关键重载模型，其余已映射键只刷新 settings。"""
    normalized = {str(key).upper() for key in keys if key}
    if category == 'ai_model' or normalized & _AI_RUNTIME_KEYS:
        _reload_ai_runtime()
    else:
        _reload_runtime_flags()


@config_center_bp.route('/categories', methods=['GET'])
def get_config_categories():
    """Return all config categories."""
    categories = [
        {
            'id': 'ai_model',
            'name_key': 'configCenter.category.ai_model',
            'description_key': 'configCenter.categoryDescription.ai_model',
            'name': 'AI Model Settings',
            'description': 'Manage AI model related settings',
            'priority': 1
        },
        {
            'id': 'case_generation',
            'name_key': 'configCenter.category.case_generation',
            'description_key': 'configCenter.categoryDescription.case_generation',
            'name': 'Test Case Generation Settings',
            'description': 'Manage test-case generation settings',
            'priority': 2
        },
        {
            'id': 'performance',
            'name_key': 'configCenter.category.performance',
            'description_key': 'configCenter.categoryDescription.performance',
            'name': 'Performance Settings',
            'description': 'Manage runtime and performance settings',
            'priority': 3
        },
        {
            'id': 'knowledge',
            'name_key': 'configCenter.category.knowledge',
            'description_key': 'configCenter.categoryDescription.knowledge',
            'name': 'Knowledge Base Retrieval Settings',
            'description': 'Manage knowledge base retrieval settings',
            'priority': 4
        },
        {
            'id': 'file_processing',
            'name_key': 'configCenter.category.file_processing',
            'description_key': 'configCenter.categoryDescription.file_processing',
            'name': 'File Processing Settings',
            'description': 'Manage file processing settings',
            'priority': 5
        }
    ]
    return _config_success(
        data=categories,
        code='CONFIG_CATEGORY_LIST_SUCCESS',
        message_key='configCenter.message.categoryListLoaded',
        message='Configuration categories loaded successfully'
    )


@config_center_bp.route('/<category>', methods=['GET'])
def get_configs_by_category(category):
    """Get configs for a single category."""
    try:
        configs = config_center_service.get_configs_by_category(category)
        return _config_success(
            data=configs,
            code='CONFIG_CATEGORY_LIST_SUCCESS',
            message_key='configCenter.message.categoryListLoaded',
            message='Configuration items loaded successfully'
        )
    except Exception as e:
        logger.error('Failed to load category configs: %s, error: %s', category, e)
        return _config_error(
            code='CONFIG_CATEGORY_FETCH_FAILED',
            message_key='configCenter.message.categoryFetchFailed',
            message='Failed to load configuration items',
            status=500
        )


@config_center_bp.route('/<category>', methods=['POST'])
def update_configs_by_category(category):
    """Batch update category configs."""
    try:
        data = request.get_json()
        if not data or 'configs' not in data:
            return _config_error(
                code='CONFIG_UPDATE_INVALID_PAYLOAD',
                message_key='configCenter.message.invalidPayload',
                message='Invalid request payload',
                status=400
            )

        if category == 'ai_model':
            validate_ai_model_configs(data['configs'])

        updated_count = 0
        failed_configs = []

        for config_data in data['configs']:
            try:
                success, message = config_center_service.set_config_value(
                    key=config_data['key'],
                    value=config_data['value'],
                    value_type=config_data.get('value_type', 'string'),
                    category=category,
                    description=config_data.get('description'),
                    is_sensitive=config_data.get('is_sensitive', False),
                    operator=_operator()
                )

                if success:
                    updated_count += 1
                else:
                    failed_configs.append({'key': config_data['key'], 'error': message})
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning('Skip invalid config payload item: %s, error: %s', config_data, exc)
                failed_configs.append({
                    'key': config_data.get('key', 'unknown'),
                    'error': 'INTERNAL_SERVER_ERROR',
                    'error_code': 'INTERNAL_SERVER_ERROR'
                })

        updated_keys = {str(item.get('key', '')) for item in data['configs'] if isinstance(item, dict)}
        if updated_count > 0:
            _reload_after_config_change(updated_keys, category)

        return _config_success(
            data={
                'updated_count': updated_count,
                'failed_configs': failed_configs
            },
            code='CONFIG_BATCH_UPDATE_SUCCESS',
            message_key='configCenter.message.batchUpdateSuccess',
            message='Configuration items updated successfully',
            message_params={'updated_count': updated_count}
        )
    except Exception as e:
        logger.error('Batch update config failed: %s, error: %s', category, e)
        return _config_error(
            code='CONFIG_BATCH_UPDATE_FAILED',
            message_key='configCenter.message.batchUpdateFailed',
            message='Failed to update configuration items',
            status=500
        )


@config_center_bp.route('/item/<key>', methods=['GET'])
def get_config_item(key):
    """Get a single config item value."""
    try:
        item = config_center_service.get_public_config_item(key)
        return _config_success(
            data=item,
            code='CONFIG_ITEM_FETCH_SUCCESS',
            message_key='configCenter.message.itemLoaded',
            message='Configuration item loaded successfully'
        )
    except Exception as e:
        logger.error('Failed to load config item: %s, error: %s', key, e)
        return _config_error(
            code='CONFIG_ITEM_FETCH_FAILED',
            message_key='configCenter.message.itemFetchFailed',
            message='Failed to load configuration item',
            status=500
        )


@config_center_bp.route('/item/<key>', methods=['PUT'])
def update_config_item(key):
    """Update a single config item."""
    try:
        data = request.get_json()
        if not data or 'value' not in data:
            return _config_error(
                code='CONFIG_ITEM_UPDATE_INVALID_PAYLOAD',
                message_key='configCenter.message.invalidPayload',
                message='Invalid request payload',
                status=400
            )

        success, message = config_center_service.set_config_value(
            key=key,
            value=data['value'],
            value_type=data.get('value_type', 'string'),
            category=data.get('category', 'general'),
            description=data.get('description'),
            is_sensitive=data.get('is_sensitive', False),
            operator=_operator()
        )

        if success:
            stored = config_center_service.get_public_config_item(key)
            _reload_after_config_change([key], stored.get('category'))
            return _config_success(
                code='CONFIG_ITEM_UPDATE_SUCCESS',
                message_key='configCenter.message.itemUpdateSuccess',
                message='Configuration item updated successfully',
                message_params={'key': key}
            )
        return _config_error(
            code='CONFIG_ITEM_UPDATE_FAILED',
            message_key='configCenter.message.itemUpdateFailed',
            message='Failed to update configuration item',
            status=400,
            details=normalize_message_response(message, default_code='CONFIG_ITEM_UPDATE_FAILED', default_message_key='configCenter.message.itemUpdateFailed', default_message='Failed to update configuration item')
        )
    except Exception as e:
        logger.error('Update config item failed: %s, error: %s', key, e)
        return _config_error(
            code='CONFIG_ITEM_UPDATE_FAILED',
            message_key='configCenter.message.itemUpdateFailed',
            message='Failed to update configuration item',
            status=500
        )


@config_center_bp.route('/item/<key>', methods=['DELETE'])
def delete_config_item(key):
    """Delete a config item."""
    try:
        success, message = config_center_service.delete_config(
            key=key,
            operator=_operator()
        )

        if success:
            _reload_after_config_change([key])
            return _config_success(
                code='CONFIG_ITEM_DELETE_SUCCESS',
                message_key='configCenter.message.itemDeleteSuccess',
                message='Configuration item deleted successfully',
                message_params={'key': key}
            )
        return _config_error(
            code='CONFIG_ITEM_DELETE_FAILED',
            message_key='configCenter.message.itemDeleteFailed',
            message='Failed to delete configuration item',
            status=400,
            details=normalize_message_response(message, default_code='CONFIG_ITEM_DELETE_FAILED', default_message_key='configCenter.message.itemDeleteFailed', default_message='Failed to delete configuration item')
        )
    except Exception as e:
        logger.error('Delete config item failed: %s, error: %s', key, e)
        return _config_error(
            code='CONFIG_ITEM_DELETE_FAILED',
            message_key='configCenter.message.itemDeleteFailed',
            message='Failed to delete configuration item',
            status=500
        )


@config_center_bp.route('/export', methods=['GET'])
def export_configs():
    """Export all configs."""
    try:
        format_type = request.args.get('format', 'json')
        success, content, filename = config_center_service.export_configs(format_type, operator=_operator())

        if success:
            return _config_success(
                data={
                    'content': content,
                    'filename': filename,
                    'format': format_type
                },
                code='CONFIG_EXPORT_SUCCESS',
                message_key='config.message.exportSuccess',
                message='Configuration exported successfully'
            )
        return _config_error(
            code='CONFIG_EXPORT_FAILED',
            message_key='config.message.exportFailed',
            message='Failed to export configuration',
            status=500,
            details=_translate_service_message(content)
        )
    except Exception as e:
        logger.error('Export configs failed: %s', e)
        return _config_error(
            code='CONFIG_EXPORT_FAILED',
            message_key='config.message.exportFailed',
            message='Failed to export configuration',
            status=500
        )


@config_center_bp.route('/import', methods=['POST'])
def import_configs():
    """Import configs from uploaded file."""
    try:
        if 'file' not in request.files:
            return _config_error(
                code='CONFIG_IMPORT_NO_FILE',
                message_key='config.message.noFileUploaded',
                message='No file was uploaded',
                status=400
            )

        file = request.files['file']
        if file.filename == '':
            return _config_error(
                code='CONFIG_IMPORT_NO_FILE_SELECTED',
                message_key='config.message.noFileSelected',
                message='No file was selected',
                status=400
            )

        filename = file.filename.lower()
        if filename.endswith('.json'):
            format_type = 'json'
        elif filename.endswith('.yaml') or filename.endswith('.yml'):
            format_type = 'yaml'
        else:
            return _config_error(
                code='CONFIG_IMPORT_UNSUPPORTED_FORMAT',
                message_key='config.message.unsupportedFileFormat',
                message='Unsupported file format. Please upload a JSON or YAML file',
                status=400
            )

        content = file.read().decode('utf-8')
        success, message, imported_count = config_center_service.import_configs(
            content=content,
            format_type=format_type,
            operator=_operator()
        )

        if success:
            _reload_ai_runtime()
            return _config_success(
                data={'imported_count': imported_count},
                code='CONFIG_IMPORT_SUCCESS',
                message_key='config.message.importSuccess',
                message='Configuration imported successfully',
                message_params={'imported_count': imported_count}
            )
        return _config_error(
            code='CONFIG_IMPORT_FAILED',
            message_key='config.message.importFailed',
            message='Failed to import configuration',
            status=400,
            details=normalize_message_response(message, default_code='CONFIG_IMPORT_FAILED', default_message_key='config.message.importFailed', default_message='Failed to import configuration')
        )
    except Exception as e:
        logger.error('Import configs failed: %s', e)
        return _config_error(
            code='CONFIG_IMPORT_FAILED',
            message_key='config.message.importFailed',
            message='Failed to import configuration',
            status=500
        )


@config_center_bp.route('/audit-logs', methods=['GET'])
def get_audit_logs():
    """Get config audit logs."""
    try:
        limit = min(max(1, request.args.get('limit', 100, type=int) or 100), 500)
        offset = max(0, request.args.get('offset', 0, type=int) or 0)
        logs = config_center_service.get_audit_logs(limit=limit, offset=offset)
        return _config_success(
            data=logs,
            code='CONFIG_AUDIT_LOGS_SUCCESS',
            message_key='configCenter.message.auditLogsLoaded',
            message='Audit logs loaded successfully'
        )
    except Exception as e:
        logger.error('Get audit logs failed: %s', e)
        return _config_error(
            code='CONFIG_AUDIT_LOGS_FAILED',
            message_key='configCenter.message.auditLogsFailed',
            message='Failed to load audit logs',
            status=500
        )


@config_center_bp.route('/validate/<key>', methods=['POST'])
def validate_config(key):
    """Validate a config item value."""
    try:
        data = request.get_json()
        if not data or 'value' not in data:
            return _config_error(
                code='CONFIG_VALIDATE_INVALID_PAYLOAD',
                message_key='configCenter.message.invalidPayload',
                message='Invalid request payload',
                status=400
            )

        valid, message = config_center_service.validate_config_value(key, data.get('value'))
        return _config_success(
            data={
                'valid': bool(valid),
                'message': message
            },
            code='CONFIG_VALIDATE_SUCCESS' if valid else 'CONFIG_VALIDATE_FAILED',
            message_key='config.message.validateSuccess' if valid else 'configCenter.message.validationFailed',
            message=message or ('Configuration value validated successfully' if valid else 'Configuration value is invalid')
        )
    except Exception as e:
        logger.error('Validate config failed: %s, error: %s', key, e)
        return _config_error(
            code='CONFIG_VALIDATE_FAILED',
            message_key='configCenter.message.validationFailed',
            message='Failed to validate configuration',
            status=500
        )
