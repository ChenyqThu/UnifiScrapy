"""
GraphQL API爬虫模块
基于GraphQL API重构的爬虫实现，用于获取Ubiquiti产品发布信息
"""
import os
import time
import json
import logging
import pickle
import requests
import urllib3
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from .models import UnifiRelease
from .storage import MongoStorage


# 如果设置了跳过SSL验证，则禁用警告
if os.getenv('SSL_VERIFY', 'True').lower() == 'false':
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class GraphQLScraper:
    """
    GraphQL API爬虫类
    使用GraphQL API获取Ubiquiti产品发布信息
    """
    
    def __init__(self, checkpoint_file: str = 'checkpoint.pkl'):
        """
        初始化爬虫
        
        Args:
            checkpoint_file: 检查点文件路径
        """
        self.api_url = "https://community.svc.ui.com/"
        self.checkpoint_file = checkpoint_file
        self.storage = MongoStorage()
        self.logger = logging.getLogger(__name__)
        
        # 已处理的发布ID
        self.processed_ids = set()
        
        # SSL验证设置
        self.verify_ssl = os.getenv('SSL_VERIFY', 'True').lower() != 'false'
        
        # 加载断点数据
        self.load_checkpoint()
    
    def setup(self) -> bool:
        """
        设置爬虫，连接到数据库
        
        Returns:
            bool: 设置是否成功
        """
        return self.storage.connect()
    
    def load_checkpoint(self) -> None:
        """加载检查点数据"""
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'rb') as f:
                    data = pickle.load(f)
                    if isinstance(data, dict) and 'processed_ids' in data:
                        self.processed_ids = data['processed_ids']
                    else:
                        # 如果加载的数据不是预期的格式，则使用默认值
                        self.logger.warning(f"检查点文件格式不正确，使用默认值")
                        self.processed_ids = set()
                self.logger.info(f"已加载检查点数据，已处理ID数量: {len(self.processed_ids)}")
            else:
                self.logger.info("检查点文件不存在，将创建新的检查点")
        except Exception as e:
            self.logger.error(f"加载检查点数据失败: {e}")
            self.processed_ids = set()
    
    def save_checkpoint(self) -> None:
        """保存检查点数据"""
        try:
            # 创建备份
            if os.path.exists(self.checkpoint_file):
                backup_file = f"{self.checkpoint_file}.bak"
                with open(backup_file, 'wb') as f:
                    pickle.dump({
                        'processed_ids': self.processed_ids,
                        'timestamp': datetime.now()
                    }, f)
            
            # 保存当前数据
            with open(self.checkpoint_file, 'wb') as f:
                pickle.dump({
                    'processed_ids': self.processed_ids,
                    'timestamp': datetime.now()
                }, f)
            self.logger.info(f"已保存检查点数据，已处理ID数量: {len(self.processed_ids)}")
        except Exception as e:
            self.logger.error(f"保存检查点数据失败: {e}")
    
    def get_headers(self) -> Dict[str, str]:
        """
        获取请求头
        
        Returns:
            Dict[str, str]: HTTP请求头
        """
        return {
            'authority': 'community.svc.ui.com',
            'method': 'POST',
            'path': '/',
            'scheme': 'https',
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'dnt': '1',
            'origin': 'https://community.ui.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://community.ui.com/',
            'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'x-frontend-version': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        }
    
    def fetch_all_releases(self, limit: int = 0, batch_size: int = 50) -> List[Dict[str, Any]]:
        """
        获取所有产品发布信息
        
        Args:
            limit: 最大获取数量，0表示不限制
            batch_size: 每批次获取的数量
        
        Returns:
            List[Dict[str, Any]]: 产品发布信息列表
        """
        self.logger.info(f"开始获取产品发布列表，批次大小: {batch_size}，最大数量: {'不限制' if limit == 0 else limit}")
        
        all_items = []
        offset = 0
        has_more = True
        
        while has_more:
            # 如果设置了limit且已达到，则停止
            if limit > 0 and len(all_items) >= limit:
                self.logger.info(f"已达到设定的获取上限: {limit}")
                break
            
            # 计算当前批次应获取的数量
            current_batch_size = batch_size
            if limit > 0:
                remaining = limit - len(all_items)
                if remaining < batch_size:
                    current_batch_size = remaining
            
            # 获取产品发布列表
            items, success = self._fetch_releases_batch(offset, current_batch_size)
            
            if not success:
                self.logger.error("获取产品发布列表失败")
                break
            
            # 添加到结果中
            all_items.extend(items)
            
            self.logger.info(f"已获取 {len(items)} 个发布项，总计: {len(all_items)}，offset: {offset}")
            
            # 如果返回的数量小于请求的数量，表示没有更多数据
            if len(items) < current_batch_size:
                has_more = False
                self.logger.info("已获取所有发布项")
            
            # 更新offset
            offset += len(items)
            
            # 每获取100个项目保存一次检查点
            if len(all_items) % 100 == 0:
                self.save_checkpoint()
        
        return all_items
    
    def _fetch_releases_batch(self, offset: int, limit: int) -> Tuple[List[Dict[str, Any]], bool]:
        """
        获取一批产品发布列表
        
        Args:
            offset: 偏移量
            limit: 获取数量
        
        Returns:
            Tuple[List[Dict[str, Any]], bool]: (产品发布列表, 是否成功)
        """
        # 构建GraphQL查询
        query = """
        query {
          releases(limit: %d, offset: %d) {
            items {
              id
              slug
              title
              version
              stage
              createdAt
              lastActivityAt
              updatedAt
              tags
              type
              stats {
                comments
                views
                __typename
              }
              publishedAs {
                id
                username
                title
                slug
                __typename
              }
              __typename
            }
          }
        }
        """ % (limit, offset)
        
        # 准备请求数据
        payload = {
            "query": query
        }
        
        try:
            # 发送请求
            response = requests.post(
                self.api_url,
                headers=self.get_headers(),
                json=payload,
                verify=self.verify_ssl,
                timeout=30
            )
            
            # 检查状态码
            if response.status_code != 200:
                self.logger.error(f"请求失败，状态码: {response.status_code}")
                return [], False
            
            # 解析响应
            data = response.json()
            
            # 检查是否有错误
            if "errors" in data:
                self.logger.error(f"GraphQL查询出错: {data['errors']}")
                return [], False
            
            # 提取产品发布列表
            items = data.get("data", {}).get("releases", {}).get("items", [])
            
            return items, True
            
        except Exception as e:
            self.logger.error(f"获取产品发布列表失败: {e}")
            return [], False
    
    def get_release_detail(self, release_id: str) -> Optional[Dict[str, Any]]:
        """
        获取产品发布详情
        
        Args:
            release_id: 产品发布ID
        
        Returns:
            Optional[Dict[str, Any]]: 产品发布详情，失败时返回None
        """
        self.logger.info(f"获取产品发布详情: {release_id}")
        
        # 使用完整的GraphQL查询格式
        query = """query GetRelease($id: ID!) {
  release(id: $id) {
    ...Release
    __typename
  }
}

fragment Release on Release {
  ...BasicRelease
  groupId
  content {
    ...Content
    __typename
  }
  newFeatures {
    ...Content
    __typename
  }
  improvements {
    ...Content
    __typename
  }
  bugfixes {
    ...Content
    __typename
  }
  knownIssues {
    ...Content
    __typename
  }
  importantNotes {
    ...Content
    __typename
  }
  instructions {
    ...Content
    __typename
  }
  links {
    url
    title
    checksums {
      md5
      sha256
      __typename
    }
    __typename
  }
  editor {
    ...UserWithStats
    __typename
  }
  status
  __typename
}

fragment BasicRelease on Release {
  id
  slug
  type
  title
  version
  stage
  tags
  betas
  alphas
  isFeatured
  isLocked
  hasUiEngagement
  stats {
    comments
    views
    __typename
  }
  createdAt
  lastActivityAt
  updatedAt
  userStatus {
    ...UserStatus
    lastViewedId
    __typename
  }
  author {
    ...UserWithStats
    __typename
  }
  publishedAs {
    ...User
    __typename
  }
  __typename
}

fragment UserStatus on UserStatus {
  isFollowing
  lastViewedAt
  reported
  vote
  __typename
}

fragment UserWithStats on User {
  ...User
  stats {
    questions
    answers
    solutions
    comments
    stories
    score
    __typename
  }
  __typename
}

fragment User on User {
  id
  username
  title
  slug
  avatar {
    color
    content
    image
    __typename
  }
  isEmployee
  registeredAt
  lastOnlineAt
  groups
  showOfficialBadge
  canBeMentioned
  canViewProfile
  canStartConversationWith
  __typename
}

fragment Content on Content {
  type
  ... on TextContent {
    content
    __typename
  }
  ... on ImagesContent {
    grid {
      images {
        src
        caption
        __typename
      }
      __typename
    }
    __typename
  }
  ... on VideoContent {
    src
    __typename
  }
  ... on AttachmentsContent {
    files {
      filename
      url
      isPublic
      __typename
    }
    __typename
  }
  __typename
}"""
        
        # 准备请求数据
        payload = {
            "operationName": "GetRelease",
            "variables": {"id": release_id},
            "query": query
        }
        
        try:
            # 发送请求
            response = requests.post(
                self.api_url,
                headers=self.get_headers(),
                json=payload,
                verify=self.verify_ssl,
                timeout=30
            )
            
            # 检查状态码
            if response.status_code != 200:
                self.logger.error(f"请求失败，状态码: {response.status_code}")
                return None
            
            # 解析响应
            data = response.json()
            
            # 检查是否有错误
            if "errors" in data:
                self.logger.error(f"GraphQL查询出错: {data['errors']}")
                return None
            
            # 提取产品发布详情
            release = data.get("data", {}).get("release")
            
            if not release:
                self.logger.error(f"未找到产品发布详情: {release_id}")
                return None
            
            return release
            
        except Exception as e:
            self.logger.error(f"获取产品发布详情失败: {e}")
            return None
    
    def extract_release_info(self, item: Dict[str, Any]) -> UnifiRelease:
        """
        从API返回的数据中提取产品发布信息
        
        Args:
            item: API返回的单个产品发布数据
        
        Returns:
            UnifiRelease: 产品发布模型
        """
        release = UnifiRelease()
        
        # 填充基本信息
        release.product_name = item.get("title", "")
        release.version = item.get("version", "")
        release.release_date = item.get("createdAt", "")
        release.release_id = item.get("id", "")
        release.download_url = f"https://community.ui.com/releases/{item.get('slug', '')}"
        release.is_beta = item.get("stage", "") == "BETA"
        release.firmware_type = item.get("type", "Unknown")
        release.stage = item.get("stage", "")
        release.slug = item.get("slug", "")
        
        # 将标签作为JSON存储
        release.tags = json.dumps(item.get("tags", []))
        
        return release
    
    def process_release_detail(self, release: UnifiRelease, detail: Dict[str, Any]) -> None:
        """
        处理产品发布详情
        
        Args:
            release: 产品发布模型
            detail: 产品发布详情数据
        """
        # 提取发布说明
        release_notes = []
        
        # 处理改进内容
        improvements = detail.get("improvements", [])
        if improvements:
            for imp in improvements:
                if imp.get("type") == "TEXT" and "content" in imp:
                    release_notes.append("== 改进内容 ==")
                    release_notes.append(imp.get("content", ""))
        
        # 处理Bug修复
        bugfixes = detail.get("bugfixes", [])
        if bugfixes:
            for bug in bugfixes:
                if bug.get("type") == "TEXT" and "content" in bug:
                    release_notes.append("== Bug修复 ==")
                    release_notes.append(bug.get("content", ""))
        
        # 处理已知问题
        known_issues = detail.get("knownIssues", [])
        if known_issues:
            for issue in known_issues:
                if issue.get("type") == "TEXT" and "content" in issue:
                    release_notes.append("== 已知问题 ==")
                    release_notes.append(issue.get("content", ""))
        
        # 处理重要说明
        important_notes = detail.get("importantNotes", [])
        if important_notes:
            for note in important_notes:
                if note.get("type") == "TEXT" and "content" in note:
                    release_notes.append("== 重要说明 ==")
                    release_notes.append(note.get("content", ""))
        
        # 设置发布说明
        release.release_notes = "\n\n".join(release_notes)
        
        # 提取下载链接
        links = detail.get("links", [])
        if links:
            # 如果有多个下载链接，使用第一个
            download_url = links[0].get("url", "")
            if download_url:
                release.download_url = download_url
            
            # 保存所有下载链接
            download_links = []
            for link in links:
                title = link.get("title", "")
                url = link.get("url", "")
                if title and url:
                    download_links.append(f"{title}: {url}")
            
            release.download_links = json.dumps(download_links)
    
    def process_releases(self, limit: int = 0) -> int:
        """
        处理产品发布信息
        
        Args:
            limit: 最大处理数量，0表示不限制
        
        Returns:
            int: 处理的数量
        """
        self.logger.info(f"开始处理产品发布信息，最大数量: {'不限制' if limit == 0 else limit}")
        
        # 获取产品发布列表
        releases = self.fetch_all_releases(limit=limit)
        
        if not releases:
            self.logger.error("未获取到产品发布信息")
            return 0
        
        self.logger.info(f"获取到 {len(releases)} 个产品发布信息")
        
        # 处理每个产品发布
        processed_count = 0
        for item in releases:
            release_id = item.get("id")
            
            # 跳过已处理的发布
            if release_id in self.processed_ids:
                self.logger.info(f"跳过已处理的发布: {item.get('title')} {item.get('version')}")
                continue
            
            try:
                # 提取基本信息
                release = self.extract_release_info(item)
                
                # 获取详情
                detail = self.get_release_detail(release_id)
                
                if detail is not None:
                    # 处理详情
                    self.process_release_detail(release, detail)
                
                # 保存到数据库
                success = self.storage.save_release(release)
                
                if success:
                    # 标记为已处理
                    self.processed_ids.add(release_id)
                    processed_count += 1
                    
                    self.logger.info(f"已处理: {release.product_name} {release.version}")
                    
                    # 每处理10个保存一次检查点
                    if processed_count % 10 == 0:
                        self.save_checkpoint()
                else:
                    self.logger.error(f"保存失败: {release.product_name} {release.version}")
                    
            except Exception as e:
                self.logger.error(f"处理产品发布信息失败: {release_id}, 错误: {e}")
                # 继续处理下一个，不中断整个过程
                continue
        
        # 保存检查点
        self.save_checkpoint()
        
        self.logger.info(f"处理完成，共处理 {processed_count} 个产品发布信息")
        
        return processed_count
    
    def scrape(self, limit: int = 0) -> bool:
        """
        执行爬取
        
        Args:
            limit: 最大处理数量，0表示不限制
        
        Returns:
            bool: 是否成功
        """
        try:
            # 处理产品发布信息
            processed_count = self.process_releases(limit=limit)
            
            # 关闭数据库连接
            self.storage.close()
            
            return processed_count > 0
            
        except Exception as e:
            self.logger.error(f"爬取失败: {e}")
            # 尝试保存检查点
            self.save_checkpoint()
            return False 