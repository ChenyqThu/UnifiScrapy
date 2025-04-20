"""
工具函数模块
"""
import os
import pickle
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Set, Optional, Dict, Any
from datetime import datetime


def load_checkpoint(checkpoint_file: str) -> Set[str]:
    """
    加载断点续爬的检查点
    
    Args:
        checkpoint_file: 检查点文件路径
        
    Returns:
        已处理ID的集合
    """
    logger = logging.getLogger(__name__)
    
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'rb') as f:
                processed_ids = pickle.load(f)
            logger.info(f"加载断点续爬检查点，已有 {len(processed_ids)} 条记录")
            
            # 验证检查点数据格式
            if not isinstance(processed_ids, set):
                logger.warning("检查点数据格式错误，将创建新的检查点")
                return set()
                
            return processed_ids
        except Exception as e:
            logger.error(f"加载检查点失败: {e}")
            
            # 创建检查点备份
            if os.path.getsize(checkpoint_file) > 0:
                backup_file = f"{checkpoint_file}.bak.{int(datetime.now().timestamp())}"
                try:
                    import shutil
                    shutil.copy2(checkpoint_file, backup_file)
                    logger.info(f"已创建检查点备份: {backup_file}")
                except Exception as backup_err:
                    logger.error(f"创建检查点备份失败: {backup_err}")
    
    logger.info("未找到检查点文件或加载失败，将创建新的检查点")
    return set()


def save_checkpoint(checkpoint_file: str, processed_ids: Set[str]) -> bool:
    """
    保存断点续爬的检查点
    
    Args:
        checkpoint_file: 检查点文件路径
        processed_ids: 已处理ID的集合
        
    Returns:
        是否保存成功
    """
    logger = logging.getLogger(__name__)
    
    # 检查数据有效性
    if not isinstance(processed_ids, set) or not processed_ids:
        logger.warning("检查点数据无效或为空，跳过保存")
        return False
    
    # 先创建临时文件，成功后再替换
    temp_file = f"{checkpoint_file}.tmp"
    try:
        with open(temp_file, 'wb') as f:
            pickle.dump(processed_ids, f)
        
        # 如果原文件存在，先备份
        if os.path.exists(checkpoint_file):
            backup_file = f"{checkpoint_file}.prev"
            try:
                import shutil
                shutil.copy2(checkpoint_file, backup_file)
            except Exception as backup_err:
                logger.warning(f"创建检查点前备份失败: {backup_err}")
        
        # 将临时文件替换为正式文件
        import shutil
        shutil.move(temp_file, checkpoint_file)
        
        logger.info(f"已保存检查点，共 {len(processed_ids)} 条记录")
        return True
    except Exception as e:
        logger.error(f"保存检查点失败: {e}")
        
        # 如果临时文件创建失败，尝试直接保存
        if not os.path.exists(temp_file):
            try:
                with open(checkpoint_file, 'wb') as f:
                    pickle.dump(processed_ids, f)
                logger.info(f"使用备选方法保存检查点，共 {len(processed_ids)} 条记录")
                return True
            except Exception as direct_err:
                logger.error(f"备选保存方法也失败: {direct_err}")
        
        return False


def clean_crawl_data(checkpoint_file: str, cache_dir: Optional[str] = None) -> None:
    """
    清除缓存和断点数据
    
    Args:
        checkpoint_file: 检查点文件路径
        cache_dir: 缓存目录路径
    """
    logger = logging.getLogger(__name__)
    
    # 清除检查点文件
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
        logger.info("已清除检查点文件")
    
    # 清除缓存目录
    if cache_dir and os.path.exists(cache_dir):
        import shutil
        shutil.rmtree(cache_dir)
        logger.info(f"已清除缓存目录: {cache_dir}")


def send_email(subject: str, message: str) -> bool:
    """
    发送通知邮件
    
    Args:
        subject: 邮件主题
        message: 邮件内容
        
    Returns:
        是否发送成功
    """
    logger = logging.getLogger(__name__)
    
    enable_email = os.getenv('ENABLE_EMAIL', 'False').lower() == 'true'
    if not enable_email:
        logger.debug("邮件通知已禁用")
        return False
    
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    recipient = os.getenv('NOTIFICATION_EMAIL')
    
    if not all([smtp_server, smtp_user, smtp_password, recipient]):
        logger.warning("邮件配置不完整，跳过邮件发送")
        return False
    
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = recipient
    msg['Subject'] = subject
    
    msg.attach(MIMEText(message, 'plain'))
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        logger.info(f"通知邮件已发送至 {recipient}")
        return True
    except Exception as e:
        logger.error(f"发送邮件失败: {e}")
        return False


def clean_text(text: Optional[str]) -> str:
    """
    清理文本，去除多余空格和换行
    
    Args:
        text: 待清理的文本
        
    Returns:
        清理后的文本
    """
    if not text:
        return ""
    
    # 移除HTML标签
    import re
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # 替换特殊字符
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text.strip())
    
    return text


def parse_date(date_str: str) -> Optional[datetime]:
    """
    解析日期字符串为datetime对象
    
    Args:
        date_str: 日期字符串
        
    Returns:
        解析后的datetime对象
    """
    date_str = clean_text(date_str)
    
    # 如果是数字（可能是时间戳），尝试转换
    if date_str.isdigit():
        timestamp = int(date_str)
        # 根据长度判断是秒还是毫秒
        if len(date_str) > 10:
            timestamp = timestamp / 1000
        try:
            return datetime.fromtimestamp(timestamp)
        except:
            pass
    
    date_formats = [
        '%Y-%m-%d',           # 2023-04-20
        '%Y/%m/%d',           # 2023/04/20
        '%b %d, %Y',          # Apr 20, 2023
        '%d %b %Y',           # 20 Apr 2023
        '%B %d, %Y',          # April 20, 2023
        '%d %B %Y',           # 20 April 2023
        '%b %d',              # Apr 20 (当前年)
        '%d %b',              # 20 Apr (当前年)
        '%m/%d/%Y',           # 04/20/2023
        '%d/%m/%Y',           # 20/04/2023
        '%Y-%m-%dT%H:%M:%S',  # 2023-04-20T14:30:00
        '%Y-%m-%d %H:%M:%S'   # 2023-04-20 14:30:00
    ]
    
    current_year = datetime.now().year
    
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # 对于没有年份的格式，设置为当前年
            if fmt in ['%b %d', '%d %b']:
                dt = dt.replace(year=current_year)
            return dt
        except ValueError:
            continue
    
    # 尝试使用更灵活的解析
    try:
        import dateutil.parser
        return dateutil.parser.parse(date_str)
    except:
        pass
    
    # 提取日期模式
    import re
    # 查找形如 2023.4.20 或 2023.04.20 的格式
    match = re.search(r'(\d{4})[\.-](\d{1,2})[\.-](\d{1,2})', date_str)
    if match:
        try:
            year, month, day = map(int, match.groups())
            return datetime(year, month, day)
        except:
            pass
    
    return None 