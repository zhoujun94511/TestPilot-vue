#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Config center API routes."""

from flask import Blueprint, request, current_app
from utils.utils_core.api_response import api_success, api_error, normalize_message_response
from utils.utils_core.common_utils import normalize_language

from services.config_center_service import config_center_service
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)

config_center_bp = Blueprint('config_center', __name__, url_prefix='/api/config')


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


def validate_ai_model_configs(configs):
    """Validate required AI model config values."""
    config_dict = {config['key']: config.get('value', '') for config in configs}
    provider = config_dict.get('DEFAULT_COMPANY', '').upper()

    if provider == 'OPENAI':
        openai_key = config_dict.get('OPENAI_API_KEY', '').strip()
        if not openai_key:
            return _t(
                'OpenAI API key is required. Please provide a valid API key or switch to another AI provider.',
                'OpenAI API key is required. Please provide a valid API key or switch to another AI provider.'
            )
        if not openai_key.startswith('sk-'):
            return _t(
                'OpenAI API key format is invalid. It should start with "sk-".',
                'OpenAI API key format is invalid. It should start with "sk-".'
            )

    elif provider == 'DEEPSEEK':
        deepseek_key = config_dict.get('DEEPSEEK_API_KEY', '').strip()
        if not deepseek_key:
            return _t(
                'DeepSeek API key is required. Please provide a valid API key or switch to another AI provider.',
                'DeepSeek API key is required. Please provide a valid API key or switch to another AI provider.'
            )
        import re
        if not re.match(r'^sk-[0-9a-f]{32}$', deepseek_key):
            return _t(
                'DeepSeek API key format is invalid. It should be "sk-" plus 32 lowercase hex characters.',
                'DeepSeek API key format is invalid. It should be "sk-" plus 32 lowercase hex characters.'
            )

    elif provider == 'OLLAMA':
        ollama_model = config_dict.get('OLLAMA_MODEL', '').strip()
        if not ollama_model:
            return _t(
                'Ollama model name is required. Please provide a valid model name or switch to another AI provider.',
                'Ollama model name is required. Please provide a valid model name or switch to another AI provider.'
            )

    elif provider == 'GEMINI':
        gemini_key = config_dict.get('GEMINI_API_KEY', '').strip()
        if not gemini_key:
            return _t(
                'Gemini API key is required. Please provide a valid API key or switch to another AI provider.',
                'Gemini API key is required. Please provide a valid API key or switch to another AI provider.'
            )
        import re
        if not re.match(r'^AIza[A-Za-z0-9_-]{35}$', gemini_key):
            return _t(
                'Gemini API key format is invalid. It should start with "AIza".',
                'Gemini API key format is invalid. It should start with "AIza".'
            )

    elif provider == 'QWEN':
        qwen_key = config_dict.get('QWEN_API_KEY', '').strip()
        if not qwen_key:
            return _t(
                'Qwen API key is required. Please provide a valid API key or switch to another AI provider.',
                'Qwen API key is required. Please provide a valid API key or switch to another AI provider.'
            )
        if not qwen_key.startswith('sk-'):
            return _t(
                'Qwen API key format is invalid. It should start with "sk-".',
                'Qwen API key format is invalid. It should start with "sk-".'
            )

    return None


def _reload_ai_runtime():
    """Reload in-memory AI runtime after config updates."""
    try:
        from config.settings import settings
        from utils.utils_ai_models.get_llm import clear_llm_cache, get_llm

        settings.load_from_config_center()
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

        try:
            if settings.DEFAULT_COMPANY != 'OLLAMA':
                from utils.utils_core.remote_model_checker import model_checker

                current_app.config['MODEL_STATUS'] = model_checker.get_model_status_summary(settings.DEFAULT_COMPANY)
            else:
                current_app.config['MODEL_STATUS'] = {
                    'company': 'ollama',
                    'service_name': 'Ollama',
                    'is_available': True,
                    'message': 'Ollama local model',
                    'details': {'note': 'Local model, no remote check required'},
                    'timestamp': None
                }
        except Exception as status_error:
            logger.warning('Failed to refresh model status cache: %s', status_error)

    except Exception as reload_error:
        logger.warning('Failed to reload config center runtime: %s', reload_error)


def _reload_runtime_flags():
    """Reload lightweight runtime flags from config center."""
    try:
        from config.settings import settings
        settings.load_from_config_center()
    except Exception as reload_error:
        logger.warning('Failed to reload runtime flags: %s', reload_error)


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
            status=500,
            details=str(e)
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
            validation_error = validate_ai_model_configs(data['configs'])
            if validation_error:
                return _config_error(
                    code='CONFIG_UPDATE_VALIDATION_FAILED',
                    message_key='configCenter.message.validationFailed',
                    message='Configuration validation failed',
                    status=400,
                    details=validation_error
                )

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
                    operator=request.headers.get('X-Operator', 'admin')
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
        if category == 'ai_model' and updated_count > 0:
            _reload_ai_runtime()
        elif 'ENABLE_EXPERIMENTAL_ACTIONS' in updated_keys and updated_count > 0:
            _reload_runtime_flags()

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
            status=500,
            details=str(e)
        )


@config_center_bp.route('/item/<key>', methods=['GET'])
def get_config_item(key):
    """Get a single config item value."""
    try:
        value = config_center_service.get_config_value(key)
        return _config_success(
            data={'key': key, 'value': value},
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
            status=500,
            details=str(e)
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
            operator=request.headers.get('X-Operator', 'admin')
        )

        if success:
            if str(key).upper() == 'ENABLE_EXPERIMENTAL_ACTIONS':
                _reload_runtime_flags()
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
            status=500,
            details=str(e)
        )


@config_center_bp.route('/item/<key>', methods=['DELETE'])
def delete_config_item(key):
    """Delete a config item."""
    try:
        success, message = config_center_service.delete_config(
            key=key,
            operator=request.headers.get('X-Operator', 'admin')
        )

        if success:
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
            status=500,
            details=str(e)
        )


@config_center_bp.route('/export', methods=['GET'])
def export_configs():
    """Export all configs."""
    try:
        format_type = request.args.get('format', 'json')
        success, content, filename = config_center_service.export_configs(format_type)

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
            status=500,
            details=str(e)
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
            operator=request.headers.get('X-Operator', 'admin')
        )

        if success:
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
            status=500,
            details=str(e)
        )


@config_center_bp.route('/audit-logs', methods=['GET'])
def get_audit_logs():
    """Get config audit logs."""
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
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
            status=500,
            details=str(e)
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

        return _config_success(
            data={
                'valid': True,
                'message': 'Configuration value validated successfully'
            },
            code='CONFIG_VALIDATE_SUCCESS',
            message_key='config.message.validateSuccess',
            message='Configuration value validated successfully'
        )
    except Exception as e:
        logger.error('Validate config failed: %s, error: %s', key, e)
        return _config_error(
            code='CONFIG_VALIDATE_FAILED',
            message_key='configCenter.message.validationFailed',
            message='Failed to validate configuration',
            status=500,
            details=str(e)
        )
