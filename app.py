#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import atexit
import signal
import subprocess
import sys
import time
import logging
import warnings
import threading
import webbrowser
from pathlib import Path
from typing import Optional
from flask_session import Session
from config.settings import settings
from utils.utils_core.logger import get_logger
from models.models import db, init_database
from utils.utils_ai_models.embeddings import create_vector_db
from utils.utils_core.common_utils import get_local_ip, resolve_request_locale
from utils.utils_core.api_response import normalize_api_response_payload
from flask import Flask, jsonify, send_from_directory, Response, make_response, request

FRONTEND_ROOT = Path(__file__).resolve().parent / 'frontend'
FRONTEND_PUBLIC = FRONTEND_ROOT / 'public'
FRONTEND_DIST = FRONTEND_ROOT / 'dist'
# Vite dev server；开发态 UI 应访问此端口才有热更新
FRONTEND_DEV_PORT = 5173
# 页面只从本站取脚本、图片和接口；模型回复里即使混进外链图片也不会被浏览器请求
SPA_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; "
    "object-src 'none'; base-uri 'self'; frame-ancestors 'self'"
)

# 添加项目根目录到 Python 路径（与 run.py 一致：仓库根即 TestPilot-vue）
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# 禁用各种遥测和警告
# noinspection SpellCheckingInspection
os.environ.update({
    "CHROMA_TELEMETRY_ENABLED": "false",
    "CHROMA_DISABLE_TELEMETRY": "true",
    "POSTHOG_DISABLED": "true",
    "POSTHOG_OPT_OUT_CAPTURING": "true",
    "OTEL_SDK_DISABLED": "true",
    "OTEL_TRACES_EXPORTER": "none",
    "OTEL_METRICS_EXPORTER": "none",
    "OTEL_LOGS_EXPORTER": "none",
    "LANGCHAIN_TRACING_V2": "false",
    "LANGCHAIN_API_KEY": "",
    # Windows 多线程安全配置
    "CHROMA_ALLOW_RESET": "true",
    "SQLITE_THREADSAFE": "1",
    # 抑制 Google Abseil 库的警告（Gemini SDK 依赖）
    "GLOG_minloglevel": "2",  # 只显示 ERROR 及以上级别
    "ABSL_MIN_LOG_LEVEL": "2"  # Abseil 最小日志级别
})

# 初始化日志系统
from utils.utils_core.logger import init_logging

init_logging()

# 禁用特定日志记录器
logging.getLogger("chromadb.telemetry.product.posthog").disabled = True
logging.getLogger("posthog").disabled = True
logging.getLogger("chromadb.telemetry").disabled = True
# 禁用 transformers 库的警告（项目使用 FastEmbed，不需要 PyTorch/TensorFlow）
logging.getLogger("transformers").setLevel(logging.ERROR)
# 抑制 Google Abseil 库的警告（Gemini SDK 依赖）
logging.getLogger("absl").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")
# 抑制 transformers 库关于 PyTorch/TensorFlow 的警告
warnings.filterwarnings("ignore", message=".*PyTorch.*TensorFlow.*Flax.*")
warnings.filterwarnings("ignore", message=".*None of PyTorch.*")
# 抑制 Abseil 库的 STDERR 警告
warnings.filterwarnings("ignore", message=".*All log messages before absl::InitializeLog.*")


def render_vue_index(base_path: str = '/') -> Response:
    """渲染 Vue 构建产物。"""
    index_file = FRONTEND_DIST / 'index.html'
    if not index_file.exists():
        return make_response(jsonify({
            'success': False,
            'message': 'Vue 前端构建产物不存在，请先执行 frontend 构建',
            'code': 503
        }), 503)

    html = index_file.read_text(encoding='utf-8')
    html = html.replace('__TESTPILOT_BASE_PATH__', base_path)
    response = Response(html, mimetype='text/html')
    response.headers['Content-Security-Policy'] = SPA_CONTENT_SECURITY_POLICY
    # 避免浏览器长期缓存 SPA 入口，导致仍加载旧 hash 的 JS/CSS
    response.headers['Cache-Control'] = 'no-store, max-age=0, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response


def serve_vue_asset(filename: str):
    """提供 Vue 构建产物静态资源。"""
    asset_dir = FRONTEND_DIST / 'assets'
    if not asset_dir.exists():
        return '', 404
    return send_from_directory(asset_dir, filename)


