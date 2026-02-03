#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
邮箱客户端模块
负责连接邮箱、搜索和获取邮件内容
"""

import imaplib
import email
from typing import List, Dict
import datetime
import re
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EmailClient:
    """
    邮箱客户端类
    """
    
    def __init__(self, email_address: str, auth_code: str, imap_server: str = "imap.qq.com", imap_port: int = 993):
        """
        初始化邮箱客户端
        
        Args:
            email_address: 邮箱地址
            auth_code: 授权码
            imap_server: IMAP服务器地址
            imap_port: IMAP服务器端口
        """
        self.email_address = email_address
        self.auth_code = auth_code
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.mail = None
    
    def connect(self):
        """
        连接到IMAP服务器
        """
        try:
            # 连接到IMAP服务器
            logger.info(f"正在连接到IMAP服务器: {self.imap_server}:{self.imap_port}")
            self.mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            # 登录
            logger.info(f"正在登录邮箱: {self.email_address}")
            self.mail.login(self.email_address, self.auth_code)
            logger.info("邮箱连接成功")
        except Exception as e:
            logger.error(f"邮箱连接失败: {e}")
            raise
    
    def _ensure_connection(self):
        """
        确保IMAP连接有效，如果连接断开则重新连接
        """
        try:
            # 尝试发送noop命令检查连接状态
            if self.mail:
                self.mail.noop()
            else:
                # 如果没有连接，则重新连接
                logger.info("没有邮箱连接，正在重新连接...")
                self.connect()
        except (imaplib.IMAP4.abort, imaplib.IMAP4.error):
            # 连接已断开，重新连接
            logger.warning("邮箱连接已断开，正在重新连接...")
            try:
                if self.mail:
                    self.mail.logout()
            except:
                pass
            self.connect()
    
    def _sanitize_email_id(self, email_id):
        """
        清理和验证邮件ID格式
        
        Args:
            email_id: 原始邮件ID
            
        Returns:
            清理后的邮件ID
        """
        # 如果是bytes类型，先解码
        if isinstance(email_id, bytes):
            email_id = email_id.decode('utf-8')
        
        # 如果是字符串，去除首尾空格
        if isinstance(email_id, str):
            email_id = email_id.strip()
            
        # 验证邮件ID是否只包含数字（大多数IMAP服务器的邮件ID是数字）
        if isinstance(email_id, str) and re.match(r'^\d+$', email_id):
            return email_id
            
        # 如果无法验证格式，转换为字符串并返回
        return str(email_id)
    
    def search_scholar_emails(self, max_emails: int = 10, sender: str = None, folder: str = "inbox") -> List[str]:
        """
        搜索Google Scholar Alerts邮件
        
        Args:
            max_emails: 最大处理邮件数
            sender: 发件人邮箱地址（已弃用，不再使用）
            folder: 邮箱文件夹名称，默认为"inbox"
            
        Returns:
            邮件ID列表
        """
        try:
            # 确保连接有效
            self._ensure_connection()
            
            # 选择指定的文件夹
            logger.info(f"正在选择邮箱文件夹: {folder}")
            self.mail.select(folder)
            
            # 搜索文件夹下所有邮件
            logger.info(f"正在搜索文件夹 {folder} 下的所有邮件")
            status, messages = self.mail.search(None, "ALL")
            
            # 获取邮件ID列表
            email_ids = messages[0].split() if messages and messages[0] else []
            
            # 清理邮件ID格式
            email_ids = [self._sanitize_email_id(eid) for eid in email_ids]
            
            # 过滤掉无效的邮件ID（不是数字的ID）
            email_ids = [eid for eid in email_ids if re.match(r'^\d+$', str(eid))]
            
            # 按时间倒序排列（最新的邮件在前面）
            email_ids.reverse()
            
            # 返回最新的几封邮件
            result = email_ids[:max_emails] if len(email_ids) > max_emails else email_ids
            logger.info(f"找到 {len(result)} 封符合条件的邮件")
            return result
        except Exception as e:
            logger.error(f"搜索邮件时出错: {e}")
            return []
    
    def get_email_content(self, email_id: str) -> str:
        """
        获取邮件内容
        
        Args:
            email_id: 邮件ID
            
        Returns:
            邮件正文内容
        """
        try:
            # 确保连接有效
            self._ensure_connection()
            
            # 清理邮件ID
            email_id = self._sanitize_email_id(email_id)
            
            # 获取邮件内容
            logger.info(f"正在获取邮件 {email_id} 的内容")
            status, msg_data = self.mail.fetch(email_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            
            # 获取邮件正文
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            logger.info(f"成功获取邮件 {email_id} 的内容，长度: {len(body)} 字符")
            return body
        except Exception as e:
            logger.error(f"获取邮件内容时出错: {e}")
            return ""
    
    def get_email_receive_time(self, email_id: str) -> str:
        """
        获取邮件接收时间
        
        Args:
            email_id: 邮件ID
            
        Returns:
            邮件接收时间字符串
        """
        try:
            # 确保连接有效
            self._ensure_connection()
            
            # 清理邮件ID
            email_id = self._sanitize_email_id(email_id)
            
            # 获取邮件头部信息
            logger.info(f"正在获取邮件 {email_id} 的接收时间")
            status, msg_data = self.mail.fetch(email_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            
            # 获取日期头部
            date_header = msg.get("Date")
            if date_header:
                try:
                    # 解析日期
                    date_tuple = email.utils.parsedate_tz(date_header)
                    if date_tuple:
                        # 转换为本地时间
                        local_date = datetime.datetime.fromtimestamp(
                            email.utils.mktime_tz(date_tuple)
                        )
                        receive_time = local_date.strftime("%Y-%m-%d %H:%M:%S")
                        logger.info(f"邮件 {email_id} 的接收时间: {receive_time}")
                        return receive_time
                except Exception as e:
                    logger.error(f"解析邮件时间出错: {e}")
            
            # 如果无法解析，返回当前时间
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.warning(f"无法解析邮件时间，返回当前时间: {current_time}")
            return current_time
        except Exception as e:
            logger.error(f"获取邮件接收时间时出错: {e}")
            return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def get_email_info(self, email_id: str) -> Dict[str, str]:
        """
        一次性获取邮件的所有必要信息（内容和接收时间）
        
        Args:
            email_id: 邮件ID
            
        Returns:
            包含邮件内容和接收时间的字典
        """
        try:
            # 确保连接有效
            self._ensure_connection()
            
            # 清理邮件ID
            email_id = self._sanitize_email_id(email_id)
            
            # 获取邮件头部信息和内容
            logger.info(f"正在获取邮件 {email_id} 的信息")
            status, msg_data = self.mail.fetch(email_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            
            # 获取邮件正文
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            # 获取日期头部
            date_header = msg.get("Date")
            receive_time = ""
            if date_header:
                try:
                    # 解析日期
                    date_tuple = email.utils.parsedate_tz(date_header)
                    if date_tuple:
                        # 转换为本地时间
                        local_date = datetime.datetime.fromtimestamp(
                            email.utils.mktime_tz(date_tuple)
                        )
                        receive_time = local_date.strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    logger.error(f"解析邮件时间出错: {e}")
            
            # 如果无法解析，返回当前时间
            if not receive_time:
                receive_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.warning(f"无法解析邮件时间，返回当前时间: {receive_time}")
            
            logger.info(f"成功获取邮件 {email_id} 的信息")
            return {
                "content": body,
                "receive_time": receive_time
            }
        except Exception as e:
            logger.error(f"获取邮件信息时出错: {e}")
            return {
                "content": "",
                "receive_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def mark_email_as_read(self, email_id: str, folder: str = "inbox") -> bool:
        """
        标记邮件为已读
        
        Args:
            email_id: 邮件ID
            folder: 邮箱文件夹名称，默认为"inbox"
            
        Returns:
            标记成功返回True，否则返回False
        """
        try:
            # 确保连接有效
            self._ensure_connection()
            
            # 清理邮件ID
            email_id = self._sanitize_email_id(email_id)
            
            # 选择邮箱文件夹，确保处于SELECTED状态
            logger.info(f"正在选择邮箱文件夹: {folder}")
            self.mail.select(folder)
            
            # 标记邮件为已读
            logger.info(f"正在标记邮件 {email_id} 为已读")
            status, data = self.mail.store(email_id, '+FLAGS', '\\Seen')
            
            # 检查操作是否成功
            if status == 'OK':
                logger.info(f"邮件 {email_id} 已成功标记为已读")
                return True
            else:
                logger.error(f"标记邮件 {email_id} 为已读失败: {data}")
                return False
        except Exception as e:
            logger.error(f"标记邮件 {email_id} 为已读时出错: {e}")
            return False
    
    def get_emails_batch(self, max_emails: int = 10, batch_size: int = 5, sender: str = None, folder: str = "inbox"):
        """
        分批获取邮件ID的生成器函数
        
        Args:
            max_emails: 最大处理邮件数
            batch_size: 每批邮件数量
            sender: 发件人邮箱地址（已弃用，不再使用）
            folder: 邮箱文件夹名称，默认为"inbox"
            
        Yields:
            邮件ID列表的批次
        """
        # 确保连接有效
        self._ensure_connection()
        
        # 选择指定的文件夹
        logger.info(f"正在选择邮箱文件夹: {folder}")
        self.mail.select(folder)
        
        # 重试次数和延迟设置
        max_retries = 5  # 增加重试次数
        retry_delay = 10  # 增加初始延迟时间
        
        for attempt in range(max_retries):
            try:
                # 搜索文件夹下所有邮件
                logger.info(f"正在搜索文件夹 {folder} 下的所有邮件（第 {attempt + 1} 次尝试）")
                status, messages = self.mail.search(None, "ALL")
                
                # 检查返回的消息是否包含服务器忙的提示
                if messages and len(messages) > 0 and messages[0]:
                    # 检查返回内容是否包含"busy"关键字
                    first_message = messages[0]
                    if isinstance(first_message, bytes):
                        first_message_str = first_message.decode('utf-8', errors='ignore')
                    else:
                        first_message_str = str(first_message)
                        
                    if "busy" in first_message_str.lower():
                        logger.warning(f"IMAP服务器繁忙: {first_message_str}")
                        raise imaplib.IMAP4.error("Server busy")
                
                # 如果没有错误，跳出重试循环
                break
                
            except (imaplib.IMAP4.abort, imaplib.IMAP4.error) as e:
                # 处理IMAP服务器错误，包括服务器繁忙的情况
                error_msg = str(e).lower()
                is_busy_error = "busy" in error_msg or "unavailable" in error_msg or "timeout" in error_msg
                
                if is_busy_error:
                    logger.warning(f"IMAP服务器繁忙或不可用: {e}")
                    if attempt < max_retries - 1:  # 不是最后一次尝试
                        wait_time = retry_delay * (2 ** attempt)  # 指数退避
                        logger.info(f"等待 {wait_time} 秒后重试... (第 {attempt + 1} 次重试)")
                        time.sleep(wait_time)
                        # 尝试重新连接
                        try:
                            self._ensure_connection()
                            # 重新选择文件夹
                            logger.info(f"重新选择邮箱文件夹: {folder}")
                            self.mail.select(folder)
                        except Exception as reconnect_error:
                            logger.error(f"重新连接失败: {reconnect_error}")
                    else:
                        logger.error("达到最大重试次数，返回空结果")
                        messages = [b'']  # 返回空结果
                        break
                else:
                    # 其他IMAP错误，重新抛出
                    logger.error(f"搜索邮件时出现错误: {e}")
                    raise
        
        # 获取邮件ID列表
        email_ids = messages[0].split() if messages and messages[0] else []
        
        # 清理邮件ID格式
        email_ids = [self._sanitize_email_id(eid) for eid in email_ids]
        
        # 过滤掉无效的邮件ID（不是数字的ID）
        email_ids = [eid for eid in email_ids if re.match(r'^\d+$', str(eid))]
        
        # 按时间倒序排列（最新的邮件在前面）
        email_ids.reverse()
        
        # 确定要处理的邮件范围
        email_ids = email_ids[:max_emails] if len(email_ids) > max_emails else email_ids
        
        logger.info(f"找到 {len(email_ids)} 封符合条件的邮件，将按每批 {batch_size} 封进行处理")
        
        # 分批返回邮件ID
        for i in range(0, len(email_ids), batch_size):
            batch = email_ids[i:i + batch_size]
            logger.info(f"返回第 {i // batch_size + 1} 批邮件，共 {len(batch)} 封")
            yield batch
    
    def close(self):
        """
        关闭邮箱连接
        """
        if self.mail:
            try:
                logger.info("正在关闭邮箱连接...")
                self.mail.close()
                self.mail.logout()
                logger.info("邮箱连接已成功关闭")
            except (imaplib.IMAP4.abort, imaplib.IMAP4.error):
                # 如果连接已经断开，忽略错误
                logger.warning("邮箱连接已断开，忽略关闭操作")
            finally:
                self.mail = None
    
    def check_folder_exists(self, folder: str) -> bool:
        """
        检查邮箱文件夹是否存在
        
        Args:
            folder: 文件夹名称
            
        Returns:
            文件夹是否存在
        """
        try:
            # 确保连接有效
            self._ensure_connection()
            
            # 获取所有文件夹列表
            status, folders = self.mail.list()
            
            if status != 'OK':
                logger.error(f"获取文件夹列表失败: {folders}")
                return False
            
            # 检查目标文件夹是否在列表中
            for folder_info in folders:
                # 解析文件夹信息
                if isinstance(folder_info, bytes):
                    folder_info = folder_info.decode('utf-8')
                
                # 提取文件夹名称
                # 格式通常是: "(\HasNoChildren) "/" "INBOX"
                match = re.search(r'"([^"]+)"$', folder_info)
                if match:
                    folder_name = match.group(1)
                    if folder_name == folder:
                        logger.info(f"文件夹 '{folder}' 存在")
                        return True
            
            logger.warning(f"文件夹 '{folder}' 不存在")
            return False
        except Exception as e:
            logger.error(f"检查文件夹是否存在时出错: {e}")
            return False