from pathlib import Path

# 项目根路径
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 配置路径
def get_config_path():
    return PROJECT_ROOT / "configs"

# 日志路径
def get_logs_path():
    path = PROJECT_ROOT / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path

# 输出路径
def get_output_path():
    path = PROJECT_ROOT / "output"
    path.mkdir(parents=True, exist_ok=True)
    return path

# 结果路径
def get_results_path():
    path = PROJECT_ROOT / "results"
    path.mkdir(parents=True, exist_ok=True)
    return path

# 测试用例路径（支持指定平台）
def get_tests_path(platform=None):
    base_path = PROJECT_ROOT / "tests"
    if platform:
        path = base_path / platform.lower()
    else:
        path = base_path
    path.mkdir(parents=True, exist_ok=True)
    return path

# 资源路径
def get_resources_path():
    return PROJECT_ROOT / "resources"

# 上传文件路径
def get_uploads_path():
    """获取上传文件根目录"""
    path = PROJECT_ROOT / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path

# 知识库文件路径
def get_knowledge_uploads_path():
    """获取知识库文件上传路径"""
    path = get_uploads_path() / "knowledge"
    path.mkdir(parents=True, exist_ok=True)
    return path

# 文档文件路径
def get_documents_uploads_path():
    """获取文档文件上传路径"""
    path = get_uploads_path() / "documents"
    path.mkdir(parents=True, exist_ok=True)
    return path

# 其他文件路径
def get_other_uploads_path():
    """获取其他文件上传路径"""
    path = get_uploads_path() / "others"
    path.mkdir(parents=True, exist_ok=True)
    return path