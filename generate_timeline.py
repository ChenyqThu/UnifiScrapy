#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
生成Unifi产品发布时间轴的交互式页面
"""

import os
import json
import logging
from datetime import datetime
from collections import defaultdict
from pymongo import MongoClient
from jinja2 import Template
from dotenv import load_dotenv
import re
from jinja2 import Environment, FileSystemLoader

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 产品线映射关系，根据标签和产品名称进行分类
PRODUCT_LINE_MAPPING = {
    # ===== Platform 平台 =====
    'unifi-os': ['unifi os', 'unifi console', 'dream os', 'udm os', 'dream machine os', 'unifi os console', 'uisp os'],
    'unifi-network-app': ['unifi network application', 'network controller', 'network management','uap controller', 'unifi sdn'],
    'unifi-protect-app': ['unifi protect application', 'unifi protect server', 'protect controller', 'video controller'],
    'unifi-access-app': ['access application', 'access app', 'access controller', 'door controller', 'identity controller'],
    'unifi-talk-app': ['talk application', 'talk app', 'talk controller', 'voip controller', 'voice controller', 'phone controller'],
    'unifi-led-app': ['led application', 'led controller', 'led app', 'lighting controller'],
    'unifi-connect-app': ['connect application', 'connect app', 'connect controller', 'sense controller', 'iot controller'],
    'unifi-drive-app': ['drive application', 'drive app', 'storage controller', 'backup controller'],
    'unifi-platform-other': ['security advisory', 'security bulletin', 'advisory bulletin', 'platform advisory'],
    
    # ===== 设备产品线 =====
    'unifi-switch': ['switch', 'campus', 'aggregation', 'usw', 'flex switch', 'enterprise switch', 'poe switch', 'switch firmware', 'usw firmware'],
    'unifi-gateway': ['gateway', 'usg', 'security gateway', 'routing', 'cable internet', 'mobile routers', 'mobile router', 'dream router', 'dream machine', 'udr', 'udm', 'lte', 'unifi lte', 'udm firmware', 'dream firmware', 'gateway firmware', 'usg firmware'],
    'unifi-ap': ['access point', 'uap', 'wifi', 'wireless', 'u6', 'nanohd', 'flexhd', 'ac-lite', 'ac-pro', 'access point firmware', 'uap firmware', 'ap firmware','bridge'],
    'unifi-cloud': ['cloud key', 'uck', 'cloud gateway', 'console', 'ck', 'cloudkey firmware'],
    'unifi-protect': ['protect', 'camera', 'g4', 'g3', 'doorbell', 'viewport', 'nvr', 'unvr', 'video', 'camera firmware', 'g4 firmware', 'g3 firmware', 'doorbell firmware', 'viewport firmware'],
    'unifi-access': ['access', 'door', 'smart lock', 'hub', 'identity', 'access hub firmware', 'door firmware', 'smart lock firmware'],
    'unifi-talk': ['talk', 'phone', 'voip', 'phone firmware', 'talk hardware firmware'],
    'unifi-led': ['led', 'light', 'lighting', 'led hardware firmware', 'light firmware'],
    'unifi-connect': ['connect', 'sense', 'sensor', 'uid', 'sense firmware', 'sensor firmware'],
    
    # ===== APP & Tools 应用与工具 =====
    'protect-app': ['protect app', 'protect ios', 'protect android','unifi play', 'unifi play ios','play android', 'play ios', 'play app'],
    'access-app': ['access app', 'access ios', 'access android'],
    'connect-app': ['connect app', 'connect ios', 'connect android'],
    'verify-app': ['verify app', 'verify ios', 'verify android'],
    'portal-app': ['portal app', 'portal ios', 'portal android'],
    'identity-endpoint': ['identity endpoint', 'identity endpoint ios', 'identity endpoint android'],
    'wifiman-app': ['wifiman app', 'wifiman ios', 'wifiman android', 'WiFiman Desktop', 'wifiman for desktop'],
    'unifi-app': ['unifi app', 'unifi ios', 'unifi android'],
    'design-center': ['unifi design center', 'unifi innerspace'],
    
    # ===== 其他产品线 =====
    'airmax': ['airmax', 'nanostation', 'litebeam', 'powerbeam', 'rocket', 'prism', 'aircube', '60ghz'],
    'airfiber': ['airfiber', 'ltu', 'gigabeam'],
    'edgemax': ['edgerouter', 'edgeswitch', 'edgepoint', 'edgemax'],
    'amplifi': ['amplifi', 'alien', 'mesh', 'poweramp'],
    'ufiber': ['ufiber', 'fiber'],
    'uisp': ['uisp', 'unms', 'isp design', 'isp-app', 'uisp design center','isp design center'],
    
    # 未分类的 Unifi 产品
    'unifi-other': ['unifi']  # 放在最后作为兜底分类
}

# 产品线分组（按照高级分类组织）
PRODUCT_LINE_GROUPS = {
    'Platform': [
        'unifi-os', 'unifi-network-app', 'unifi-protect-app', 'unifi-access-app', 
        'unifi-talk-app', 'unifi-led-app', 'unifi-connect-app', 'unifi-drive-app', 'unifi-platform-other'
    ],
    'UniFi Devices': [
        'unifi-switch', 'unifi-gateway', 'unifi-ap', 'unifi-cloud', 'unifi-protect',
        'unifi-access', 'unifi-talk', 'unifi-led', 'unifi-connect'
    ],
    'APP & Tools': [
        'unifi-app', 'protect-app', 'wifiman-app', 'design-center', 'access-app', 'connect-app', 'verify-app', 'portal-app', 'identity-endpoint'
    ],
    'Other Products': [
        'airmax', 'airfiber', 'edgemax', 'amplifi', 'ufiber', 'uisp', 'unifi-other'
    ]
}

# 产品线显示顺序
PRODUCT_LINE_ORDER = [
    # Platform
    'unifi-os', 'unifi-network-app', 'unifi-protect-app', 'unifi-access-app', 
    'unifi-talk-app', 'unifi-led-app', 'unifi-connect-app', 'unifi-drive-app', 'unifi-platform-other',
    # UniFi Devices
    'unifi-switch', 'unifi-gateway', 'unifi-ap', 'unifi-cloud', 'unifi-protect',
    'unifi-access', 'unifi-talk', 'unifi-led', 'unifi-connect',
    # APP & Tools
    'unifi-app', 'protect-app', 'wifiman-app', 'design-center', 'access-app', 'connect-app', 'verify-app', 'portal-app', 'identity-endpoint'
    # Other Products
    'airmax', 'airfiber', 'edgemax', 'amplifi', 'ufiber', 'uisp', 'unifi-other'
]

# 产品线显示名称
PRODUCT_LINE_LABELS = {
    # Platform
    'unifi-os': 'UniFi OS/Dream OS',
    'unifi-network-app': 'UniFi Network Application',
    'unifi-protect-app': 'UniFi Protect Application',
    'unifi-access-app': 'UniFi Access Application',
    'unifi-talk-app': 'UniFi Talk Application',
    'unifi-led-app': 'UniFi LED Application',
    'unifi-connect-app': 'UniFi Connect Application',
    'unifi-drive-app': 'UniFi Drive Application',
    'unifi-platform-other': 'Security & Platform Bulletins',
    # UniFi Devices
    'unifi-switch': 'UniFi Switch',
    'unifi-gateway': 'UniFi Gateway',
    'unifi-ap': 'UniFi AP',
    'unifi-cloud': 'UniFi Cloud Key',
    'unifi-protect': 'UniFi Protect Devices',
    'unifi-access': 'UniFi Access Devices',
    'unifi-talk': 'UniFi Talk Devices',
    'unifi-led': 'UniFi LED Devices',
    'unifi-connect': 'UniFi Connect Devices',
    # APP & Tools
    'unifi-app': 'UniFi APP',
    'protect-app': 'Protect APP',
    'wifiman-app': 'WiFiMan APP',
    'design-center': 'Design Center',
    'access-app': 'Access APP',
    'connect-app': 'Connect APP',
    'verify-app': 'Verify APP',
    'portal-app': 'Portal APP',
    'identity-endpoint': 'Identity Endpoint',
    # Other Products
    'airmax': 'airMAX',
    'airfiber': 'airFiber',
    'edgemax': 'EdgeMAX',
    'amplifi': 'AmpliFi',
    'ufiber': 'UFiber',
    'uisp': 'UISP/UNMS',
    'unifi-other': '其他 UniFi 产品'
}

# 版本类型展示名称
VERSION_TYPE_LABELS = {
    # 常规版本类型
    'GA': '正式版',
    'RC': '候选版',
    'Beta': '测试版',
    'Alpha': '内测版',
    'other': '其他版本',
    
    # APP平台类型
    'iOS': 'iOS版',
    'Android': 'Android版',
    'Desktop': '桌面版',
    'Other': '其他平台'
}

class ImprovedTimelineGenerator:
    """增强版时间轴生成器"""
    
    def __init__(self):
        """初始化连接和设置"""
        self.mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        self.mongo_db = os.getenv('MONGO_DATABASE', 'unifi_releases')
        self.collection_name = 'unifi_releases'
        self.client = None
        self.db = None
        self.output_dir = 'timeline_output'
        self.html_file = os.path.join(self.output_dir, 'index.html')
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
    
    def connect_db(self):
        """连接到MongoDB"""
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.mongo_db]
            logger.info(f"已连接到MongoDB: {self.mongo_uri}")
            return True
        except Exception as e:
            logger.error(f"MongoDB连接失败: {e}")
            return False
    
    def close_db(self):
        """关闭MongoDB连接"""
        if self.client:
            self.client.close()
            logger.info("已关闭MongoDB连接")
    
    def get_all_releases(self):
        """获取所有产品发布数据"""
        if self.db is None:
            logger.error("未连接到数据库，无法获取数据")
            return []
        
        try:
            # 获取所有数据并按发布日期排序
            releases = list(self.db[self.collection_name].find({}).sort('release_date', -1))
            logger.info(f"已获取 {len(releases)} 条产品发布数据")
            return releases
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            return []
    
    def determine_product_line(self, release):
        """确定产品所属的产品线"""
        tags_str = release.get('tags', '[]')
        product_name = release.get('product_name', '').lower()
        firmware_type = release.get('firmware_type', '').lower()
        version = release.get('version', '').lower()
        
        try:
            # 解析标签
            tags = json.loads(tags_str) if isinstance(tags_str, str) else tags_str
            if not isinstance(tags, list):
                tags = []
            
            # 获取标签文本和产品名称文本
            tags_text = ' '.join([str(tag).lower() for tag in tags])
            name_text = product_name + ' ' + firmware_type
            all_text = name_text + ' ' + tags_text
            
            # 调试日志
            logger.debug(f"处理产品: {product_name}, 标签: {tags}")
            
            # 特殊处理：识别旧版本的UniFi控制器（5.x.x系列）
            if ('unifi' in product_name.lower() and 
                re.search(r'\b5\.\d+\.\d+\b', version) and 
                ('stable' in all_text or 'controller' in all_text)):
                return 'unifi-network-app'
            
            # 先检查是不是UniFi OS - 这是最高优先级
            if ('unifi os' in all_text or 'dream os' in all_text or 'udm os' in all_text or 'console os' in all_text) and not 'ios' in all_text:
                return 'unifi-os'
            
            # 检查是否为移动应用 (APP) - 高优先级
            # 移动应用识别
            if 'ios' in all_text or 'iphone' in all_text or 'ipad' in all_text or 'android' in all_text or 'mobile app' in all_text:
                if 'play' in all_text or 'protect' in all_text:
                    return 'protect-app'
                elif 'wifiman' in all_text:
                    return 'wifiman-app'
                elif 'access' in all_text:
                    return 'access-app'
                elif 'connect' in all_text:
                    return 'connect-app'
                elif 'verify' in all_text:
                    return 'verify-app'
                elif 'portal' in all_text:
                    return 'portal-app'
                elif 'identity' in all_text:
                    return 'identity-endpoint'
                elif 'unifi' in all_text:
                    return 'unifi-app'

            # 直接从标签中获取产品线（精确匹配）
            primary_tag = None
            for tag in tags:
                tag_lower = str(tag).lower()
                if (tag_lower.startswith('unifi-') or tag_lower in ['edgemax', 'airmax', 'airfiber', 'amplifi', 'ufiber', 'uisp', 'design-center']):
                    primary_tag = tag_lower
                    break
            
            # 特定产品线的标签映射
            if primary_tag:
                # 处理标签直接匹配的情况
                if primary_tag == 'unifi-gateway' or (primary_tag == 'unifi-gateway-cloudkey' and 'gateway' in all_text):
                    # 如果是UniFi OS相关，优先归类为OS
                    if ('unifi os' in all_text or 'dream os' in all_text or 'udm os' in all_text) and not 'ios' in all_text:
                        return 'unifi-os'
                    return 'unifi-gateway'
                elif primary_tag == 'unifi-gateway-cloudkey' and not 'gateway' in all_text:
                    return 'unifi-cloud'
                elif primary_tag in ['unifi-cloud', 'unifi-cloudkey']:
                    return 'unifi-cloud'
                elif primary_tag in ['unifi-switch', 'unifi-switching', 'unifi-routing-switching']:
                    return 'unifi-switch'
                elif primary_tag == 'unifi-wireless':
                    if 'lte' in all_text:
                        return 'unifi-gateway'  # LTE产品归到Gateway
                    else:
                        return 'unifi-ap'
                elif primary_tag in ['edgemax', 'airmax', 'airfiber', 'amplifi', 'ufiber', 'uisp', 'unms', 'design-center']:
                    if primary_tag == 'unms':
                        return 'uisp'
                    return primary_tag
            
            # 使用PRODUCT_LINE_MAPPING进行精确匹配
            # 1. 将all_text拆分为单词列表，用于精确匹配
            words = re.findall(r'\b\w+\b', all_text.lower())
            text_as_phrase = ' '.join(words)
            
            # 检查是否包含UniFi OS关键词（最高优先级）
            for keyword in PRODUCT_LINE_MAPPING['unifi-os']:
                # 将关键词转换为单词边界正则表达式模式
                keyword_pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                # 检查是否完整匹配且非iOS
                if re.search(keyword_pattern, text_as_phrase) and not 'ios' in all_text:
                    return 'unifi-os'
            
            # 2. 对每个产品线的关键词列表进行匹配
            for product_line, keywords in PRODUCT_LINE_MAPPING.items():
                # 跳过已检查过的UniFi OS
                if product_line == 'unifi-os':
                    continue
                
                for keyword in keywords:
                    # 将关键词转换为单词边界正则表达式模式
                    keyword_pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                    
                    # 检查关键词是否完整匹配（作为独立短语）
                    if re.search(keyword_pattern, text_as_phrase):
                        # 特殊情况处理：避免iOS被识别为OS
                        if product_line == 'unifi-os' and 'ios' in all_text and not keyword.lower() in all_text:
                            continue
                        
                        return product_line
            
            # 产品线标识检查
            if 'unifi' in all_text:
                # Play相关的产品归类到protect-app
                if 'play' in all_text:
                    return 'protect-app'
                
                # 检查是否是旧版本UniFi控制器
                if re.search(r'(unifi.*controller|controller.*unifi|network.*controller)', all_text) or re.search(r'\bunifi\s+\d+\.\d+\.\d+', all_text):
                    return 'unifi-network-app'
                
                # 如果包含UniFi标识，但无法精确匹配，归为其他UniFi产品
                return 'unifi-other'
            elif 'edgemax' in all_text or 'edgerouter' in all_text or 'edgeswitch' in all_text:
                return 'edgemax'
            elif 'airmax' in all_text:
                return 'airmax'
            elif 'airfiber' in all_text or 'ltu' in all_text:
                return 'airfiber'
            elif 'amplifi' in all_text:
                return 'amplifi'
            elif 'ufiber' in all_text:
                return 'ufiber'
            elif 'uisp' in all_text or 'unms' in all_text:
                return 'uisp'
            
            # 完全无法识别的产品
            return 'other'
        except Exception as e:
            logger.warning(f"解析产品线失败: {e}")
            return 'other'
    
    def determine_version_type(self, release):
        """确定版本类型(GA/RC/Beta/Alpha等)或移动应用平台类型"""
        # 获取产品线
        product_line = self.determine_product_line(release)
        
        # 对于APP类产品，返回平台类型而非版本类型
        if product_line in ['unifi-app', 'protect-app', 'wifiman-app', 'access-app', 'connect-app', 'verify-app', 'portal-app', 'identity-endpoint']:
            all_text = (release.get('product_name', '') + ' ' + 
                       release.get('firmware_type', '') + ' ' + 
                       ' '.join(json.loads(release.get('tags', '[]')) if isinstance(release.get('tags', '[]'), str) else release.get('tags', '[]'))).lower()
            
            # 确定平台类型
            if 'ios' in all_text or 'iphone' in all_text or 'ipad' in all_text:
                return 'iOS'
            elif 'android' in all_text:
                return 'Android'
            elif 'desktop' in all_text or 'windows' in all_text or 'mac' in all_text:
                return 'Desktop'
            else:
                return 'Other'  # 默认平台类型
        
        # 非APP产品使用正常的版本类型判断
        # 首先检查stage字段
        stage = release.get('stage', '').lower()
        
        if 'ga' in stage or 'general' in stage:
            return 'GA'
        elif 'rc' in stage or 'release candidate' in stage:
            return 'RC'
        elif 'beta' in stage:
            return 'Beta'
        elif 'alpha' in stage:
            return 'Alpha'
        
        # 如果stage字段没有明确指示，从版本号中识别
        version = release.get('version', '').lower()
        
        if 'rc' in version:
            return 'RC'
        elif 'beta' in version or 'b' in version:
            return 'Beta'
        elif 'alpha' in version or 'a' in version:
            return 'Alpha'
        elif release.get('is_beta', False):
            return 'Beta'
        
        # 默认为GA
        return 'GA'
    
    def format_date(self, date_str):
        """格式化日期为YYYY-MM-DD格式"""
        try:
            if isinstance(date_str, str):
                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return date_obj.strftime('%Y-%m-%d')
            elif isinstance(date_str, datetime):
                return date_str.strftime('%Y-%m-%d')
        except Exception:
            pass
        
        return str(date_str)
    
    def extract_year(self, date_str):
        """从日期中提取年份"""
        try:
            if isinstance(date_str, str):
                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return date_obj.year
            elif isinstance(date_str, datetime):
                return date_str.year
        except Exception:
            pass
        
        # 如果无法解析日期，尝试直接提取开头的4位数字作为年份
        if isinstance(date_str, str) and len(date_str) >= 4:
            year_str = date_str[:4]
            if year_str.isdigit():
                return int(year_str)
        
        return "未知年份"
    
    def categorize_notes(self, notes_text, categorized_notes):
        """将release notes分类为改进内容、bug修复、已知问题等类别"""
        # 常见的章节标题
        improvement_keywords = ['improvement', 'feature', 'new', 'enhance', '改进', '新功能', '特性', '增强']
        bugfix_keywords = ['bugfix', 'fix', 'issue', 'resolve', '修复', '问题', '解决']
        known_issue_keywords = ['known issue', 'limitation', '已知问题', '限制']
        
        lines = notes_text.split('\n')
        current_category = 'other'  # 默认分类
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 尝试确定当前行属于哪个分类
            lower_line = line.lower()
            
            # 检查是否是章节标题
            if any(keyword in lower_line for keyword in improvement_keywords):
                current_category = 'improvements'
                continue
            elif any(keyword in lower_line for keyword in bugfix_keywords):
                current_category = 'bug_fixes'
                continue
            elif any(keyword in lower_line for keyword in known_issue_keywords):
                current_category = 'known_issues'
                continue
            
            # 如果是列表项（以-、*、•等开头）或短句，则归类
            if line.startswith(('-', '*', '•', '- ', '* ', '• ')) or len(line) < 100:
                categorized_notes[current_category].add(line)
            else:
                # 长文本按句子拆分
                sentences = line.split('. ')
                for sentence in sentences:
                    if sentence:
                        categorized_notes[current_category].add(sentence.strip() + ('.' if not sentence.endswith('.') else ''))
    
    def process_releases(self, releases):
        """处理发布数据，按产品线、版本类型和年份组织，并合并相同版本的产品"""
        # 创建多级嵌套字典结构：产品线 -> 版本类型 -> 年份 -> 发布列表
        organized_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        
        # 统计信息 - 总体统计
        stats = {
            'total_releases': len(releases),
            'product_lines': defaultdict(int),
            'version_types': defaultdict(int),
            'years': defaultdict(int)
        }
        
        # 产品线级别的版本类型统计信息
        product_line_stats = defaultdict(lambda: defaultdict(int))
        
        # 用于合并相同版本的临时数据结构
        merged_releases = {}
        
        for release in releases:
            # 确定产品线、版本类型和年份
            product_line = self.determine_product_line(release)
            version_type = self.determine_version_type(release)
            release_date = release.get('release_date', '')
            year = self.extract_year(release_date)
            version = release.get('version', '未知版本')
            
            # 确定版本号和清理版本显示
            if isinstance(version, str):
                # 只替换下划线为连字符，其他保持原样
                version = version.replace('_', '-')
            
            # 格式化日期
            formatted_date = self.format_date(release_date)
            
            # 处理下载链接
            download_links = []
            links_str = release.get('download_links', '[]')
            try:
                links = json.loads(links_str) if isinstance(links_str, str) else links_str
                if isinstance(links, list):
                    for link in links:
                        if isinstance(link, str) and "http" in link:
                            # 处理可能存在的前缀，如"Express 7: https://..."
                            http_pos = link.find("http")
                            if http_pos > 0:
                                # 提取前缀作为链接名称，URL作为链接地址
                                prefix = link[:http_pos].strip()
                                if prefix.endswith(":"):  # 去除末尾冒号
                                    prefix = prefix[:-1].strip()
                                
                                url = link[http_pos:].strip()
                                download_links.append({
                                    "name": prefix if prefix else "下载",
                                    "url": url
                                })
                            else:
                                download_links.append({
                                    "name": "下载",
                                    "url": link.strip()
                                })
            except Exception as e:
                logger.warning(f"处理下载链接失败: {e}")
                pass
            
            # 清理产品名称，但保持原始格式
            product_name = release.get('product_name', '未知产品')
            if isinstance(product_name, str):
                # 只替换下划线为空格，其他保持原样
                product_name = product_name.replace('_', ' ')
                release['product_name'] = product_name
            
            # 获取原帖链接
            source_url = None
            # 尝试从不同可能的字段获取原帖链接
            for field in ['source_url', 'post_url', 'url', 'thread_url', 'forum_url', 'original_post']:
                if field in release and release[field] and isinstance(release[field], str):
                    temp_url = release[field].strip()
                    # 如果链接以@开头，去除@符号
                    if temp_url.startswith('@'):
                        temp_url = temp_url[1:]
                    # 确保URL包含http
                    if "http" in temp_url:
                        source_url = temp_url
                        break
            
            # 如果所有字段都没有，但存在资源ID，则构建一个默认的社区链接
            if not source_url and release.get('release_id'):
                resource_id = str(release.get('release_id'))
                # 清理产品名称用于URL
                clean_product_name = product_name
                if isinstance(clean_product_name, str):
                    # 只保留英文字母、数字和短横线
                    # 将空格替换为短横线
                    clean_product_name = clean_product_name.replace(' ', '-')
                    # 移除其他特殊字符
                    clean_product_name = re.sub(r'[^a-zA-Z0-9-]', '', clean_product_name)
                    # 确保没有连续的短横线
                    clean_product_name = re.sub(r'-+', '-', clean_product_name)
                
                # 清理版本号用于URL
                clean_version = version
                if isinstance(clean_version, str):
                    # 移除特殊字符，将点替换为连字符
                    clean_version = clean_version.replace('.', '-')
                    clean_version = re.sub(r'[^a-zA-Z0-9-]', '', clean_version)
                
                # 组合产品名和版本号
                url_path = f"{clean_product_name}-{clean_version}"
                source_url = f"https://community.ui.com/releases/{url_path}/{resource_id}"
            
            # 清理发布说明内容，但保留格式
            release_notes = release.get('release_notes', '无发布说明')
            if isinstance(release_notes, str):
                # 只做最小限度的清理，保留原始格式
                # 只替换下划线为空格，保留所有其他格式和换行
                release_notes = release_notes.replace('_', ' ')
            
            # 创建唯一键，用于合并相同产品线、版本类型、年份和版本号的发布
            merge_key = f"{product_line}_{version_type}_{year}_{version}"
            
            # 创建处理后的发布数据
            processed_release = {
                'product_name': product_name,
                'version': version,
                'date': formatted_date,
                'raw_date': release.get('release_date', ''),  # 保存原始日期用于排序
                'year': year,
                'notes': release_notes,
                'version_type': version_type,
                'download_links': download_links,
                'source_urls': [source_url] if source_url else [],  # 只保留source_urls列表
                'product_line': product_line,  # 添加产品线信息便于筛选
                'compatible_devices': [release.get('product_name', '未知产品')],  # 初始兼容设备列表
                'is_merged': False,  # 标记是否为合并版本
                'categorized_notes': defaultdict(set)  # 添加分类字段
            }
            
            # 如果该合并键已存在，合并发布信息
            if merge_key in merged_releases:
                # 添加兼容设备到列表
                if release.get('product_name', '未知产品') not in merged_releases[merge_key]['compatible_devices']:
                    merged_releases[merge_key]['compatible_devices'].append(release.get('product_name', '未知产品'))
                
                # 标记为合并版本
                merged_releases[merge_key]['is_merged'] = True
                
                # 合并原帖链接(如果有)
                if source_url:
                    if not merged_releases[merge_key].get('source_urls'):
                        merged_releases[merge_key]['source_urls'] = []
                    # 检查是否已经存在相同或类似链接（避免重复）
                    url_exists = False
                    for existing_url in merged_releases[merge_key]['source_urls']:
                        # 如果两个URL相似度高（比如只是参数不同），则认为是同一个链接
                        if source_url.split('?')[0] == existing_url.split('?')[0]:
                            url_exists = True
                            break
                    if not url_exists:
                        merged_releases[merge_key]['source_urls'].append(source_url)
                
                # 更新合并版本的产品名称
                device_count = len(merged_releases[merge_key]['compatible_devices'])
                # 根据产品线获取产品线显示名称作为前缀
                product_line_prefix = PRODUCT_LINE_LABELS.get(product_line, "")
                merged_releases[merge_key]['display_title'] = f"{product_line_prefix} 统一固件 {version} (适用于{device_count}个设备)"
                
                # 合并下载链接（如果有不同的链接）
                for link in download_links:
                    if link not in merged_releases[merge_key]['download_links']:
                        merged_releases[merge_key]['download_links'].append(link)
                
                # 合并release notes - 简单拼接而非分类
                new_notes = release.get('release_notes', '').strip()
                product_name = release.get('product_name', '未知产品')
                
                # 清理合并的发布说明，但保留格式
                if isinstance(new_notes, str):
                    # 只做最小限度的清理，保留原始格式
                    new_notes = new_notes.replace('_', ' ')  # 只替换下划线为空格
                
                if new_notes and product_name:
                    # 如果这是第一个添加的notes
                    if not merged_releases[merge_key].get('combined_notes'):
                        merged_releases[merge_key]['combined_notes'] = []
                    
                    # 将当前设备的notes添加到合并列表中
                    merged_releases[merge_key]['combined_notes'].append({
                        'device_name': product_name,
                        'notes': new_notes
                    })
                
                # 不增加统计计数，因为这是已合并的条目
            else:
                # 这是新的合并键，添加到合并数据结构
                processed_release['display_title'] = processed_release['product_name']  # 单个设备使用原始产品名
                
                # 初始化combined_notes
                notes = processed_release.get('notes', '').strip()
                product_name = processed_release.get('product_name', '未知产品')
                if notes and product_name:
                    processed_release['combined_notes'] = [{
                        'device_name': product_name,
                        'notes': notes
                    }]
                else:
                    processed_release['combined_notes'] = []
                
                merged_releases[merge_key] = processed_release
                
                # 更新统计信息
                stats['product_lines'][product_line] += 1
                stats['version_types'][version_type] += 1
                stats['years'][year] += 1
                
                # 更新产品线级别的版本类型统计
                product_line_stats[product_line][version_type] += 1
        
        # 按照产品线、版本类型和年份进行组织
        for merge_key, release in merged_releases.items():
            product_line = release['product_line']
            version_type = release['version_type']
            year = release['year']
            
            # 将发布数据添加到相应的年份列表中
            organized_data[product_line][version_type][year].append(release)
        
        # 对每个年份下的发布按日期降序排序，同一日期的按版本号降序
        for product_line in organized_data:
            for version_type in organized_data[product_line]:
                for year in organized_data[product_line][version_type]:
                    # 先按日期降序，同日期再按版本号降序
                    organized_data[product_line][version_type][year].sort(
                        key=lambda x: (x['raw_date'], self.version_to_sortable(x['version'])), 
                        reverse=True
                    )
        
        return organized_data, stats, product_line_stats
    
    def version_to_sortable(self, version_str):
        """将版本号转换为可排序的格式"""
        try:
            # 移除常见的版本前缀
            version = version_str.lower().replace('v', '').replace('version', '').strip()
            
            # 分割版本号为组件 (例如 1.2.3-rc.4 -> [1, 2, 3, -1, 4])
            components = []
            
            # 处理预发布版本号后缀
            if '-' in version:
                version, suffix = version.split('-', 1)
                # 处理常见的后缀类型
                if 'rc' in suffix:
                    components.append(-1)  # RC版本
                    suffix = suffix.replace('rc', '').replace('.', '').strip()
                    if suffix.isdigit():
                        components.append(int(suffix))
                elif 'beta' in suffix:
                    components.append(-2)  # Beta版本
                    suffix = suffix.replace('beta', '').replace('.', '').strip()
                    if suffix.isdigit():
                        components.append(int(suffix))
                elif 'alpha' in suffix:
                    components.append(-3)  # Alpha版本
                    suffix = suffix.replace('alpha', '').replace('.', '').strip()
                    if suffix.isdigit():
                        components.append(int(suffix))
            
            # 处理主版本号部分
            for part in version.split('.'):
                if part.isdigit():
                    components.append(int(part))
                else:
                    # 非数字部分，按原样添加
                    components.append(part)
            
            return components
        except Exception:
            # 如果解析失败，返回原始字符串
            return version_str
    
    def create_template_files(self):
        """创建HTML模板"""
        # HTML模板
        html_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Unifi产品发布时间轴</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        unifi: {
                            blue: '#0559C9',
                            darkblue: '#044AA9',
                            lightblue: '#2A75E5',
                            gray: '#212121',
                            lightgray: '#F5F5F5'
                        }
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-gray-100 min-h-screen font-sans text-gray-800">
    <div class="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
        <header class="bg-gradient-to-r from-unifi-darkblue to-unifi-blue text-white rounded-xl shadow-lg p-6 mb-8">
            <h1 class="text-3xl font-bold mb-2">Unifi产品发布时间轴</h1>
            <p class="text-unifi-lightgray opacity-90">可视化展示Ubiquiti产品发布历史及版本信息</p>
            <div class="flex flex-wrap items-center mt-4">
                <div class="bg-white/20 rounded-lg py-1 px-3 text-sm mr-4 mb-2">
                    <span class="font-semibold">总发布数:</span> {{ stats.total_releases }}
                </div>
                <div class="bg-white/20 rounded-lg py-1 px-3 text-sm mr-4 mb-2">
                    <span class="font-semibold">产品线:</span> {{ stats.product_lines|length }}
                </div>
                <div class="bg-white/20 rounded-lg py-1 px-3 text-sm mr-4 mb-2">
                    <span class="font-semibold">最新更新:</span> {{ latest_update }}
                </div>
            </div>
        </header>

        <div class="mb-6">
            <div class="bg-white rounded-lg shadow-md p-4">
                <h2 class="text-xl font-semibold mb-3 text-unifi-blue">产品线筛选</h2>
                <div class="mb-4">
                    <button 
                        data-product-line="all" 
                        class="product-line-filter bg-unifi-darkblue text-white px-3 py-1.5 rounded hover:bg-unifi-blue transition duration-200 text-sm font-medium active">
                        全部产品
                        <span class="ml-1 bg-white/30 px-1.5 rounded-full text-xs">{{ stats.total_releases }}</span>
                    </button>
                </div>
                
                {% for group_name, product_lines in product_line_groups.items() %}
                <div class="mb-3">
                    <h3 class="text-md font-medium text-gray-700 mb-2">{{ group_name }}</h3>
                    <div class="flex flex-wrap gap-2 mb-2">
                        {% for product_line in product_lines %}
                            {% if product_line in organized_data %}
                                <button 
                                    data-product-line="{{ product_line }}" 
                                    class="product-line-filter bg-unifi-lightblue text-white px-3 py-1.5 rounded hover:bg-unifi-blue transition duration-200 text-sm font-medium">
                                    {{ product_line_labels[product_line] }}
                                    <span class="ml-1 bg-white/30 px-1.5 rounded-full text-xs">{{ stats.product_lines[product_line] }}</span>
                                </button>
                            {% endif %}
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        {% for product_line in product_line_order %}
            {% if product_line in organized_data %}
                <section id="{{ product_line }}" class="mb-12 product-line-section">
                    <div class="bg-white rounded-xl shadow-md overflow-hidden">
                        <div class="bg-gradient-to-r from-unifi-blue to-unifi-lightblue p-4 text-white">
                            <h2 class="text-2xl font-bold">{{ product_line_labels[product_line] }}</h2>
                            <p class="text-sm opacity-90">共 {{ stats.product_lines[product_line] }} 个版本</p>
                        </div>
                        
                        <!-- 版本类型标签页 -->
                        <div class="px-4 pt-4">
                            <div class="border-b border-gray-200">
                                <nav class="flex flex-wrap -mb-px">
                                    {% if product_line in ['unifi-app', 'protect-app', 'wifiman-app', 'access-app', 'connect-app', 'verify-app', 'portal-app', 'identity-endpoint'] %}
                                        <!-- 针对APP类产品显示平台类型 -->
                                        {% for version_type in ['iOS', 'Android', 'Desktop', 'Other'] %}
                                            {% if version_type in organized_data[product_line] %}
                                                <button 
                                                    class="version-tab mr-6 py-2 px-1 border-b-2 font-medium text-sm focus:outline-none"
                                                    data-product-line="{{ product_line }}" 
                                                    data-version-type="{{ version_type }}">
                                                    {{ version_type_labels[version_type] }}
                                                    <span class="ml-1 bg-gray-100 px-2 py-0.5 rounded-full text-xs version-count">
                                                        {{ product_line_stats[product_line][version_type] }}
                                                    </span>
                                                </button>
                                            {% endif %}
                                        {% endfor %}
                                    {% else %}
                                        <!-- 针对非APP产品显示版本类型 -->
                                        {% for version_type in ['GA', 'RC', 'Beta', 'Alpha'] %}
                                            {% if version_type in organized_data[product_line] %}
                                                <button 
                                                    class="version-tab mr-6 py-2 px-1 border-b-2 font-medium text-sm focus:outline-none"
                                                    data-product-line="{{ product_line }}" 
                                                    data-version-type="{{ version_type }}">
                                                    {{ version_type_labels[version_type] }}
                                                    <span class="ml-1 bg-gray-100 px-2 py-0.5 rounded-full text-xs version-count">
                                                        {{ product_line_stats[product_line][version_type] }}
                                                    </span>
                                                </button>
                                            {% endif %}
                                        {% endfor %}
                                    {% endif %}
                                </nav>
                            </div>
                        </div>
                        
                        <!-- 时间轴内容 -->
                        {% if product_line in ['unifi-app', 'protect-app', 'wifiman-app', 'access-app', 'connect-app', 'verify-app', 'portal-app', 'identity-endpoint'] %}
                            <!-- APP产品按平台类型显示内容 -->
                            {% for version_type in ['iOS', 'Android', 'Desktop', 'Other'] %}
                                {% if version_type in organized_data[product_line] %}
                                    <div class="version-content p-4" 
                                        id="content-{{ product_line }}-{{ version_type }}"
                                        style="display: {% if loop.first %}block{% else %}none{% endif %};">
                                        
                                        <!-- 年份分组 -->
                                        {% for year in organized_data[product_line][version_type]|sort(reverse=true) %}
                                            <div class="mb-6">
                                                <div class="year-header cursor-pointer flex items-center bg-gray-50 p-3 rounded-lg mb-2 hover:bg-gray-100 transition duration-200">
                                                    <svg class="year-arrow w-5 h-5 mr-2 text-unifi-blue transform transition-transform duration-200" viewBox="0 0 20 20" fill="currentColor">
                                                        <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                                                    </svg>
                                                    <h3 class="text-lg font-semibold">{{ year }}</h3>
                                                    <span class="ml-2 bg-unifi-blue text-white px-2 py-0.5 rounded-full text-xs">
                                                        {{ organized_data[product_line][version_type][year]|length }}
                                                    </span>
                                                </div>
                                                
                                                <div class="year-content ml-2">
                                                    <!-- 发布时间轴 -->
                                                    <div class="relative border-l-4 border-unifi-blue pl-8 ml-3">
                                                        {% for release in organized_data[product_line][version_type][year] %}
                                                            <div class="relative mb-8">
                                                                <!-- 时间轴节点 -->
                                                                <div class="absolute -left-11 mt-3.5">
                                                                    <div class="w-5 h-5 rounded-full bg-unifi-blue border-4 border-white shadow"></div>
                                                                </div>
                                                                
                                                                <!-- 发布卡片 -->
                                                                <div class="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition duration-200 overflow-hidden">
                                                                    <div class="border-b border-gray-100 px-4 py-3 flex justify-between items-center bg-gray-50">
                                                                        <div>
                                                                            {% if release.is_merged %}
                                                                                <h4 class="font-semibold text-lg">{{ release.display_title }}</h4>
                                                                            {% else %}
                                                                                <h4 class="font-semibold text-lg">{{ release.product_name }}</h4>
                                                                            {% endif %}
                                                                            <div class="text-sm text-gray-500">{{ release.date }}</div>
                                                                        </div>
                                                                        <div class="flex items-center">
                                                                            <span class="bg-unifi-blue text-white rounded-full px-3 py-1 text-xs font-medium">
                                                                                {{ release.version }}
                                                                            </span>
                                                                        </div>
                                                                    </div>
                                                                    
                                                                    <div class="p-4">
                                                                        {% if release.compatible_devices and release.compatible_devices|length > 1 %}
                                                                            <div class="mb-4 bg-blue-50 p-3 rounded-lg border border-blue-100">
                                                                                <div class="text-sm font-medium text-unifi-blue mb-1">适配设备 ({{ release.compatible_devices|length }}):</div>
                                                                                <div class="flex flex-wrap gap-1">
                                                                                    {% for device in release.compatible_devices %}
                                                                                        <span 
                                                                                            class="device-selector bg-white text-gray-800 text-xs px-2 py-1 rounded border cursor-pointer transition-colors duration-200 {% if loop.first %}border-unifi-blue bg-blue-50 selected-device{% else %}border-gray-200 hover:border-unifi-blue hover:bg-blue-50{% endif %}"
                                                                                            data-device-index="{{ loop.index0 }}"
                                                                                            data-release-id="{{ release.product_line }}-{{ release.version_type }}-{{ release.year }}-{{ release.version|replace('.', '-') }}">
                                                                                            {{ device }}
                                                                                        </span>
                                                                                    {% endfor %}
                                                                                </div>
                                                                            </div>
                                                                        {% endif %}
                                                                        
                                                                        {% if release.is_merged and release.combined_notes %}
                                                                            <div class="mb-4 text-sm text-gray-700">
                                                                                <div class="font-medium text-lg mb-2">版本说明</div>
                                                                                
                                                                                {% for note_entry in release.combined_notes %}
                                                                                    <div class="release-note-content mb-4 bg-blue-50 p-3 rounded-lg {% if not loop.first %}hidden{% endif %}"
                                                                                         data-device-index="{{ loop.index0 }}"
                                                                                         data-release-id="{{ release.product_line }}-{{ release.version_type }}-{{ release.year }}-{{ release.version|replace('.', '-') }}">
                                                                                        <div class="device-name font-semibold text-unifi-blue mb-2">{{ release.compatible_devices[loop.index0] }}</div>
                                                                                        <div class="whitespace-pre-line">{{ note_entry.notes }}</div>
                                                                                    </div>
                                                                                {% endfor %}
                                                                            </div>
                                                                        {% elif release.notes %}
                                                                            <div class="mb-4 text-sm text-gray-700 release-notes">
                                                                                {{ release.notes|truncate(300) }}
                                                                                {% if release.notes|length > 300 %}
                                                                                    <button class="text-unifi-blue hover:text-unifi-darkblue expand-notes">显示更多</button>
                                                                                    <div class="hidden full-notes mt-2">
                                                                                        {{ release.notes }}
                                                                                    </div>
                                                                                {% endif %}
                                                                            </div>
                                                                        {% endif %}
                                                                        
                                                                        {% if release.download_links or release.source_urls %}
                                                                            <div class="flex flex-wrap gap-2 mt-3">
                                                                                {% if release.source_urls and release.source_urls|length > 0 %}
                                                                                    {% for url in release.source_urls %}
                                                                                        {% if url %}
                                                                                        <a href="{{ url }}" target="_blank" rel="noopener" 
                                                                                           class="inline-flex items-center text-xs font-medium text-green-600 hover:text-green-800 border border-green-600 hover:bg-green-50 rounded px-2 py-1 transition duration-200">
                                                                                            <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path>
                                                                                            </svg>
                                                                                            {% if release.source_urls|length > 1 %}原帖 {{ loop.index }}{% else %}查看原帖{% endif %}
                                                                                        </a>
                                                                                        {% endif %}
                                                                                    {% endfor %}
                                                                                {% endif %}
                                                                                
                                                                                {% for link in release.download_links %}
                                                                                    <a href="{{ link.url }}" target="_blank" rel="noopener" 
                                                                                       class="inline-flex items-center text-xs font-medium text-unifi-blue hover:text-unifi-darkblue border border-unifi-blue hover:bg-unifi-blue/5 rounded px-2 py-1 transition duration-200">
                                                                                        <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                                                                                        </svg>
                                                                                        {{ link.name }}
                                                                                    </a>
                                                                                {% endfor %}
                                                                            </div>
                                                                        {% endif %}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        {% endfor %}
                                                    </div>
                                                </div>
                                            </div>
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            {% endfor %}
                        {% else %}
                            <!-- 非APP产品按版本类型显示内容 -->
                            {% for version_type in ['GA', 'RC', 'Beta', 'Alpha'] %}
                                {% if version_type in organized_data[product_line] %}
                                    <div class="version-content p-4" 
                                         id="content-{{ product_line }}-{{ version_type }}"
                                         style="display: {% if loop.first %}block{% else %}none{% endif %};">
                                        
                                        <!-- 年份分组 -->
                                        {% for year in organized_data[product_line][version_type]|sort(reverse=true) %}
                                            <div class="mb-6">
                                                <div class="year-header cursor-pointer flex items-center bg-gray-50 p-3 rounded-lg mb-2 hover:bg-gray-100 transition duration-200">
                                                    <svg class="year-arrow w-5 h-5 mr-2 text-unifi-blue transform transition-transform duration-200" viewBox="0 0 20 20" fill="currentColor">
                                                        <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                                                    </svg>
                                                    <h3 class="text-lg font-semibold">{{ year }}</h3>
                                                    <span class="ml-2 bg-unifi-blue text-white px-2 py-0.5 rounded-full text-xs">
                                                        {{ organized_data[product_line][version_type][year]|length }}
                                                    </span>
                                                </div>
                                                
                                                <div class="year-content ml-2">
                                                    <!-- 发布时间轴 -->
                                                    <div class="relative border-l-4 border-unifi-blue pl-8 ml-3">
                                                        {% for release in organized_data[product_line][version_type][year] %}
                                                            <div class="relative mb-8">
                                                                <!-- 时间轴节点 -->
                                                                <div class="absolute -left-11 mt-3.5">
                                                                    <div class="w-5 h-5 rounded-full bg-unifi-blue border-4 border-white shadow"></div>
                                                                </div>
                                                                
                                                                <!-- 发布卡片 -->
                                                                <div class="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition duration-200 overflow-hidden">
                                                                    <div class="border-b border-gray-100 px-4 py-3 flex justify-between items-center bg-gray-50">
                                                                        <div>
                                                                            {% if release.is_merged %}
                                                                                <h4 class="font-semibold text-lg">{{ release.display_title }}</h4>
                                                                            {% else %}
                                                                                <h4 class="font-semibold text-lg">{{ release.product_name }}</h4>
                                                                            {% endif %}
                                                                            <div class="text-sm text-gray-500">{{ release.date }}</div>
                                                                        </div>
                                                                        <div class="flex items-center">
                                                                            <span class="bg-unifi-blue text-white rounded-full px-3 py-1 text-xs font-medium">
                                                                                {{ release.version }}
                                                                            </span>
                                                                        </div>
                                                                    </div>
                                                                    
                                                                    <div class="p-4">
                                                                        {% if release.compatible_devices and release.compatible_devices|length > 1 %}
                                                                            <div class="mb-4 bg-blue-50 p-3 rounded-lg border border-blue-100">
                                                                                <div class="text-sm font-medium text-unifi-blue mb-1">适配设备 ({{ release.compatible_devices|length }}):</div>
                                                                                <div class="flex flex-wrap gap-1">
                                                                                    {% for device in release.compatible_devices %}
                                                                                        <span 
                                                                                            class="device-selector bg-white text-gray-800 text-xs px-2 py-1 rounded border cursor-pointer transition-colors duration-200 {% if loop.first %}border-unifi-blue bg-blue-50 selected-device{% else %}border-gray-200 hover:border-unifi-blue hover:bg-blue-50{% endif %}"
                                                                                            data-device-index="{{ loop.index0 }}"
                                                                                            data-release-id="{{ release.product_line }}-{{ release.version_type }}-{{ release.year }}-{{ release.version|replace('.', '-') }}">
                                                                                            {{ device }}
                                                                                        </span>
                                                                                    {% endfor %}
                                                                                </div>
                                                                            </div>
                                                                        {% endif %}
                                                                        
                                                                        {% if release.is_merged and release.combined_notes %}
                                                                            <div class="mb-4 text-sm text-gray-700">
                                                                                <div class="font-medium text-lg mb-2">版本说明</div>
                                                                                
                                                                                {% for note_entry in release.combined_notes %}
                                                                                    <div class="release-note-content mb-4 bg-blue-50 p-3 rounded-lg {% if not loop.first %}hidden{% endif %}"
                                                                                         data-device-index="{{ loop.index0 }}"
                                                                                         data-release-id="{{ release.product_line }}-{{ release.version_type }}-{{ release.year }}-{{ release.version|replace('.', '-') }}">
                                                                                        <div class="device-name font-semibold text-unifi-blue mb-2">{{ release.compatible_devices[loop.index0] }}</div>
                                                                                        <div class="whitespace-pre-line">{{ note_entry.notes }}</div>
                                                                                    </div>
                                                                                {% endfor %}
                                                                            </div>
                                                                        {% elif release.notes %}
                                                                            <div class="mb-4 text-sm text-gray-700 release-notes">
                                                                                {{ release.notes|truncate(300) }}
                                                                                {% if release.notes|length > 300 %}
                                                                                    <button class="text-unifi-blue hover:text-unifi-darkblue expand-notes">显示更多</button>
                                                                                    <div class="hidden full-notes mt-2">
                                                                                        {{ release.notes }}
                                                                                    </div>
                                                                                {% endif %}
                                                                            </div>
                                                                        {% endif %}
                                                                        
                                                                        {% if release.download_links or release.source_urls %}
                                                                            <div class="flex flex-wrap gap-2 mt-3">
                                                                                {% if release.source_urls and release.source_urls|length > 0 %}
                                                                                    {% for url in release.source_urls %}
                                                                                        {% if url %}
                                                                                        <a href="{{ url }}" target="_blank" rel="noopener" 
                                                                                           class="inline-flex items-center text-xs font-medium text-green-600 hover:text-green-800 border border-green-600 hover:bg-green-50 rounded px-2 py-1 transition duration-200">
                                                                                            <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path>
                                                                                            </svg>
                                                                                            {% if release.source_urls|length > 1 %}原帖 {{ loop.index }}{% else %}查看原帖{% endif %}
                                                                                        </a>
                                                                                        {% endif %}
                                                                                    {% endfor %}
                                                                                {% endif %}
                                                                                
                                                                                {% for link in release.download_links %}
                                                                                    <a href="{{ link.url }}" target="_blank" rel="noopener" 
                                                                                       class="inline-flex items-center text-xs font-medium text-unifi-blue hover:text-unifi-darkblue border border-unifi-blue hover:bg-unifi-blue/5 rounded px-2 py-1 transition duration-200">
                                                                                        <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                                                                                        </svg>
                                                                                        {{ link.name }}
                                                                                    </a>
                                                                                {% endfor %}
                                                                            </div>
                                                                        {% endif %}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        {% endfor %}
                                                    </div>
                                                </div>
                                            </div>
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            {% endfor %}
                        {% endif %}
                    </div>
                </section>
            {% endif %}
        {% endfor %}
        
        <footer class="mt-12 mb-6 text-center text-gray-600 text-sm">
            <p>© {{ current_year }} Unifi产品时间轴 | 数据更新时间: {{ generated_time }}</p>
        </footer>
    </div>

    <script>
        // 保存产品线版本类型统计信息，用于动态更新
        const productLineStats = {{ product_line_stats|tojson }};
        
        // 初始化页面功能
        document.addEventListener('DOMContentLoaded', function() {
            // 产品线筛选功能
            const productLineFilters = document.querySelectorAll('.product-line-filter');
            const productLineSections = document.querySelectorAll('.product-line-section');
            
            productLineFilters.forEach(filter => {
                filter.addEventListener('click', function() {
                    const productLine = this.getAttribute('data-product-line');
                    
                    // 更新按钮样式
                    productLineFilters.forEach(btn => {
                        btn.classList.remove('bg-unifi-darkblue');
                        btn.classList.add('bg-unifi-lightblue');
                    });
                    this.classList.remove('bg-unifi-lightblue');
                    this.classList.add('bg-unifi-darkblue');
                    
                    // 显示/隐藏相关部分
                    if (productLine === 'all') {
                        // 显示所有产品线
                        productLineSections.forEach(section => {
                            section.style.display = 'block';
                        });
                    } else {
                        // 只显示选中的产品线
                        productLineSections.forEach(section => {
                            if (section.id === productLine) {
                                section.style.display = 'block';
                            } else {
                                section.style.display = 'none';
                            }
                        });
                    }
                });
            });
            
            // 设置标签页激活状态
            const tabs = document.querySelectorAll('.version-tab');
            tabs.forEach(tab => {
                tab.addEventListener('click', function() {
                    const productLine = this.getAttribute('data-product-line');
                    const versionType = this.getAttribute('data-version-type');
                    
                    // 隐藏当前产品线下所有内容
                    const contents = document.querySelectorAll(`[id^="content-${productLine}-"]`);
                    contents.forEach(content => {
                        content.style.display = 'none';
                    });
                    
                    // 显示选中的内容
                    const selectedContent = document.getElementById(`content-${productLine}-${versionType}`);
                    if (selectedContent) {
                        selectedContent.style.display = 'block';
                    }
                    
                    // 更新标签样式
                    const productLineTabs = document.querySelectorAll(`[data-product-line="${productLine}"]`);
                    productLineTabs.forEach(t => {
                        if (t.classList.contains('version-tab')) {
                            t.classList.remove('border-unifi-blue', 'text-unifi-blue');
                            t.classList.add('border-transparent', 'text-gray-500', 'hover:text-gray-700', 'hover:border-gray-300');
                        }
                    });
                    
                    this.classList.remove('border-transparent', 'text-gray-500', 'hover:text-gray-700', 'hover:border-gray-300');
                    this.classList.add('border-unifi-blue', 'text-unifi-blue');
                });
                
                // 设置初始激活状态
                if (tab.getAttribute('data-version-type') === 'GA') {
                    tab.classList.add('border-unifi-blue', 'text-unifi-blue');
                } else {
                    tab.classList.add('border-transparent', 'text-gray-500', 'hover:text-gray-700', 'hover:border-gray-300');
                }
            });
            
            // 年份折叠/展开功能
            const yearHeaders = document.querySelectorAll('.year-header');
            yearHeaders.forEach(header => {
                header.addEventListener('click', function() {
                    const content = this.nextElementSibling;
                    const arrow = this.querySelector('.year-arrow');
                    
                    if (content.style.display === 'none') {
                        content.style.display = 'block';
                        arrow.classList.remove('rotate-180');
                    } else {
                        content.style.display = 'none';
                        arrow.classList.add('rotate-180');
                    }
                });
            });
            
            // 发布说明展开/收起功能
            const expandButtons = document.querySelectorAll('.expand-notes');
            expandButtons.forEach(button => {
                button.addEventListener('click', function() {
                    const notesContainer = this.closest('.release-notes');
                    const fullNotes = notesContainer.querySelector('.full-notes');
                    
                    if (fullNotes.classList.contains('hidden')) {
                        fullNotes.classList.remove('hidden');
                        this.textContent = '收起';
                    } else {
                        fullNotes.classList.add('hidden');
                        this.textContent = '显示更多';
                    }
                });
            });

            // 设备选择器与版本说明联动功能
            const deviceSelectors = document.querySelectorAll('.device-selector');
            deviceSelectors.forEach(selector => {
                selector.addEventListener('click', function() {
                    const deviceIndex = this.getAttribute('data-device-index');
                    const releaseId = this.getAttribute('data-release-id');
                    
                    // 更新选中状态样式
                    const relatedSelectors = document.querySelectorAll(`.device-selector[data-release-id="${releaseId}"]`);
                    relatedSelectors.forEach(sel => {
                        sel.classList.remove('border-unifi-blue', 'bg-blue-50', 'selected-device');
                        sel.classList.add('border-gray-200');
                    });
                    this.classList.remove('border-gray-200');
                    this.classList.add('border-unifi-blue', 'bg-blue-50', 'selected-device');
                    
                    // 更新显示内容
                    const releaseNotes = document.querySelectorAll(`.release-note-content[data-release-id="${releaseId}"]`);
                    releaseNotes.forEach(note => {
                        if (note.getAttribute('data-device-index') === deviceIndex) {
                            note.classList.remove('hidden');
                        } else {
                            note.classList.add('hidden');
                        }
                    });
                });
            });
        });
    </script>
</body>
</html>'''
        
        return html_template
    
    def generate_timeline(self):
        """生成时间轴HTML文件"""
        try:
            # 获取所有发布数据
            releases = self.get_all_releases()
            if not releases:
                logger.error("没有发布数据，无法生成时间轴")
                return False
            
            # 处理数据
            organized_data, stats, product_line_stats = self.process_releases(releases)
            
            # 创建Jinja2环境
            env = Environment(loader=FileSystemLoader('.'))
            
            # 添加模板
            template_content = self.create_template_files()
            template = env.from_string(template_content)
            
            # 找出最新更新日期
            latest_date = "未知"
            for release in releases:
                if release.get('release_date'):
                    date_str = self.format_date(release['release_date'])
                    if date_str and date_str != "None":
                        latest_date = date_str
                        break
            
            # 渲染模板并保存到文件
            html_output = template.render(
                organized_data=organized_data,
                stats=stats,
                product_line_stats=product_line_stats,
                product_line_order=PRODUCT_LINE_ORDER,
                product_line_labels=PRODUCT_LINE_LABELS,
                product_line_groups=PRODUCT_LINE_GROUPS,
                version_type_labels=VERSION_TYPE_LABELS,
                latest_update=latest_date
            )
            
            with open(self.html_file, 'w', encoding='utf-8') as f:
                f.write(html_output)
            
            logger.info(f"时间轴HTML文件已生成: {self.html_file}")
            return True
        except Exception as e:
            logger.error(f"生成时间轴失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def run(self):
        """运行生成器"""
        if not self.connect_db():
            return False
        
        try:
            success = self.generate_timeline()
            if success:
                logger.info(f"时间轴生成成功，请在浏览器中打开: {self.html_file}")
            else:
                logger.error("时间轴生成失败")
            
            return success
        finally:
            self.close_db()


if __name__ == "__main__":
    generator = ImprovedTimelineGenerator()
    success = generator.run()
    
    if not success:
        print("时间轴生成失败，请检查日志获取详细信息。")
    else:
        print(f"时间轴生成成功，请在浏览器中打开: {generator.html_file}") 