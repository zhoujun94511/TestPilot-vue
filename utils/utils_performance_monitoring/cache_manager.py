#!/usr/bin/python
# -*- coding: utf-8 -*-
import hashlib
import pickle
import os
import time
from typing import Any, Optional
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    """缓存管理器"""

    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    @staticmethod
    def _get_cache_key(data: Any) -> str:
        """生成缓存键"""
        data_str = str(data)
        return hashlib.md5(data_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{cache_key}.pkl")

    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        try:
            cache_path = self._get_cache_path(key)
            if os.path.exists(cache_path):
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
        return None

    def set(self, key: str, data: Any, ttl: int = 3600):
        """设置缓存数据，支持TTL（生存时间）"""
        try:
            cache_path = self._get_cache_path(key)

            # 创建包含数据和过期时间的缓存对象
            cache_data = {
                'data': data,
                'expires_at': time.time() + ttl,
                'created_time': time.time()
            }

            # 修复类型注解问题：使用类型忽略注释
            with open(cache_path, 'wb') as f:  # type: ignore
                pickle.dump(cache_data, f) # type: ignore[arg-type]

            logger.debug(f"缓存设置成功: {key}, TTL: {ttl}秒")
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")

    def get_with_ttl(self, key: str) -> Optional[Any]:
        """获取缓存数据，自动检查TTL"""
        try:
            cache_path = self._get_cache_path(key)
            if os.path.exists(cache_path):
                with open(cache_path, 'rb') as f:
                    cache_data = pickle.load(f)

                # 检查是否过期
                if isinstance(cache_data, dict) and 'expires_at' in cache_data:
                    if time.time() > cache_data['expires_at']:
                        # 缓存已过期，删除文件
                        self.delete(key)
                        logger.debug(f"缓存已过期: {key}")
                        return None
                    return cache_data['data']
                else:
                    # 兼容旧格式缓存
                    return cache_data
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
        return None

    def delete(self, key: str):
        """删除缓存数据"""
        try:
            cache_path = self._get_cache_path(key)
            if os.path.exists(cache_path):
                os.remove(cache_path)
                logger.debug(f"缓存删除成功: {key}")
        except Exception as e:
            logger.error(f"删除缓存失败: {e}")

    def clear(self):
        """清空所有缓存"""
        try:
            for file in os.listdir(self.cache_dir):
                if file.endswith('.pkl'):
                    os.remove(os.path.join(self.cache_dir, file))
            logger.info("所有缓存已清空")
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")

    def get_cache_size(self) -> int:
        """获取缓存大小（字节）"""
        try:
            total_size = 0
            for file in os.listdir(self.cache_dir):
                if file.endswith('.pkl'):
                    file_path = os.path.join(self.cache_dir, file)
                    total_size += os.path.getsize(file_path)
            return total_size
        except Exception as e:
            logger.error(f"获取缓存大小失败: {e}")
            return 0

    def get_cache_info(self) -> dict:
        """获取缓存信息"""
        try:
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.pkl')]
            total_size = self.get_cache_size()

            return {
                'file_count': len(cache_files),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'cache_dir': self.cache_dir
            }
        except Exception as e:
            logger.error(f"获取缓存信息失败: {e}")
            return {}

    def cleanup_expired(self):
        """清理过期的缓存文件"""
        try:
            cleaned_count = 0
            for file in os.listdir(self.cache_dir):
                if file.endswith('.pkl'):
                    file_path = os.path.join(self.cache_dir, file)
                    try:
                        with open(file_path, 'rb') as f:
                            cache_data = pickle.load(f)

                        if isinstance(cache_data, dict) and 'expires_at' in cache_data:
                            if time.time() > cache_data['expires_at']:
                                os.remove(file_path)
                                cleaned_count += 1
                    except (pickle.PickleError, EOFError, FileNotFoundError) as file_error:
                        # 修复：使用更具体的异常处理
                        logger.warning(f"缓存文件损坏，将删除: {file_path}, 错误: {file_error}")
                        try:
                            os.remove(file_path)
                            cleaned_count += 1
                        except OSError as remove_error:
                            logger.error(f"无法删除损坏的缓存文件: {file_path}, 错误: {remove_error}")

            if cleaned_count > 0:
                logger.info(f"清理了 {cleaned_count} 个过期缓存文件")
            return cleaned_count
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")
            return 0


# 全局缓存管理器
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """获取缓存管理器实例（单例模式）"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager