#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
论文解析模块
负责从邮件内容中提取论文信息
"""

import re
from typing import List, Dict
from html import unescape
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('paper_parser.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PaperParser:
    """
    论文解析器类
    """
    
    def __init__(self):
        """
        初始化论文解析器
        """
        pass
    
    def extract_paper_info(self, email_body: str) -> List[Dict[str, str]]:
        """
        从邮件正文中提取论文信息
        
        Args:
            email_body: 邮件正文
            
        Returns:
            论文信息列表，每个元素包含标题、链接和摘要
        """
        try:
            logger.info("开始解析邮件中的论文信息...")
            # 首先尝试解析HTML格式
            papers = self._parse_html_format(email_body)
            
            if papers:
                logger.info(f"成功解析到 {len(papers)} 篇论文")
            else:
                logger.warning("未解析到任何论文信息")
            
            return papers
        except Exception as e:
            logger.error(f"解析邮件内容时出错: {e}")
            return []
    
    def _parse_html_format(self, email_body: str) -> List[Dict[str, str]]:
        """
        解析HTML格式的Google Scholar邮件
        
        Args:
            email_body: HTML格式的邮件正文
            
        Returns:
            论文信息列表
        """
        papers = []
        
        # 匹配每篇论文的模式
        # 匹配论文链接和标题（更健壮的模式）
        title_pattern = r'<a href="([^"]+)"[^>]*class="gse_alrt_title"[^>]*>(.*?)</a>'
        # 匹配作者和来源信息
        author_pattern = r'<div style="color:#006621;line-height:18px">(.*?)</div>'
        # 匹配摘要信息（更健壮的模式）
        abstract_pattern = r'<div[^>]*class="gse_alrt_sni"[^>]*>(.*?)</div>'
        
        # 找到所有论文标题和链接
        titles = re.findall(title_pattern, email_body, re.DOTALL)
        authors = re.findall(author_pattern, email_body, re.DOTALL)
        abstracts = re.findall(abstract_pattern, email_body, re.DOTALL)
        
        logger.info(f"找到 {len(titles)} 个标题链接, {len(authors)} 个作者信息, {len(abstracts)} 个摘要")
        
        # 组合信息
        for i in range(len(titles)):
            try:
                # 清理标题中的HTML标签和实体
                clean_title = re.sub(r'<[^>]+>', '', titles[i][1]).strip()
                clean_title = unescape(clean_title)
                
                # 提取真实的论文链接
                real_link = titles[i][0]
                # 检查是否是Google Scholar的跳转链接
                if 'scholar.google.com/scholar_url?url=' in real_link:
                    # 从跳转链接中提取真实的URL
                    url_match = re.search(r'url=([^&]+)', real_link)
                    if url_match:
                        real_link = unescape(url_match.group(1))
                        logger.info(f"从Google Scholar跳转链接中提取真实链接: {real_link[:100]}...")
                
                # 清理摘要中的HTML标签和实体
                clean_abstract = ""
                if i < len(abstracts):
                    clean_abstract = re.sub(r'<[^>]+>', ' ', abstracts[i]).strip()
                    clean_abstract = re.sub(r'\s+', ' ', clean_abstract)  # 合并多个空格
                    clean_abstract = unescape(clean_abstract)
                
                # 验证提取的信息
                if clean_title and real_link:
                    papers.append({
                        "title": clean_title,
                        "link": real_link,
                        "abstract": clean_abstract
                    })
                    logger.info(f"成功解析论文: {clean_title[:50]}...")
                else:
                    logger.warning(f"跳过无效论文信息: 标题={clean_title[:50]}..., 链接={real_link[:50]}...")
            except Exception as e:
                logger.error(f"解析第 {i+1} 篇论文时出错: {e}")
                continue
        
        return papers
    
    def parse_email_body(self, raw_body: str) -> str:
        """
        解析原始邮件内容，提取纯文本正文
        
        Args:
            raw_body: 原始邮件内容
            
        Returns:
            纯文本正文
        """
        try:
            # 移除HTML标签
            text_body = re.sub(r'<[^>]+>', ' ', raw_body)
            # 合并多个空格
            text_body = re.sub(r'\s+', ' ', text_body).strip()
            # 解码HTML实体
            text_body = unescape(text_body)
            logger.info(f"成功提取纯文本正文，长度: {len(text_body)} 字符")
            return text_body
        except Exception as e:
            logger.error(f"提取纯文本正文时出错: {e}")
            return raw_body