def serve_frontend_public_asset(*parts: str):
    """提供前端 public 目录中的静态资源，优先使用构建产物。"""
    dist_path = FRONTEND_DIST.joinpath(*parts)
    if dist_path.exists():
        return send_from_directory(dist_path.parent, dist_path.name)

    public_path = FRONTEND_PUBLIC.joinpath(*parts)
    if public_path.exists():
        return send_from_directory(public_path.parent, public_path.name)

    return '', 404


def _local_secret_key(key_file: Path) -> str:
    """读取或生成本机持久化的随机会话密钥，重启后已有会话仍然有效。"""
    import secrets

    try:
        existing = key_file.read_text(encoding='utf-8').strip()
        if len(existing) >= 32:
            return existing
    except OSError:
        pass
    key = secrets.token_urlsafe(48)
    try:
        key_file.write_text(key, encoding='utf-8')
        os.chmod(key_file, 0o600)
    except OSError as exc:
        get_logger(__name__).warning('会话密钥无法落盘，重启后需要重新登录: %s', exc)
    return key


def create_app():
    """创建Flask应用实例"""
    # 创建共享的 logger，避免在内部函数中重复定义
    logger = get_logger(__name__)

    # 创建Flask应用
    flask_app = Flask(__name__)

    # 加载配置
    flask_app.config.from_object(settings)
    settings.init_app(flask_app)

    from utils.utils_core.api_error_handler import is_placeholder_secret

    secret_key = str(flask_app.config.get('SECRET_KEY') or '')
    if (
        len(secret_key) < 16
        or secret_key == 'testpilot-secret-key-2024'
        or is_placeholder_secret(secret_key)
    ):
        flask_app.config['SECRET_KEY'] = _local_secret_key(project_root / '.secret_key')
        logger.warning('SECRET_KEY 为默认值或占位值，已改用本机随机密钥；多实例部署请在 .env 设置同一个随机 SECRET_KEY')

    if not flask_app.config.get('AUTH_REQUIRE_AUTH') and not flask_app.config.get('DEBUG'):
        logger.warning('AUTH_REQUIRE_AUTH=false：所有接口无需登录且不做部门隔离，仅适合本机单人使用')

    if not flask_app.config.get('SESSION_COOKIE_SECURE'):
        logger.warning('SESSION_COOKIE_SECURE=false：会话 Cookie 会随 HTTP 发送。本机 HTTP 保持关闭；HTTPS 部署请在 .env 设为 true')

    # 初始化扩展
    db.init_app(flask_app)

    # 配置flask_session
    Session(flask_app)

    # 初始化数据库
    init_database(flask_app)
    _warn_pending_password_changes(flask_app)

    # 注入功能开关到所有模板
    @flask_app.context_processor
    def inject_feature_flags():
        return {
            'ENABLE_VECTOR_STORE': getattr(settings, 'ENABLE_VECTOR_STORE', True)
        }

    # 添加根路径路由
    @flask_app.route('/')
    def index():
        try:
            return render_vue_index()
        except Exception as ex_index:
            logger.error(f"渲染首页失败: {str(ex_index)}")
            return jsonify({'error': '首页渲染失败'}), 500

    @flask_app.route('/assets/<path:filename>')
    def vue_assets(filename: str):
        return serve_vue_asset(filename)

    @flask_app.route('/pic/<path:filename>')
    def public_pic(filename: str):
        return serve_frontend_public_asset('pic', filename)

    @flask_app.route('/tsvg/<path:filename>')
    def public_tsvg(filename: str):
        return serve_frontend_public_asset('tsvg', filename)

    @flask_app.route('/<path:path>')
    def frontend_fallback(path: str):
        if path.startswith(('api/', 'static/', 'assets/', 'pic/', 'tsvg/', 'favicon.ico')):
            return '', 404

        return render_vue_index()

    @flask_app.route('/favicon.ico')
    def favicon():
        try:
            return serve_frontend_public_asset('pic', 'favicon.ico')
        except Exception as ex_favicon:
            logger.warning(f"favicon文件未找到: {str(ex_favicon)}")
            return '', 404

    # 添加健康检查路由
    @flask_app.route('/health')
    def health_check():
        """健康检查"""
        return jsonify({
            'status': 'healthy',
            'message': 'TestPilot is running',
            'version': '1.0.0'
        })

    # 添加模型状态检查路由
    @flask_app.route('/api/model-status')
    def model_status():
        """获取模型状态信息（实时返回当前配置的AI提供商状态）"""
        try:
            from services.auth_service import auth_required, current_user

            if auth_required() and current_user() is None:
                return jsonify({
                    'success': False,
                    'code': 'UNAUTHORIZED',
                    'message_key': 'common.errors.http401',
                    'message': '未登录或会话已过期',
                }), 401

            # 实时从settings读取当前的AI提供商
            current_company = settings.DEFAULT_COMPANY
            status_data = flask_app.config.get('MODEL_STATUS')

            # 如果缓存的状态与当前配置不匹配，重新检查
            if not status_data or status_data.get('company') != current_company:
                if str(current_company or '').upper() != "OLLAMA":
                    try:
                        from utils.utils_core.remote_model_checker import model_checker
                        status_data = model_checker.get_model_status_summary(current_company)
                        flask_app.config['MODEL_STATUS'] = status_data
                    except Exception as check_error:
                        get_logger(__name__).warning(f"实时检查模型状态失败: {check_error}")
                        status_data = {
                            'company': current_company,
                            'service_name': current_company.title(),
                            'is_available': False,
                            'message': '模型状态检查失败',
                            'details': {'error_type': 'check_failed'},
                            'timestamp': None
                        }
                else:
                    status_data = {
                        'company': current_company,
                        'service_name': 'Ollama',
                        'is_available': True,
                        'message': 'Ollama 本地模型',
                        'details': {'note': '本地模型，无需远程检查'},
                        'timestamp': None
                    }

            return jsonify({
                'success': True,
                'code': 'MODEL_STATUS_SUCCESS',
                'message_key': 'model.message.statusLoaded',
                'message': 'Model status loaded successfully',
                'message_params': {},
                'data': status_data
            })
        except Exception as status_error:
            get_logger(__name__).error(f"获取模型状态失败: {status_error}")
            return jsonify({
                'success': False,
                'code': 'MODEL_STATUS_FAILED',
                'message_key': 'model.message.statusFailed',
                'message': 'Failed to load model status',
                'message_params': {},
                'error': 'internal_error'
            }), 500

    # 注册蓝图
    register_blueprints(flask_app)
    from services.auth_gate import install_auth_gate
    install_auth_gate(flask_app)

    # 注册错误处理器（先注册特定错误，后注册通用异常处理）
    register_error_handlers(flask_app)

    # 添加全局异常处理（最后注册，作为兜底处理）
    @flask_app.errorhandler(Exception)
    def handle_exception(exc):
        """全局异常处理器"""
        from werkzeug.exceptions import HTTPException

        # 405、413 等 HTTP 错误没有单独的处理器时也会落到这里，要保留原状态码
        if isinstance(exc, HTTPException):
            status = exc.code or 500
            if not request.path.startswith('/api/'):
                return exc
            return jsonify({
                'success': False,
                'error': exc.name,
                'code': status,
                'error_code': 'FILE_TOO_LARGE' if status == 413 else f'HTTP_{status}',
                'message': exc.description or exc.name,
            }), status

        error_type = type(exc).__name__
        error_msg = str(exc)

        # 特别处理 Windows 访问冲突错误
        if "access violation" in error_msg.lower() or "0xC0000005" in error_msg:
            logger.critical(f"检测到访问冲突错误: {error_type} - {error_msg}", exc_info=True)
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Memory access error, please try again later',
                'code': 'ACCESS_VIOLATION',
                'message_key': 'errors.accessViolation',
                'error_type': 'access_violation'
            }), 500

        # 处理其他严重错误
        logger.error(f"未处理的异常: {error_type} - {error_msg}", exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Internal server error, please try again later',
            'code': 'INTERNAL_SERVER_ERROR',
            'message_key': 'errors.internalServerError',
        }), 500

    # 添加请求前后处理（捕获可能的访问冲突）
    @flask_app.before_request
    def before_request():
        """请求前处理"""
        try:
            # 可以在这里添加请求前的安全检查
            pass
        except Exception as request_error:
            logger.error(f"请求前处理失败: {request_error}", exc_info=True)

    @flask_app.after_request
    def after_request(response):
        """请求后处理"""
        try:
            if request.path.startswith('/api/'):
                resolved_locale = resolve_request_locale(request)
                response.headers['X-TestPilot-Locale'] = resolved_locale
            if request.path.startswith('/api/') and response.is_json:
                payload = response.get_json(silent=True)
                if isinstance(payload, dict):
                    normalized = normalize_api_response_payload(
                        payload,
                        path=request.path,
                        method=request.method,
                        status_code=response.status_code,
                    )
                    if normalized is not payload:
                        new_response = jsonify(normalized)
                        new_response.status_code = response.status_code
                        return new_response
            return response
        except Exception as response_error:
            logger.error(f"请求后处理失败: {response_error}", exc_info=True)
            return response

    # 初始化应用上下文
    with flask_app.app_context():
        try:
            init_app_context(flask_app)
        except Exception as init_error:
            logger.critical(f"应用上下文初始化失败: {init_error}", exc_info=True)
            # 不要在这里退出，让应用继续运行但记录错误

    return flask_app


