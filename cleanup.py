#!/usr/bin/env python
"""
项目清理脚本
用于删除不必要的文件，精简项目结构
"""
import os
import shutil
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 需要保留的主要文件
KEEP_FILES = [
    # 核心Python文件
    'run.py',
    'requirements.txt',
    '.env',
    '.env.example',
    '.gitignore',
    'README.md',
    '设计文档.md',
    # 数据目录
    'unifi_scraper',
    # 运行时文件
    'checkpoint.pkl',
]

# 需要保留的unifi_scraper目录下的文件
KEEP_SCRAPER_FILES = [
    '__init__.py',
    'models.py',
    'storage.py',
    'graphql_scraper.py',
    'utils.py',
]

# 需要删除的目录
DELETE_DIRS = [
    '.scrapy',
    'crawls',
    'unifi_scrapy',
    '__pycache__',
    'unifi_scraper/__pycache__',
]

def cleanup_directory(directory):
    """清理目录，删除不需要的文件"""
    try:
        # 过滤需要保留的文件
        keep_paths = [os.path.join(os.getcwd(), f) for f in KEEP_FILES]
        keep_paths.append(os.path.join(os.getcwd(), 'cleanup.py'))  # 暂时保留清理脚本本身
        
        # 删除根目录中不需要的文件
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path) and item_path not in keep_paths:
                os.remove(item_path)
                logger.info(f"已删除文件: {item}")
        
        # 删除指定的目录
        for dir_name in DELETE_DIRS:
            dir_path = os.path.join(directory, dir_name)
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                shutil.rmtree(dir_path)
                logger.info(f"已删除目录: {dir_name}")
        
        # 清理unifi_scraper目录
        scraper_dir = os.path.join(directory, 'unifi_scraper')
        if os.path.exists(scraper_dir) and os.path.isdir(scraper_dir):
            for item in os.listdir(scraper_dir):
                if item not in KEEP_SCRAPER_FILES:
                    item_path = os.path.join(scraper_dir, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                        logger.info(f"已删除文件: unifi_scraper/{item}")
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        logger.info(f"已删除目录: unifi_scraper/{item}")
                        
        logger.info("项目清理完成!")
        
    except Exception as e:
        logger.error(f"清理过程中出错: {e}")

if __name__ == "__main__":
    logger.info("开始清理项目...")
    cleanup_directory(os.getcwd()) 