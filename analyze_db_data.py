#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
分析MongoDB中的数据结构，找出更合适的产品线分组方式
"""

import os
import json
import logging
from collections import defaultdict, Counter
from pymongo import MongoClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataAnalyzer:
    """数据分析器"""
    
    def __init__(self):
        """初始化连接"""
        self.mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        self.mongo_db = os.getenv('MONGO_DATABASE', 'unifi_releases')
        self.collection_name = 'unifi_releases'
        self.client = None
        self.db = None
    
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
            # 获取所有数据
            releases = list(self.db[self.collection_name].find())
            logger.info(f"已获取 {len(releases)} 条产品发布数据")
            return releases
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            return []
    
    def analyze_field_values(self, releases, field_name):
        """分析字段值的分布"""
        value_counts = Counter()
        
        for release in releases:
            value = release.get(field_name, None)
            if value is not None:
                value_counts[str(value)] += 1
        
        return value_counts
    
    def analyze_tags(self, releases):
        """分析tags字段"""
        all_tags = []
        tag_counts = Counter()
        tags_per_release = Counter()
        
        for release in releases:
            tags_str = release.get('tags', '[]')
            try:
                tags = json.loads(tags_str)
                if isinstance(tags, list):
                    tags_per_release[len(tags)] += 1
                    for tag in tags:
                        all_tags.append(tag)
                        tag_counts[tag] += 1
            except json.JSONDecodeError:
                logger.warning(f"无法解析tags: {tags_str}")
        
        return {
            'unique_tags': len(tag_counts),
            'total_tags': len(all_tags),
            'tags_per_release': dict(tags_per_release),
            'most_common_tags': tag_counts.most_common(50)
        }
    
    def identify_product_line_patterns(self, releases):
        """识别可能的产品线模式"""
        # 分析tags字段中的常见前缀
        tag_prefixes = Counter()
        product_name_prefixes = Counter()
        
        for release in releases:
            # 分析tags字段
            tags_str = release.get('tags', '[]')
            try:
                tags = json.loads(tags_str)
                if isinstance(tags, list):
                    for tag in tags:
                        # 获取前两个单词作为可能的前缀
                        words = str(tag).split()
                        if len(words) >= 2:
                            prefix = ' '.join(words[:2])
                            tag_prefixes[prefix] += 1
                        elif len(words) == 1:
                            tag_prefixes[words[0]] += 1
            except json.JSONDecodeError:
                pass
            
            # 分析product_name字段
            product_name = release.get('product_name', '')
            if product_name:
                words = product_name.split()
                if len(words) >= 2:
                    prefix = ' '.join(words[:2])
                    product_name_prefixes[prefix] += 1
                elif len(words) == 1:
                    product_name_prefixes[words[0]] += 1
        
        return {
            'tag_prefixes': tag_prefixes.most_common(20),
            'product_name_prefixes': product_name_prefixes.most_common(20)
        }
    
    def analyze_version_distribution(self, releases):
        """分析版本号分布"""
        version_counts = Counter()
        version_patterns = Counter()
        
        for release in releases:
            version = release.get('version', '')
            if version:
                version_counts[version] += 1
                
                # 识别版本模式 (x.y.z, vx.y 等)
                pattern = ''
                for char in version:
                    if char.isdigit():
                        pattern += 'n'
                    else:
                        pattern += char
                version_patterns[pattern] += 1
        
        return {
            'unique_versions': len(version_counts),
            'most_common_versions': version_counts.most_common(20),
            'version_patterns': version_patterns.most_common(10)
        }
    
    def analyze_product_line_candidates(self, releases):
        """分析可能的产品线字段"""
        product_lines = defaultdict(Counter)
        
        # 分析常见的产品线字段
        fields_to_check = ['product_name', 'firmware_type', 'stage']
        
        for release in releases:
            for field in fields_to_check:
                value = release.get(field, '')
                if value:
                    product_lines[field][value] += 1
        
        # 分析tags字段中的可能产品线
        for release in releases:
            tags_str = release.get('tags', '[]')
            try:
                tags = json.loads(tags_str)
                if isinstance(tags, list) and len(tags) > 0:
                    # 假设第一个标签可能是产品线
                    product_lines['first_tag'][tags[0]] += 1
                    
                    # 检查包含特定关键词的标签
                    for tag in tags:
                        if any(keyword in tag.lower() for keyword in ['unifi', 'edgemax', 'airmax', 'amplifi']):
                            product_lines['keyword_in_tag'][tag] += 1
            except json.JSONDecodeError:
                pass
        
        return {
            field: {
                'unique_values': len(counter),
                'most_common': counter.most_common(20)
            }
            for field, counter in product_lines.items()
        }
    
    def print_analysis_results(self, results):
        """打印分析结果"""
        print("\n===== 数据分析结果 =====\n")
        
        # 打印字段分布
        for field, info in results['field_distributions'].items():
            print(f"\n----- {field} 字段值分布 -----")
            print(f"唯一值数量: {len(info)}")
            if len(info) <= 20:
                for value, count in info.most_common():
                    print(f"  {value}: {count}")
            else:
                print("前20个常见值:")
                for value, count in info.most_common(20):
                    print(f"  {value}: {count}")
                
        # 打印tags分析
        print("\n----- Tags 分析 -----")
        tags_info = results['tags_analysis']
        print(f"唯一标签数量: {tags_info['unique_tags']}")
        print(f"标签总数: {tags_info['total_tags']}")
        print(f"每条记录的标签数分布: {tags_info['tags_per_release']}")
        print("\n最常见的标签:")
        for tag, count in tags_info['most_common_tags']:
            print(f"  {tag}: {count}")
        
        # 打印产品线模式识别
        print("\n----- 产品线模式识别 -----")
        patterns = results['product_line_patterns']
        print("\nTags中的常见前缀:")
        for prefix, count in patterns['tag_prefixes']:
            print(f"  {prefix}: {count}")
        
        print("\nProduct Name中的常见前缀:")
        for prefix, count in patterns['product_name_prefixes']:
            print(f"  {prefix}: {count}")
        
        # 打印版本分布
        print("\n----- 版本号分布 -----")
        version_info = results['version_distribution']
        print(f"唯一版本数量: {version_info['unique_versions']}")
        print("\n最常见的版本格式:")
        for pattern, count in version_info['version_patterns']:
            print(f"  {pattern}: {count}")
        
        # 打印可能的产品线字段
        print("\n----- 可能的产品线字段 -----")
        for field, info in results['product_line_candidates'].items():
            print(f"\n{field} 字段作为产品线:")
            print(f"唯一值数量: {info['unique_values']}")
            print("最常见值:")
            for value, count in info['most_common']:
                print(f"  {value}: {count}")
    
    def suggest_product_line_strategy(self, results):
        """根据分析结果建议产品线分组策略"""
        print("\n===== 产品线分组策略建议 =====\n")
        
        # 分析各字段作为产品线的适合度
        candidates = results['product_line_candidates']
        
        # 最佳候选字段及其唯一值数量
        best_candidates = [
            (field, info['unique_values']) 
            for field, info in candidates.items()
        ]
        
        # 对候选排序，寻找合适的分组数量
        best_candidates.sort(key=lambda x: abs(x[1] - 20))  # 假设理想的产品线数量在20左右
        
        print(f"可能的产品线字段候选（按接近理想分组数量排序）:")
        for field, unique_count in best_candidates:
            print(f"  {field}: {unique_count} 个唯一值")
        
        # 提出具体建议
        if best_candidates:
            best_field, _ = best_candidates[0]
            print(f"\n推荐使用 {best_field} 字段作为产品线分组依据。")
            
            # 提出具体的分组实现建议
            if best_field == 'product_name':
                print("建议直接使用product_name字段作为产品线分组。")
            elif best_field == 'first_tag':
                print("建议使用tags字段的第一个元素作为产品线分组。")
            elif best_field == 'keyword_in_tag':
                print("建议在tags中寻找包含产品关键词的标签作为产品线分组。")
            else:
                print(f"建议直接使用{best_field}字段作为产品线分组。")
        
        # 查看是否需要合并某些产品线
        highest_count_field = max(candidates.items(), key=lambda x: x[1]['unique_values'])[0]
        if candidates[highest_count_field]['unique_values'] > 50:
            print("\n当前最佳候选字段的唯一值仍然较多，建议考虑以下合并策略:")
            print("1. 按前缀合并：将相同前缀的值合并为一个产品线")
            print("2. 按关键词合并：将包含相同关键词的值合并为一个产品线")
            print("3. 手动定义映射：预定义主要产品线，将各值映射到这些主要产品线")
    
    def run(self):
        """运行分析器"""
        if not self.connect_db():
            return False
        
        try:
            releases = self.get_all_releases()
            if not releases:
                logger.error("未获取到数据，无法进行分析")
                return False
            
            results = {}
            
            # 分析每个字段的值分布
            field_distributions = {}
            common_fields = ['product_name', 'version', 'firmware_type', 'stage', 'is_beta']
            for field in common_fields:
                field_distributions[field] = self.analyze_field_values(releases, field)
            
            results['field_distributions'] = field_distributions
            
            # 分析tags字段
            results['tags_analysis'] = self.analyze_tags(releases)
            
            # 识别产品线模式
            results['product_line_patterns'] = self.identify_product_line_patterns(releases)
            
            # 分析版本分布
            results['version_distribution'] = self.analyze_version_distribution(releases)
            
            # 分析可能的产品线字段
            results['product_line_candidates'] = self.analyze_product_line_candidates(releases)
            
            # 打印分析结果
            self.print_analysis_results(results)
            
            # 提出产品线分组策略建议
            self.suggest_product_line_strategy(results)
            
            return True
        finally:
            self.close_db()


if __name__ == "__main__":
    analyzer = DataAnalyzer()
    success = analyzer.run()
    
    if not success:
        print("数据分析失败，请检查日志获取详细信息。") 