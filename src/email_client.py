#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
邮箱客户端模块
负责连接邮箱、搜索和获取邮件内容
"""

import imaplib
import email
from typing import List


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
    
    def search_scholar_emails(self, max_emails: int = 10, sender: str = "scholaralerts-noreply@google.com") -> List[str]:
        """
        搜索Google Scholar Alerts邮件
        
        Args:
            max_emails: 最大处理邮件数
            sender: 发件人邮箱地址
            
        Returns:
            邮件ID列表
        """
        # 选择收件箱
        self.mail.select("inbox")
        
        # 搜索指定发件人的邮件
        status, messages = self.mail.search(None, f'FROM "{sender}"')
        
        # 获取邮件ID列表
        email_ids = messages[0].split()
        
        # 返回最新的几封邮件
        return email_ids[-max_emails:] if len(email_ids) > max_emails else email_ids
    
    def get_email_content(self, email_id: str) -> str:
        """
        获取邮件内容
        
        Args:
            email_id: 邮件ID
            
        Returns:
            邮件正文内容
        """
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
    
    def close(self):
        """
        关闭邮箱连接
        """
        if self.mail:
            self.mail.close()
            self.mail.logout()