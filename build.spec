# -*- mode: python ; coding: utf-8 -*-
"""
TestPilot PyInstaller 打包配置文件
Windows 平台专用

支持两种打包模式（由 build.bat 传入环境变量 TESTPILOT_BUILD_SLIM）：
- full（默认）：包含 sqlite-vec + FTS5 向量库，体积较大
- slim：不包含向量库，需运行前设置 ENABLE_VECTOR_STORE=false，体积更小
"""

import os
from pathlib import Path

# 精简打包：不打包 sqlite-vec / sqlite_vector_store，缩小体积
BUILD_SLIM = os.environ.get('TESTPILOT_BUILD_SLIM', '0') == '1'
if BUILD_SLIM:
    print("[INFO] Slim build: excluding sqlite-vec and sqlite_vector_store")

# 项目根目录 - spec 文件所在目录
# 在 PyInstaller 中，SPEC 变量包含 spec 文件的完整路径
try:
    project_root = Path(os.path.dirname(os.path.abspath(SPEC))).resolve()
except NameError:
    # 如果 SPEC 不存在，使用当前工作目录（build.spec 应该在项目根目录）
    project_root = Path(os.getcwd()).resolve()

print(f"[INFO] Project root: {project_root}")

block_cipher = None

# 收集所有需要的数据文件
# 检查路径是否存在，只添加存在的目录
datas = []

# 模板文件
templates_path = project_root / 'templates'
if templates_path.exists():
    datas.append((str(templates_path), 'templates'))
else:
    print(f"WARNING: Templates directory not found: {templates_path}")

# 静态文件
static_path = project_root / 'static'
if static_path.exists():
    datas.append((str(static_path), 'static'))
else:
    print(f"WARNING: Static directory not found: {static_path}")

# 配置文件
config_path = project_root / 'config'
if config_path.exists():
    datas.append((str(config_path), 'config'))
else:
    print(f"WARNING: Config directory not found: {config_path}")

# FastEmbed 模型文件（如果存在）
# 注意：打包前需要先运行 scripts/preload_fastembed_models.py 下载模型
# 优先使用项目目录下的模型（推荐，用于打包）
project_models_dir = project_root / 'models' / 'fastembed'
print(f"[INFO] Checking for FastEmbed models...")
print(f"[INFO] Project models directory: {project_models_dir}")
print(f"[INFO] Exists: {project_models_dir.exists()}")

if project_models_dir.exists():
    # 检查目录内容
    items = list(project_models_dir.iterdir())
    print(f"[INFO] Directory contains {len(items)} items")
    for item in items[:5]:  # 显示前5个
        print(f"[INFO]   - {item.name} ({'dir' if item.is_dir() else 'file'})")
    
    if items:
        # 将项目模型目录包含到打包中
        datas.append((str(project_models_dir), 'fastembed_cache'))
        print(f"[INFO] ✅ Found project models directory: {project_models_dir}")
        print(f"[INFO] ✅ Will include in package directory: fastembed_cache/")
        
        # 检查 hub 子目录
        hub_dir = project_models_dir / 'hub'
        if hub_dir.exists():
            hub_items = list(hub_dir.iterdir())
            print(f"[INFO] ✅ Found hub directory with {len(hub_items)} model directories")
        else:
            print(f"[WARNING] ⚠️ hub directory not found, but will still include models directory")
    else:
        print(f"[WARNING] ⚠️ Project models directory exists but is empty")
else:
    print(f"[WARNING] ⚠️ Project models directory does not exist")

# 如果项目目录没有模型，回退到用户目录下的缓存（如果存在）
if not (project_models_dir.exists() and any(project_models_dir.iterdir())):
    fastembed_cache_dir = os.path.expanduser('~/.cache/fastembed')
    hf_cache_dir = os.path.expanduser('~/.cache/huggingface')
    
    print(f"[INFO] Checking user cache directories...")
    print(f"[INFO] FastEmbed cache: {fastembed_cache_dir} (exists: {os.path.exists(fastembed_cache_dir)})")
    print(f"[INFO] HuggingFace cache: {hf_cache_dir} (exists: {os.path.exists(hf_cache_dir)})")
    
    # 优先检查 HuggingFace 缓存（fastembed 实际使用这个）
    if os.path.exists(hf_cache_dir):
        hf_hub_dir = Path(hf_cache_dir) / 'hub'
        if hf_hub_dir.exists() and any(hf_hub_dir.iterdir()):
            # 创建一个临时目录结构来打包
            # 注意：这里需要复制整个 HuggingFace 缓存，但为了简化，我们只提示用户
            print(f"[WARNING] ⚠️ Found HuggingFace cache but cannot auto-include")
            print(f"[WARNING] ⚠️ Please run: USE_PROJECT_MODELS=true python scripts/preload_fastembed_models.py")
    elif os.path.exists(fastembed_cache_dir) and any(Path(fastembed_cache_dir).iterdir()):
        datas.append((fastembed_cache_dir, 'fastembed_cache'))
        print(f"[INFO] ✅ Found FastEmbed cache in user directory: {fastembed_cache_dir}")
        print(f"[INFO] ✅ Will include in package directory: fastembed_cache/")
    else:
        print(f"[ERROR] ❌ FastEmbed models not found!")
        print(f"[ERROR] ❌ Please run: USE_PROJECT_MODELS=true python scripts/preload_fastembed_models.py")
        print(f"[ERROR] ❌ This will download models to: {project_models_dir}")

