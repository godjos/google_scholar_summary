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


class EmailClient:
    """
    邮箱客户端类
    """
    
    def __init__(self, email_address: str, auth_code: str, imap_server: str = "imap.qq.com"):
        """
        初始化邮箱客户端
        
        Args:
            email_address: 邮箱地址
            auth_code: 授权码
            imap_server: IMAP服务器地址
        """
        self.email_address = email_address
        self.auth_code = auth_code
        self.imap_server = imap_server
        self.mail = None
    
    def connect(self):
        """
        连接到IMAP服务器
        """
        # 连接到IMAP服务器
        self.mail = imaplib.IMAP4_SSL(self.imap_server)
        # 登录
        self.mail.login(self.email_address, self.auth_code)
    
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
                self.connect()
        except (imaplib.IMAP4.abort, imaplib.IMAP4.error):
            # 连接已断开，重新连接
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
    
    def search_scholar_emails(self, max_emails: int = 10, sender: str = "scholaralerts-noreply@google.com", folder: str = "inbox") -> List[str]:
        """
        搜索Google Scholar Alerts邮件
        
        Args:
            max_emails: 最大处理邮件数
            sender: 发件人邮箱地址
            folder: 邮箱文件夹名称，默认为"inbox"
            
        Returns:
            邮件ID列表
        """
        # 确保连接有效
        self._ensure_connection()
        
        # 选择指定的文件夹
        self.mail.select(folder)
        
        # 搜索指定发件人的未读邮件
        status, messages = self.mail.search(None, f'FROM "{sender}" UNSEEN')
        
        # 获取邮件ID列表
        email_ids = messages[0].split()
        
        print(f"IMAP search returned {len(email_ids)} email IDs.")

        exit(0)

        # 清理邮件ID格式
        email_ids = [self._sanitize_email_id(eid) for eid in email_ids]
        
        # 按时间倒序排列（最新的邮件在前面）
        # 由于IMAP返回的ID列表已经是按时间顺序的，我们只需要反转它
        email_ids.reverse()
        
        # 返回最新的几封邮件
        return email_ids[:max_emails] if len(email_ids) > max_emails else email_ids
    
    def get_email_content(self, email_id: str) -> str:
        """
        获取邮件内容
        
        Args:
            email_id: 邮件ID
            
        Returns:
            邮件正文内容
        """
        # 确保连接有效
        self._ensure_connection()
        
        # 清理邮件ID
        email_id = self._sanitize_email_id(email_id)
        
        # 获取邮件内容
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
        
        return body
    
    def get_email_receive_time(self, email_id: str) -> str:
        """
        获取邮件接收时间
        
        Args:
            email_id: 邮件ID
            
        Returns:
            邮件接收时间字符串
        """
        # 确保连接有效
        self._ensure_connection()
        
        # 清理邮件ID
        email_id = self._sanitize_email_id(email_id)
        
        # 获取邮件头部信息
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
                    return local_date.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                print(f"解析邮件时间出错: {e}")
        
        # 如果无法解析，返回当前时间
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def get_email_info(self, email_id: str) -> Dict[str, str]:
        """
        一次性获取邮件的所有必要信息（内容和接收时间）
        
        Args:
            email_id: 邮件ID
            
        Returns:
            包含邮件内容和接收时间的字典
        """
        # 确保连接有效
        self._ensure_connection()
        
        # 清理邮件ID
        email_id = self._sanitize_email_id(email_id)
        
        # 获取邮件头部信息和内容
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
                print(f"解析邮件时间出错: {e}")
        
        # 如果无法解析，返回当前时间
        if not receive_time:
            receive_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return {
            "content": body,
            "receive_time": receive_time
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
            self.mail.select(folder)
            
            # 标记邮件为已读
            status, data = self.mail.store(email_id, '+FLAGS', '\\Seen')
            
            # 检查操作是否成功
            if status == 'OK':
                return True
            else:
                print(f"标记邮件 {email_id} 为已读失败: {data}")
                return False
        except Exception as e:
            print(f"标记邮件 {email_id} 为已读时出错: {e}")
            return False
    
    def get_emails_batch(self, max_emails: int = 10, batch_size: int = 5, sender: str = "scholaralerts-noreply@google.com", folder: str = "inbox"):
        """
        分批获取邮件ID的生成器函数
        
        Args:
            max_emails: 最大处理邮件数
            batch_size: 每批邮件数量
            sender: 发件人邮箱地址
            folder: 邮箱文件夹名称，默认为"inbox"
            
        Yields:
            邮件ID列表的批次
        """
        # 确保连接有效
        self._ensure_connection()
        
        # 选择指定的文件夹
        self.mail.select(folder)
        
        try:
            # 搜索指定发件人的未读邮件
            status, messages = self.mail.search(None, f'FROM "{sender}" UNSEEN')
        except (imaplib.IMAP4.abort, imaplib.IMAP4.error) as e:
            # 处理IMAP服务器错误，包括服务器繁忙的情况
            error_msg = str(e).lower()
            if "busy" in error_msg or "unavailable" in error_msg:
                print(f"IMAP服务器繁忙或不可用: {e}")
                # 尝试重新连接
                print("尝试重新连接...")
                try:
                    self._ensure_connection()
                    # 重新选择文件夹
                    self.mail.select(folder)
                    # 再次尝试搜索
                    status, messages = self.mail.search(None, f'FROM "{sender}" UNSEEN')
                except (imaplib.IMAP4.abort, imaplib.IMAP4.error) as retry_e:
                    retry_error_msg = str(retry_e).lower()
                    if "busy" in retry_error_msg or "unavailable" in retry_error_msg:
                        print(f"重新连接后仍然无法访问服务器，等待一段时间后再次尝试: {retry_e}")
                        import time
                        time.sleep(5)  # 等待5秒
                        try:
                            self._ensure_connection()
                            self.mail.select(folder)
                            status, messages = self.mail.search(None, f'FROM "{sender}" UNSEEN')
                        except (imaplib.IMAP4.abort, imaplib.IMAP4.error) as final_e:
                            print(f"最终尝试仍然失败: {final_e}")
                            # 返回空列表而不是抛出异常
                            messages = [b'']
                    else:
                        # 其他错误重新抛出
                        raise
            else:
                # 重新抛出其他IMAP错误
                raise
        
        # 获取邮件ID列表
        email_ids = messages[0].split()
        
        # 清理邮件ID格式
        email_ids = [self._sanitize_email_id(eid) for eid in email_ids]
        
        # 按时间倒序排列（最新的邮件在前面）
        # 由于IMAP返回的ID列表已经是按时间顺序的，我们只需要反转它
        email_ids.reverse()
        
        # 确定要处理的邮件范围
        email_ids = email_ids[:max_emails] if len(email_ids) > max_emails else email_ids
        
        # 分批返回邮件ID
        for i in range(0, len(email_ids), batch_size):
            yield email_ids[i:i + batch_size]
    
    def close(self):
        """
        关闭邮箱连接
        """
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
            except (imaplib.IMAP4.abort, imaplib.IMAP4.error):
                # 如果连接已经断开，忽略错误
                pass
            finally:
                self.mail = None