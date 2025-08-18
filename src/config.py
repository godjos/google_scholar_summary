#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置管理模块
用于加载和管理应用程序配置
"""

import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


class Config:
    """
    配置管理类
    """
    
    def __init__(self):
        """
        初始化配置
        """
        # 邮箱配置
        self.email_address = os.getenv("QQ_EMAIL_ADDRESS", "your_email@qq.com")
        self.auth_code = os.getenv("QQ_EMAIL_AUTH_CODE", "your_auth_code")
        
        # 大模型API配置
        self.llm_api_key = os.getenv("LLM_API_KEY", "your_api_key")
        
        # 其他配置
        self.max_emails = int(os.getenv("MAX_EMAILS", "10"))
        self.output_file = os.getenv("OUTPUT_FILE", "scholar_results.csv")
        
        # IMAP服务器配置
        self.imap_server = "imap.qq.com"
        self.imap_port = 993
        
        # Google Scholar发件人
        self.scholar_sender = "scholaralerts-noreply@google.com"