def register_blueprints(flask_app: Flask) -> None:
    """注册蓝图"""
    from blueprints.cases import cases_bp
    from blueprints.documents import documents_bp
    from blueprints.knowledge import knowledge_bp
    from blueprints.export import export_bp
    from blueprints.stats import stats_bp
    from blueprints.chat import chat_bp
    from blueprints.config_center import config_center_bp
    from blueprints.auth import auth_bp

    # 注册API蓝图
    flask_app.register_blueprint(auth_bp, url_prefix='/api/auth')
    from blueprints.projects import projects_bp
    flask_app.register_blueprint(projects_bp, url_prefix='/api')
    flask_app.register_blueprint(cases_bp, url_prefix='/api/cases')
    flask_app.register_blueprint(documents_bp, url_prefix='/api/documents')
    flask_app.register_blueprint(knowledge_bp, url_prefix='/api/knowledge')
    flask_app.register_blueprint(export_bp, url_prefix='/api/export')
    flask_app.register_blueprint(stats_bp, url_prefix='/api/stats')
    flask_app.register_blueprint(chat_bp, url_prefix='/api/chat')
    flask_app.register_blueprint(config_center_bp)
    from blueprints.experimental_actions import experimental_actions_bp
    flask_app.register_blueprint(experimental_actions_bp)