# 隐藏导入（PyInstaller 可能无法自动检测的模块）
hiddenimports = [
    # Flask 相关
    'flask',
    'flask_cors',
    'flask_session',
    'flask_sqlalchemy',
    'werkzeug',
    'jinja2',
    # 数据库
    'sqlalchemy',
    'sqlite3',
    # AI 模型相关
    'langchain',
    'langchain_core',
    'langchain_community',
    'langchain_openai',
    'langchain_google_genai',
    'langchain_deepseek',
    'langchain_ollama',
    'openai',
    'google.generativeai',
    # 'deepseek',  # 如果未安装，注释掉
    'ollama',
    # 向量数据库
    'fastembed',
    'onnxruntime',
    # 文档处理
    'docx',
    'openpyxl',
    'PyPDF2',
    'yaml',
    'pandas',
    # 工具库
    'colorlog',
    'dotenv',  # python-dotenv 包的导入名是 dotenv
    'requests',
    'tiktoken',
    # WSGI 服务器（可选，但建议包含）
    'waitress',  # Windows 生产环境 WSGI 服务器
    # 其他
    'pydantic',
    'pydantic_settings',
    'typing_extensions',
    'concurrent.futures',
    'threading',
    'multiprocessing',
    # pkg_resources 相关依赖（setuptools 需要）
    'pkg_resources',
    'setuptools',
    'setuptools._vendor.jaraco',
    'setuptools._vendor.jaraco.text',
    'setuptools._vendor.jaraco.functools',
    'setuptools._vendor.jaraco.context',
    'jaraco',
    'jaraco.text',
    'jaraco.functools',
    'jaraco.context',
    # huggingface-hub 相关（fastembed 需要）
    'huggingface_hub',
    'hf_xet',  # 虽然可选，但 huggingface-hub 可能在运行时尝试导入
]

# 排除的模块（减小打包体积）
# 只排除明确不需要的模块，避免影响运行时依赖
excludes = [
    'matplotlib',
    'numpy.distutils',
    'scipy',
    'pandas.tests',
    'pytest',
    'tkinter',
    'unittest',
    'IPython',
    'jupyter',
    'notebook',
    # 注意：不要排除 hf_xet，虽然它是可选的，但 huggingface-hub 可能在运行时尝试导入它
    # 'hf_xet',  # 已移除，避免运行时导入错误
    # 不要排除以下模块，它们可能被其他包需要：
    # 'setuptools',  # pkg_resources 需要
    # 'distutils',   # 某些包可能需要
    # 'email',       # pkg_resources 需要
    # 'http',        # 可能被其他包使用
    # 'urllib3.packages.six',  # 可能被其他包使用
]
if BUILD_SLIM:
    excludes.extend([
        'sqlite_vec',
        'utils.utils_ai_models.sqlite_vector_store',
    ])

# 收集二进制文件（DLL 等）
binaries = []

# sqlite-vec 扩展 DLL（slim 模式不包含，避免依赖）
# 注意：sqlite_vec.load() 使用 loadable_path() 查找 vec0（无扩展名）
# 在 Windows 上会自动添加 .dll，所以需要将 DLL 放在 sqlite_vec 包目录下
if not BUILD_SLIM:
    try:
        import sqlite_vec
        sqlite_vec_path = os.path.dirname(sqlite_vec.__file__)
        vec0_dll = os.path.join(sqlite_vec_path, 'vec0.dll')
        if os.path.exists(vec0_dll):
            # 将 DLL 添加到 binaries，目标路径是 sqlite_vec 包目录
            # 格式：(源路径, 目标目录)
            binaries.append((vec0_dll, 'sqlite_vec'))
            print(f"[INFO] Found sqlite-vec DLL: {vec0_dll}")
            print(f"[INFO] Will include in package directory: sqlite_vec/")
        else:
            print(f"[WARNING] sqlite-vec DLL not found: {vec0_dll}")
    except Exception as e:
        print(f"[WARNING] Could not find sqlite-vec DLL: {e}")
else:
    print("[INFO] Slim build: skipping sqlite-vec DLL")

a = Analysis(
    ['run.py'],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TestPilot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 保留控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'static' / 'pic' / 'wavicon.ico') if (project_root / 'static' / 'pic' / 'wavicon.ico').exists() else None,  # 应用图标
)

