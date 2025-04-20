"""
数据模型定义
"""
from datetime import datetime
from typing import Dict, Any, Optional
import json


class UnifiRelease:
    """Ubiquiti产品发布模型"""
    
    def __init__(self):
        self.product_name: str = ""
        self.version: str = ""
        self.release_date: str = ""
        self.release_id: str = ""
        self.download_url: str = ""
        self.release_notes: str = ""
        self.firmware_type: str = "Unknown"
        self.is_beta: bool = False
        self.created_at: datetime = datetime.now()
        # 新增字段
        self.stage: str = ""  # 发布阶段：GA, RC, BETA等
        self.slug: str = ""   # 发布标识
        self.tags: str = "[]" # 标签，JSON格式
        self.download_links: str = "[]" # 所有下载链接，JSON格式
        self.last_updated: datetime = datetime.now() # 最后更新时间
    
    def set_data(self, data: Dict[str, Any]) -> 'UnifiRelease':
        """从字典设置数据"""
        self.product_name = data.get('product_name', '')
        self.version = data.get('version', '')
        self.release_date = data.get('release_date', '')
        self.release_id = data.get('release_id', '')
        self.download_url = data.get('download_url', '')
        self.release_notes = data.get('release_notes', '')
        self.firmware_type = data.get('firmware_type', 'Unknown')
        self.is_beta = data.get('is_beta', False)
        
        # 设置新字段
        self.stage = data.get('stage', '')
        self.slug = data.get('slug', '')
        self.tags = data.get('tags', '[]')
        self.download_links = data.get('download_links', '[]')
        
        # 处理日期时间字段
        if 'created_at' in data:
            if isinstance(data['created_at'], str):
                # 如果是字符串，尝试解析为datetime
                try:
                    self.created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    self.created_at = datetime.now()
            else:
                self.created_at = data['created_at']
        
        if 'last_updated' in data:
            if isinstance(data['last_updated'], str):
                try:
                    self.last_updated = datetime.fromisoformat(data['last_updated'].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    self.last_updated = datetime.now()
            else:
                self.last_updated = data['last_updated']
        else:
            self.last_updated = datetime.now()
            
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'product_name': self.product_name,
            'version': self.version,
            'release_date': self.release_date,
            'release_id': self.release_id,
            'download_url': self.download_url,
            'release_notes': self.release_notes,
            'firmware_type': self.firmware_type,
            'is_beta': self.is_beta,
            'created_at': self.created_at,
            'stage': self.stage,
            'slug': self.slug,
            'tags': self.tags,
            'download_links': self.download_links,
            'last_updated': self.last_updated
        }
    
    def __str__(self) -> str:
        return f"{self.product_name} {self.version} ({self.stage}) - {self.release_date}"
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'UnifiRelease':
        """从字典创建实例"""
        instance = UnifiRelease()
        return instance.set_data(data) 