def register_error_handlers(flask_app: Flask) -> None:
    """注册错误处理器"""
    from utils.utils_performance_monitoring.token_session import TokenSessionLimitExceeded

    @flask_app.errorhandler(TokenSessionLimitExceeded)
    def token_session_limit(error: TokenSessionLimitExceeded) -> tuple:
        payload = error.to_normalize_dict()
        return jsonify({
            'success': False,
            'message': payload['message'],
            'error': payload['error_code'],
            'error_code': payload['error_code'],
            'message_key': payload['message_key'],
            'message_params': payload['message_params'],
            'retryable': False,
        }), 429

    @flask_app.errorhandler(400)
    def bad_request(_) -> tuple:
        return jsonify({
            'error': 'Bad Request',
            'message': '请求参数错误',
            'code': 400
        }), 400

    @flask_app.errorhandler(404)
    def not_found(_) -> tuple:
        return jsonify({
            'error': 'Not Found',
            'message': '请求的资源不存在',
            'code': 404
        }), 404

    @flask_app.errorhandler(500)
    def internal_error(_) -> tuple:
        return jsonify({
            'error': 'Internal Server Error',
            'message': '服务器内部错误',
            'code': 500
        }), 500


def _warn_pending_password_changes(flask_app: Flask) -> None:
    """启动时只报告还有多少账号必须先改密，不写出密码。"""
    try:
        with flask_app.app_context():
            from models.auth_models import User

            pending = User.query.filter_by(must_change_password=True, is_active=True).count()
        if pending:
            get_logger(__name__).warning(
                '%s 个账号仍在使用默认密码，登录后必须先修改才能使用业务接口',
                pending,
            )
    except Exception as exc:
        get_logger(__name__).warning('默认密码检查跳过: %s', exc)


