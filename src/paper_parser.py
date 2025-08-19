#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
论文解析模块
负责从邮件内容中提取论文信息
"""

import re
from typing import List, Dict
from html import unescape


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
        # 这里需要根据实际邮件格式编写正则表达式
        # 以下是一个示例格式，需要根据实际情况调整
        papers = self._parse_html_format(email_body)
        
        return papers
    
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
        # 匹配论文链接和标题
        title_pattern = r'<a href="([^"]+)" class="gse_alrt_title"[^>]*>(.*?)</a>'
        # 匹配作者和来源信息
        author_pattern = r'<div style="color:#006621;line-height:18px">(.*?)</div>'
        # 匹配摘要信息
        abstract_pattern = r'<div class="gse_alrt_sni"[^>]*>(.*?)</div>'
        
        # 找到所有论文标题和链接
        titles = re.findall(title_pattern, email_body, re.DOTALL)
        authors = re.findall(author_pattern, email_body, re.DOTALL)
        abstracts = re.findall(abstract_pattern, email_body, re.DOTALL)
        
        # 组合信息
        for i in range(len(titles)):
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
            
            # 清理摘要中的HTML标签和实体
            clean_abstract = ""
            if i < len(abstracts):
                clean_abstract = re.sub(r'<[^>]+>', ' ', abstracts[i]).strip()
                clean_abstract = re.sub(r'\s+', ' ', clean_abstract)  # 合并多个空格
                clean_abstract = unescape(clean_abstract)
            
            papers.append({
                "title": clean_title,
                "link": real_link,
                "abstract": clean_abstract
            })
        
        return papers
    
    def parse_email_body(self, raw_body: str) -> str:
        """
        解析原始邮件内容，提取纯文本正文
        
        Args:
            raw_body: 原始邮件内容
            
        Returns:
            纯文本正文
        """
        # 如果需要处理HTML格式的邮件，可以在这里添加处理逻辑
        return raw_body