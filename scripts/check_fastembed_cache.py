#!/usr/bin/python
# -*- coding: utf-8 -*-
"""检查 fastembed 模型的实际缓存位置"""
import os
from pathlib import Path

# 检查可能的缓存位置
cache_locations = [
    os.path.expanduser('~/.cache/fastembed'),
    os.path.expanduser('~/.cache/huggingface'),
    os.path.expanduser('~/.cache/huggingface/hub'),
    Path(__file__).parent / 'models' / 'fastembed',
]

print("=" * 60)
print("检查 FastEmbed 模型缓存位置")
print("=" * 60)

for cache_dir in cache_locations:
    cache_path = Path(cache_dir)
    print(f"\n检查: {cache_path}")
    print(f"  存在: {cache_path.exists()}")
    
    if cache_path.exists():
        # 查找所有文件
        all_files = list(cache_path.rglob('*'))
        files_only = [f for f in all_files if f.is_file()]
        dirs_only = [f for f in all_files if f.is_dir()]
        
        print(f"  总条目: {len(all_files)} (文件: {len(files_only)}, 目录: {len(dirs_only)})")
        
        if files_only:
            total_size = sum(f.stat().st_size for f in files_only)
            print(f"  总大小: {total_size / 1024 / 1024:.2f} MB")
            print(f"  前5个文件:")
            for f in files_only[:5]:
                size_mb = f.stat().st_size / 1024 / 1024
                print(f"    {f.name} ({size_mb:.2f} MB)")
        
        # 查找 BGE 相关文件
        bge_files = [f for f in all_files if 'bge' in f.name.lower() or 'BAAI' in str(f)]
        if bge_files:
            print(f"  找到 BGE 相关文件: {len(bge_files)}")
            for f in bge_files[:3]:
                print(f"    {f}")

print("\n" + "=" * 60)
print("检查环境变量")
print("=" * 60)
print(f"FASTEMBED_CACHE_DIR: {os.getenv('FASTEMBED_CACHE_DIR', '未设置')}")
print(f"HF_HOME: {os.getenv('HF_HOME', '未设置')}")
print(f"HUGGINGFACE_HUB_CACHE: {os.getenv('HUGGINGFACE_HUB_CACHE', '未设置')}")