def warm_model_status(flask_app: Flask, company: str) -> None:
    """后台检查远程模型。线程里要先进入应用上下文，才能读到配置中心里的密钥。"""
    try:
        with flask_app.app_context():
            try:
                from utils.utils_core.remote_model_checker import model_checker

                status = model_checker.get_model_status_summary(company)
                if not status.get('is_available'):
                    get_logger(__name__).warning("模型可用性检查失败: %s", status.get('message'))
                flask_app.config['MODEL_STATUS'] = status
            finally:
                db.session.remove()
    except Exception as check_error:
        get_logger(__name__).error("模型可用性检查失败: %s", check_error)


def init_app_context(flask_app: Flask) -> None:
    """初始化应用上下文"""
    try:
        try:
            flask_app.logger = get_logger('testpilot')
            get_logger(__name__).debug('应用日志已就绪')
        except Exception as log_error:
            get_logger(__name__).warning('应用日志初始化跳过: %s', log_error)

        # 从配置中心加载配置（优先级：配置中心 > .env）
        try:
            settings.load_from_config_center()
        except Exception as e:
            get_logger(__name__).warning(f"从配置中心加载配置失败，使用 .env 配置: {e}")

        # 检查是否跳过 LLM 初始化（用于初始化脚本等场景）
        skip_llm_init = os.getenv('SKIP_LLM_INIT', 'false').lower() == 'true'

        if not skip_llm_init:
            # 检查远程模型可用性（非Ollama本地模型）
            if str(settings.DEFAULT_COMPANY or '').upper() != "OLLAMA":
                # 远程探测最长要等十秒，放到后台，避免拖慢启动
                threading.Thread(
                    target=warm_model_status,
                    args=(flask_app, settings.DEFAULT_COMPANY),
                    name='model-status-warmup',
                    daemon=True,
                ).start()

            # 初始化LLM
            try:
                # 为不同场景初始化LLM实例
                from utils.utils_ai_models.get_llm import get_llm

                flask_app.llm = get_llm(settings.DEFAULT_COMPANY, use_case='chat')  # AI聊天
                flask_app.llm_case_generation = get_llm(settings.DEFAULT_COMPANY, use_case='case_generation')  # 用例生成
                flask_app.llm_requirement_analysis = get_llm(settings.DEFAULT_COMPANY,
                                                             use_case='requirement_analysis')  # 需求分析
                get_logger(__name__).info("LLM初始化成功！")
            except ValueError as key_error:
                get_logger(__name__).warning(
                    "当前提供商 %s 未就绪，已跳过模型初始化: %s",
                    settings.DEFAULT_COMPANY,
                    key_error,
                )
                flask_app.llm = None
                flask_app.llm_case_generation = None
                flask_app.llm_requirement_analysis = None
            except Exception as e:
                get_logger(__name__).error(f"LLM初始化失败: {e}")
                flask_app.llm = None
                flask_app.llm_case_generation = None
                flask_app.llm_requirement_analysis = None
        else:
            # 跳过 LLM 初始化，设置默认值
            flask_app.llm = None
            flask_app.llm_case_generation = None
            flask_app.llm_requirement_analysis = None
            get_logger(__name__).debug("跳过 LLM 初始化（SKIP_LLM_INIT=true）")

        # 初始化向量数据库（ENABLE_VECTOR_STORE=false 时不加载 sqlite-vec/FTS5，可缩减打包体积）
        if not getattr(settings, 'ENABLE_VECTOR_STORE', True):
            flask_app.vector_db = None
            get_logger(__name__).info("向量数据库已禁用（ENABLE_VECTOR_STORE=false），知识库与 RAG 相关功能不可用")
        else:
            try:
                flask_app.vector_db = create_vector_db()
                get_logger(__name__).info("向量数据库初始化成功！")
                try:
                    from services.knowledge_vector_scope import backfill_all_knowledge_vector_metadata

                    backfill_all_knowledge_vector_metadata(flask_app.vector_db)
                except Exception as meta_error:
                    get_logger(__name__).warning('知识库向量 metadata 回填跳过: %s', meta_error)
            except Exception as e:
                get_logger(__name__).error(f"向量数据库初始化失败: {e}")
                flask_app.vector_db = None

        try:
            from services.app_background_jobs import start_background_jobs

            start_background_jobs(flask_app)
        except Exception as job_error:
            get_logger(__name__).warning('后台任务启动跳过: %s', job_error)

        get_logger(__name__).info("应用上下文初始化完成！")
    except Exception as e:
        get_logger(__name__).error(f"应用上下文初始化失败: {e}")


