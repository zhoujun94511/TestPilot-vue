"""
基础工具包 (utils_core)
提供通用工具函数、日志管理、错误处理、JSON处理、路径管理等功能
"""

from .common_utils import (
    get_local_ip,
    open_browser,
    get_network_info,
    generate_id,
    format_size,
    get_file_list,
    formate_reqs,
    is_remote_api,
    CaseNumberManager
)

from .logger import (
    setup_logging,
    setup_logger,
    get_logger,
    init_logging
)

from .error_handler import ErrorHandler

from .json_utils import safe_json_loads
from .api_response import api_success, api_error, normalize_message_response, normalize_api_response_payload

from .path_helper import (
    PROJECT_ROOT,
    get_config_path,
    get_logs_path,
    get_output_path,
    get_results_path,
    get_tests_path,
    get_resources_path,
    get_uploads_path,
    get_knowledge_uploads_path,
    get_documents_uploads_path,
    get_other_uploads_path
)

__all__ = [
    # common_utils
    'get_local_ip',
    'open_browser', 
    'get_network_info',
    'generate_id',
    'format_size',
    'get_file_list',
    'formate_reqs',
    'is_remote_api',
    'CaseNumberManager',
    
    # logger
    'setup_logging',
    'setup_logger',
    'get_logger',
    'init_logging',
    
    # error_handler
    'ErrorHandler',
    
    # json_utils
    'safe_json_loads',

    # api_response
    'api_success',
    'api_error',
    'normalize_message_response',
    'normalize_api_response_payload',
    
    # path_helper
    'PROJECT_ROOT',
    'get_config_path',
    'get_logs_path',
    'get_output_path',
    'get_results_path',
    'get_tests_path',
    'get_resources_path',
    'get_uploads_path',
    'get_knowledge_uploads_path',
    'get_documents_uploads_path',
    'get_other_uploads_path'
]


