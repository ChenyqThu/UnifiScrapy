#!/usr/bin/env python
"""
Ubiquiti产品发布爬虫运行脚本
基于GraphQL API重构版本
"""
import os
import sys
import time
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

from unifi_scraper.graphql_scraper import GraphQLScraper
from unifi_scraper.utils import clean_crawl_data, send_email


# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('unifi_scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# 加载环境变量
load_dotenv()


def parse_args():
    """
    解析命令行参数
    
    Returns:
        解析后的参数
    """
    parser = argparse.ArgumentParser(description='运行 Ubiquiti 产品发布爬虫 (GraphQL版)')
    parser.add_argument('--clean', action='store_true', help='清除断点数据，从头开始爬取')
    parser.add_argument('--limit', type=int, default=0, help='爬取的最大数量，0表示不限制')
    parser.add_argument('--checkpoint', type=str, default='checkpoint.pkl', help='检查点文件路径')
    parser.add_argument('--skip-ssl-verify', action='store_true', help='跳过SSL验证')
    parser.add_argument('--batch-size', type=int, default=50, help='每批次爬取数量')
    return parser.parse_args()


def main():
    """主运行函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 设置环境变量
    if args.skip_ssl_verify:
        os.environ['SSL_VERIFY'] = 'False'
    
    # 检查点文件路径
    checkpoint_file = args.checkpoint
    
    # 如果指定了清除数据，则清除检查点
    if args.clean:
        clean_crawl_data(checkpoint_file)
    
    # 记录开始时间
    start_time = time.time()
    logging.info("开始爬取 Ubiquiti 产品发布页面 (GraphQL版)...")
    
    try:
        # 创建爬虫实例
        scraper = GraphQLScraper(checkpoint_file=checkpoint_file)
        
        # 设置MongoDB连接
        if not scraper.setup():
            logging.error("爬虫设置失败，无法连接到MongoDB")
            return False
        
        # 执行爬取
        success = scraper.scrape(limit=args.limit)
        
        # 计算运行时间
        duration = time.time() - start_time
        
        if success:
            logging.info(f"爬取完成! 总用时: {duration:.2f} 秒")
            
            # 发送通知邮件
            send_email(
                subject="Ubiquiti 产品发布爬虫已完成",
                message=f"爬虫已成功运行，总用时: {duration:.2f} 秒。\n运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            return True
        else:
            logging.error(f"爬取失败! 总用时: {duration:.2f} 秒")
            
            # 发送通知邮件
            send_email(
                subject="Ubiquiti 产品发布爬虫失败",
                message=f"爬虫运行失败。\n运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            return False
        
    except Exception as e:
        # 计算运行时间
        duration = time.time() - start_time
        
        logging.error(f"爬虫运行出错: {e}")
        
        # 发送通知邮件
        send_email(
            subject="Ubiquiti 产品发布爬虫出错",
            message=f"爬虫运行出错，错误信息: {str(e)}\n运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return False


if __name__ == "__main__":
    main() 