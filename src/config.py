#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置管理模块
用于加载和管理应用程序配置
"""

import os
from dotenv import load_dotenv
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('config.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
        
        # 大模型API配置 - 支持多个API密钥
        llm_api_keys = os.getenv("LLM_API_KEY", "your_api_key")
        # 同时支持逗号和空格分隔的API密钥
        import re
        self.llm_api_keys = [key.strip() for key in re.split(r'[,\s]+', llm_api_keys) if key.strip()]
        self.llm_api_base_url = os.getenv("LLM_API_BASE_URL", "https://api.openai.com/v1")
        self.llm_model_name = os.getenv("LLM_MODEL_NAME", "gpt-3.5-turbo")
        
        # 其他配置
        self.max_emails = int(os.getenv("MAX_EMAILS", "10"))
        self.output_file = os.getenv("OUTPUT_FILE", "scholar_results.csv")
        
        # 是否使用大模型处理
        self.use_llm = os.getenv("USE_LLM", "true").lower() == "true"
        
        # IMAP服务器配置
        self.imap_server = os.getenv("IMAP_SERVER", "imap.qq.com")
        self.imap_port = int(os.getenv("IMAP_PORT", "993"))
        
        # Google Scholar发件人
        self.scholar_sender = os.getenv("SCHOLAR_SENDER", "scholaralerts-noreply@google.com")
        
        # 邮箱文件夹配置
        self.email_folder = os.getenv("EMAIL_FOLDER", "inbox")
        
        # 数据库配置
        self.database_path = os.getenv("DATABASE_PATH", "scholar_data.db")
        
        # 线程池配置
        self.max_workers = int(os.getenv("MAX_WORKERS", "5"))
        
        # 超时配置
        self.email_timeout = int(os.getenv("EMAIL_TIMEOUT", "30"))
        self.llm_timeout = int(os.getenv("LLM_TIMEOUT", "30"))
        
        # 验证配置
        self.validate_config()
    
    def validate_config(self):
        """
        验证配置的有效性
        """
        logger.info("正在验证配置...")
        
        # 验证邮箱配置
        if self.email_address == "your_email@qq.com":
            logger.warning("邮箱地址未配置，使用默认值")
        
        if self.auth_code == "your_auth_code":
            logger.warning("邮箱授权码未配置，使用默认值")
        
        # 验证大模型配置
        if self.use_llm:
            if not self.llm_api_keys or any(key == "your_api_key" for key in self.llm_api_keys):
                logger.warning("大模型API密钥未配置或使用默认值，大模型功能可能无法正常工作")
            else:
                logger.info(f"已配置 {len(self.llm_api_keys)} 个大模型API密钥")
        
        # 验证其他配置
        if self.max_emails <= 0:
            logger.warning("最大邮件数配置无效，设置为默认值10")
            self.max_emails = 10
        
        if self.max_workers <= 0:
            logger.warning("最大工作线程数配置无效，设置为默认值5")
            self.max_workers = 5
        
        logger.info("配置验证完成")
    
    def get_config_summary(self):
        """
        获取配置摘要
        
        Returns:
            配置摘要字典
        """
        return {
            "email_address": self.email_address,
            "use_llm": self.use_llm,
            "llm_api_keys_count": len(self.llm_api_keys),
            "llm_model_name": self.llm_model_name,
            "max_emails": self.max_emails,
            "output_file": self.output_file,
            "imap_server": self.imap_server,
            "scholar_sender": self.scholar_sender,
            "database_path": self.database_path,
            "max_workers": self.max_workers
        }