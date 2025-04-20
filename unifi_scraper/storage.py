"""
数据存储模块，负责管理MongoDB连接和数据存储
"""
import os
import logging
from typing import Dict, Any, Optional
import pymongo
from datetime import datetime

from .models import UnifiRelease


class MongoStorage:
    """MongoDB存储类"""
    
    def __init__(self):
        """初始化MongoDB连接"""
        self.mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        self.mongo_db = os.getenv('MONGO_DATABASE', 'unifi_releases')
        self.collection_name = 'unifi_releases'
        self.client = None
        self.db = None
        self.logger = logging.getLogger(__name__)
    
    def connect(self):
        """连接到MongoDB"""
        try:
            self.client = pymongo.MongoClient(self.mongo_uri)
            self.db = self.client[self.mongo_db]
            self.logger.info(f"已连接到MongoDB: {self.mongo_uri}")
            return True
        except Exception as e:
            self.logger.error(f"MongoDB连接失败: {e}")
            return False
    
    def close(self):
        """关闭MongoDB连接"""
        if self.client is not None:
            self.client.close()
            self.logger.info("已关闭MongoDB连接")
    
    def save_release(self, release: UnifiRelease) -> bool:
        """保存或更新产品发布信息"""
        if self.db is None:
            self.logger.error("未连接到MongoDB，无法保存数据")
            return False
        
        release_dict = release.to_dict()
        release_id = release_dict.get('release_id')
        
        try:
            # 检查是否已存在该版本
            existing = self.db[self.collection_name].find_one({'release_id': release_id})
            
            if existing is not None:
                # 如果已存在记录，则更新
                result = self.db[self.collection_name].update_one(
                    {'release_id': release_id},
                    {'$set': release_dict}
                )
                self.logger.info(f"更新已存在项目: {release.product_name} {release.version}")
                return result.modified_count > 0
            else:
                # 如果不存在，则插入新记录
                result = self.db[self.collection_name].insert_one(release_dict)
                self.logger.info(f"添加新项目: {release.product_name} {release.version}")
                return result.acknowledged
            
        except Exception as e:
            self.logger.error(f"保存数据失败: {e}")
            return False
    
    def get_release(self, release_id: str) -> Optional[UnifiRelease]:
        """根据ID获取产品发布信息"""
        if self.db is None:
            self.logger.error("未连接到MongoDB，无法获取数据")
            return None
        
        try:
            result = self.db[self.collection_name].find_one({'release_id': release_id})
            if result is not None:
                return UnifiRelease.from_dict(result)
            return None
        except Exception as e:
            self.logger.error(f"获取数据失败: {e}")
            return None
    
    def get_all_releases(self, limit: int = 100) -> list:
        """获取所有产品发布信息"""
        if self.db is None:
            self.logger.error("未连接到MongoDB，无法获取数据")
            return []
        
        try:
            results = list(self.db[self.collection_name]
                           .find()
                           .sort('created_at', pymongo.DESCENDING)
                           .limit(limit))
            return [UnifiRelease.from_dict(item) for item in results]
        except Exception as e:
            self.logger.error(f"获取数据失败: {e}")
            return [] 