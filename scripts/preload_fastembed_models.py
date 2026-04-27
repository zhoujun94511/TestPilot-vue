#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
FastEmbed 模型预下载脚本

用途：
    - 在部署前预下载 FastEmbed 模型，避免运行时外网依赖
    - 确保生产环境无隐式网络访问

使用方法：
    python scripts/preload_fastembed_models.py
    
    或指定模型：
    python scripts/preload_fastembed_models.py --model BAAI/bge-small-en-v1.5

环境变量：
    FASTEMBED_CACHE_DIR: 指定模型缓存目录（可选）
    
注意：
    - 首次运行需要网络连接
    - 模型下载后可重复执行（不会重复下载）
    - 生产环境部署前必须执行此脚本
"""
import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 使用简单的日志输出，避免导入复杂依赖
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_fastembed_cache_dir():
    """获取 FastEmbed 缓存目录"""
    cache_dir = os.getenv('FASTEMBED_CACHE_DIR')
    if cache_dir:
        logger.info(f"使用指定的 FastEmbed 缓存目录: {cache_dir}")
        return cache_dir
    
    # 对于预下载脚本，默认使用项目目录下的模型目录（用于打包）
    workspace_root = Path(__file__).parent.parent
    project_models_dir = workspace_root / 'models' / 'fastembed'
    
    # 无论目录是否存在，都使用项目目录（除非设置了环境变量）
    project_models_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"使用项目模型目录: {project_models_dir}")
    logger.info("提示：此目录会被打包到 dist/fastembed_cache")
    return str(project_models_dir)


def copy_huggingface_cache_to_project(hf_cache_dir: Path, project_cache_dir: Path):
    """
    将 HuggingFace 缓存中的模型文件复制到项目目录
    
    Args:
        hf_cache_dir: HuggingFace 缓存目录
        project_cache_dir: 项目模型目录
    """
    import shutil
    
    # 在 hub 目录下查找
    hub_dir = hf_cache_dir / 'hub'
    if not hub_dir.exists():
        # Windows 上可能在 AppData/Local/huggingface/hub
        local_app_data = os.getenv('LOCALAPPDATA')
        if local_app_data:
            alt_hub_dir = Path(local_app_data) / 'huggingface' / 'hub'
            if alt_hub_dir.exists():
                hub_dir = alt_hub_dir
                logger.info(f"使用 Windows 备选 HuggingFace hub 目录: {hub_dir}")
        
    if not hub_dir.exists():
        logger.warning(f"HuggingFace hub 目录不存在: {hub_dir}")
        return False
    
    # fastembed 可能使用不同的模型名称，需要查找所有可能的模型目录
    # 查找所有 models-- 开头的目录（这些是 HuggingFace 的模型目录）
    all_model_dirs = [d for d in hub_dir.iterdir() if d.is_dir() and d.name.startswith('models--')]
    
    if not all_model_dirs:
        logger.warning(f"未找到任何模型目录")
        return False
    
    logger.info(f"找到 {len(all_model_dirs)} 个模型目录，将全部复制到项目目录")
    
    # 创建项目目录下的 hub 子目录（fastembed 使用 HuggingFace Hub 结构）
    project_hub_dir = project_cache_dir / 'hub'
    project_hub_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制所有模型目录（fastembed 可能需要多个模型）
    copied_count = 0
    total_size = 0
    
    for model_dir in all_model_dirs:
        # 目标目录应该是 project_cache_dir/hub/models--xxx
        target_dir = project_hub_dir / model_dir.name
        try:
            if target_dir.exists():
                logger.info(f"  跳过已存在的目录: {target_dir.name}")
                # 计算已存在目录的大小
                files = list(target_dir.rglob('*'))
                size = sum(f.stat().st_size for f in files if f.is_file())
                total_size += size
                copied_count += 1
                continue
            
            logger.info(f"  复制: {model_dir.name} -> {target_dir.relative_to(project_cache_dir)}")
            shutil.copytree(model_dir, target_dir, dirs_exist_ok=True)
            
            # 计算大小
            files = list(target_dir.rglob('*'))
            size = sum(f.stat().st_size for f in files if f.is_file())
            total_size += size
            copied_count += 1
            
            logger.info(f"    大小: {size / 1024 / 1024:.2f} MB")
        except Exception as e:
            logger.error(f"  复制失败 {model_dir.name}: {e}")
            # 继续复制其他目录，不中断
            continue
    
    if copied_count > 0:
        logger.info(f"✅ 成功复制 {copied_count} 个模型目录到 {project_hub_dir.relative_to(project_cache_dir.parent.parent)}")
        logger.info(f"   总大小: {total_size / 1024 / 1024:.2f} MB")
        return True
    else:
        logger.warning("没有复制任何文件")
        return False


def preload_model(model_name: str):
    """
    预下载 FastEmbed 模型并复制到项目目录
    
    Args:
        model_name: 模型名称，如 'BAAI/bge-small-en-v1.5'
    """
    try:
        import os
        from fastembed import TextEmbedding
        
        logger.info(f"开始预下载 FastEmbed 模型: {model_name}")
        logger.info("注意：首次下载需要网络连接，可能需要几分钟...")
        
        # 获取项目模型目录
        project_cache_dir = Path(get_fastembed_cache_dir())
        project_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 先初始化模型（会自动下载到指定缓存目录）
        # 显式传递 cache_dir 确保模型下载到项目目录下的 hub 子目录
        # 这样可以匹配 build.spec 和 FastEmbedBackend 的预期结构
        project_hub_dir = project_cache_dir / "hub"
        project_hub_dir.mkdir(parents=True, exist_ok=True)
        model = TextEmbedding(model_name=model_name, cache_dir=str(project_hub_dir))
        
        # 测试编码以确认模型可用
        test_text = "test"
        embeddings = list(model.embed([test_text]))
        
        if not embeddings:
            logger.error(f"❌ 模型下载后测试失败: {model_name}")
            return False
        
        dimension = len(embeddings[0])
        logger.info(f"✅ 模型下载成功: {model_name}")
        logger.info(f"   维度: {dimension}")
        
        # 获取项目模型目录（已在上面初始化）
        
        # 从 HuggingFace 缓存复制到项目目录
        hf_cache_dir = Path(os.path.expanduser('~/.cache/huggingface'))
        logger.info(f"从 HuggingFace 缓存复制模型到项目目录...")
        logger.info(f"  源目录: {hf_cache_dir}")
        logger.info(f"  目标目录: {project_cache_dir}")
        
        # 如果已经成功下载到项目目录，即使复制全局缓存失败也认为成功
        copy_success = copy_huggingface_cache_to_project(hf_cache_dir, project_cache_dir)
        
        # 检查项目目录下是否已经有模型文件（fastembed 的目录结构）
        # BAAI/bge-small-en-v1.5 -> models--qdrant--bge-small-en-v1.5-onnx-q
        model_found = any(project_cache_dir.glob("models--*"))
        
        if copy_success or model_found:
            if model_found and not copy_success:
                logger.info(f"✅ 模型已存在于项目目录: {project_cache_dir}")
            else:
                logger.info(f"✅ 模型已复制到项目目录: {project_cache_dir}")
            logger.info("   此目录会被打包到 dist/fastembed_cache")
            return True
        else:
            logger.warning("⚠️ 模型复制失败，且项目目录中未找到模型文件")
            logger.warning("   打包时可能需要手动复制模型文件")
            return False
            
    except ImportError:
        logger.error("❌ fastembed 未安装，请运行: pip install fastembed")
        return False
    except Exception as e:
        logger.error(f"❌ 模型预下载失败: {e}", exc_info=True)
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='FastEmbed 模型预下载脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 下载默认模型
  python scripts/preload_fastembed_models.py
  
  # 下载指定模型
  python scripts/preload_fastembed_models.py --model BAAI/bge-base-en-v1.5
  
  # 指定缓存目录
  FASTEMBED_CACHE_DIR=/path/to/cache python scripts/preload_fastembed_models.py
        """
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default='BAAI/bge-small-en-v1.5',
        help='模型名称（默认: BAAI/bge-small-en-v1.5）'
    )
    
    args = parser.parse_args()
    
    cache_dir = get_fastembed_cache_dir()
    
    logger.info("=" * 60)
    logger.info("FastEmbed 模型预下载脚本")
    logger.info("=" * 60)
    logger.info(f"目标模型: {args.model}")
    logger.info(f"缓存目录: {cache_dir}")
    logger.info("")
    
    # 确保缓存目录存在
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    
    success = preload_model(args.model)
    
    if success:
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ 模型预下载完成")
        logger.info("=" * 60)
        logger.info("提示：模型已缓存，后续运行无需网络连接")
        sys.exit(0)
    else:
        logger.error("")
        logger.error("=" * 60)
        logger.error("❌ 模型预下载失败")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    main()








