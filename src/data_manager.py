#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据管理模块
负责处理和存储数据
"""

import pandas as pd
from typing import List, Dict


class DataManager:
    """
    数据管理器类
    """
    
    def __init__(self):
        """
        初始化数据管理器
        """
        pass
    
    def save_to_csv(self, papers: List[Dict], filename: str = "scholar_results.csv"):
        """
        将论文信息保存到CSV文件
        
        Args:
            papers: 论文信息列表
            filename: 保存的文件名
        """
        # 格式化每篇论文的数据
        formatted_papers = [self.format_paper_data(paper) for paper in papers]
        
        # 转换为DataFrame
        df = pd.DataFrame(formatted_papers)
        
        # 保存为CSV文件
        df.to_csv(filename, index=False, encoding="utf-8-sig")
    
    def save_to_excel(self, papers: List[Dict], filename: str = "scholar_results.xlsx"):
        """
        将论文信息保存到Excel文件
        
        Args:
            papers: 论文信息列表
            filename: 保存的文件名
        """
        # 格式化每篇论文的数据
        formatted_papers = [self.format_paper_data(paper) for paper in papers]
        
        # 转换为DataFrame
        df = pd.DataFrame(formatted_papers)
        
        # 保存为Excel文件
        df.to_excel(filename, index=False)
    
    def format_paper_data(self, paper: Dict) -> Dict:
        """
        格式化单篇论文数据
        
        Args:
            paper: 论文信息字典
            
        Returns:
            格式化后的论文信息
        """
        # 处理研究亮点列表
        highlights = paper.get("highlights", [])
        if isinstance(highlights, list):
            highlights_str = ", ".join(highlights)
        else:
            highlights_str = str(highlights)
            
        # 处理应用领域列表
        applications = paper.get("applications", [])
        if isinstance(applications, list):
            applications_str = ", ".join(applications)
        else:
            applications_str = str(applications)
            
        formatted = {
            "标题": paper.get("title", ""),
            "链接": paper.get("link", ""),
            "原始摘要": paper.get("abstract", ""),
            "中文摘要": paper.get("chinese_abstract", ""),
            "研究亮点": highlights_str,
            "应用领域": applications_str
        }
        return formatted