def open_browser(ip: str, web_port: int) -> None:
    """Open browser after a delay

    Args:
        ip: IP address to open
        web_port: Port number to use
    """
    time.sleep(1.5)
    webbrowser.open(f'http://{ip}:{web_port}')


def sync_frontend_env(host: str, port: int, *, proxy_host: Optional[str] = None):
    """写入 Vite 开发代理目标。同机开发时应用 127.0.0.1，避免 LAN IP 变更导致 /api 全 502。"""
    logger = get_logger(__name__)
    try:
        env_file = FRONTEND_ROOT / '.env.development.local'
        target_host = (proxy_host or host or '127.0.0.1').strip()
        if target_host == '0.0.0.0':
            target_host = '127.0.0.1'
        flask_target = f"http://{target_host}:{port}"
        env_file.write_text(
            f"VITE_FLASK_TARGET={flask_target}\n",
            encoding='utf-8'
        )
        logger.info(f"[SYNC] 前端代理地址已更新: {flask_target} (Flask bind 参考: {host}:{port})")
    except Exception as e:
        logger.error(f"[SYNC ERROR] 写入前端 env 失败: {e}", exc_info=True)


_FRONTEND_PROC: Optional[subprocess.Popen] = None


def stop_frontend() -> None:
    """停止 run.py 拉起的前端 dev 进程（Windows 下清理 npm/node 子树）。"""
    global _FRONTEND_PROC
    logger = get_logger(__name__)
    proc = _FRONTEND_PROC
    _FRONTEND_PROC = None
    os.environ.pop('FRONTEND_STARTED', None)
    if proc is None:
        return
    if proc.poll() is not None:
        return
    try:
        if sys.platform == 'win32':
            subprocess.run(
                ['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
        logger.info("前端 dev 进程已停止")
    except Exception as e:
        logger.warning(f"停止前端 dev 进程时出错: {e}")


def start_frontend():
    global _FRONTEND_PROC
    logger = get_logger(__name__)
    try:
        if _FRONTEND_PROC is not None and _FRONTEND_PROC.poll() is None:
            logger.info("前端 dev 已在运行 (pid=%s)，跳过重复启动", _FRONTEND_PROC.pid)
            return

        os.environ["FRONTEND_STARTED"] = "1"

        npm_cmd = 'npm.cmd' if sys.platform == 'win32' else 'npm'
        # 勿继承 Flask 的 DEBUG=true：Tailwind PostCSS 会据此打开 JIT 控制台计时日志
        frontend_env = os.environ.copy()
        frontend_env.pop("DEBUG", None)
        # 勿用 shell=True：否则会多一层 cmd.exe，Ctrl+C 退出时出现 GBK「终止批处理(Y/N)?」并在 UTF-8 终端乱码
        _FRONTEND_PROC = subprocess.Popen(
            [npm_cmd, 'run', 'dev'],
            cwd=str(FRONTEND_ROOT),
            shell=False,
            env=frontend_env,
        )
        logger.info(
            "前端 Vite 已启动 (pid=%s)，开发 UI: http://127.0.0.1:%s （热更新）",
            _FRONTEND_PROC.pid,
            FRONTEND_DEV_PORT,
        )
    except Exception as e:
        logger.error(f"启动前端失败: {e}", exc_info=True)


def register_shutdown_handlers() -> None:
    """Ctrl+C / 终止时先停前端子进程，避免 Windows cmd 批处理确认乱码。"""
    logger = get_logger(__name__)

    def _shutdown(signum=None, _frame=None):
        label = 'SIGINT' if signum == signal.SIGINT else ('SIGTERM' if signum == signal.SIGTERM else 'exit')
        logger.info("正在退出 TestPilot (%s)...", label)
        stop_frontend()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, _shutdown)
    atexit.register(stop_frontend)


# 创建应用实例（用于直接运行 app.py）
# 注释掉自动创建，避免重复初始化 如果需要
# app = create_app()


if __name__ == '__main__':
    host_ip = get_local_ip()
    server_port = 5001

    app = create_app()

    browser_thread = threading.Thread(
        target=open_browser,
        args=(host_ip, server_port)
    )

    # 绑定局域网 IP 时交互式调试台等于把远程执行代码的入口暴露出去
    app.run(
        host=host_ip,
        port=server_port,
        debug=True,
        use_reloader=False,
        use_debugger=False,
    )
