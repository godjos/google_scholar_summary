#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据管理模块
负责处理和存储数据
"""

import pandas as pd
import sqlite3
from typing import List, Dict, Optional, ContextManager
import json
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DataManager:
    """
    数据管理器类
    """
    
    def __init__(self, database_path: str = "scholar_data.db"):
        """
        初始化数据管理器
        
        Args:
            database_path: SQLite数据库路径
        """
        self.database_path = database_path
        self.init_database()
    
    def init_database(self):
        """
        初始化数据库表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建已处理邮件表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_emails (
                    email_id TEXT PRIMARY KEY,
                    receive_time TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建论文信息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    link TEXT UNIQUE,
                    abstract TEXT,
                    chinese_abstract TEXT,
                    highlights TEXT,
                    applications TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建邮件与论文关联表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_paper_relations (
                    email_id TEXT,
                    paper_link TEXT,
                    FOREIGN KEY (email_id) REFERENCES processed_emails (email_id),
                    FOREIGN KEY (paper_link) REFERENCES papers (link),
                    PRIMARY KEY (email_id, paper_link)
                )
            ''')
            
            conn.commit()
    
    def _get_connection(self) -> ContextManager[sqlite3.Connection]:
        """
        获取数据库连接的上下文管理器
        
        Returns:
            数据库连接上下文管理器
        """
        return sqlite3.connect(self.database_path)
    
    def is_email_processed(self, email_id: str) -> bool:
        """
        检查邮件是否已处理
        
        Args:
            email_id: 邮件ID
            
        Returns:
            是否已处理
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT 1 FROM processed_emails WHERE email_id = ?', (email_id,))
            result = cursor.fetchone()
            
            return result is not None
    
    def mark_email_processed(self, email_id: str, receive_time: str = ""):
        """
        标记邮件为已处理
        
        Args:
            email_id: 邮件ID
            receive_time: 邮件接收时间
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                'INSERT OR IGNORE INTO processed_emails (email_id, receive_time) VALUES (?, ?)', 
                (email_id, receive_time)
            )
            
            conn.commit()
    
    def is_paper_exists(self, paper_link: str) -> bool:
        """
        检查论文是否已存在
        
        Args:
            paper_link: 论文链接
            
        Returns:
            是否已存在
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT 1 FROM papers WHERE link = ?', (paper_link,))
            result = cursor.fetchone()
            
            return result is not None
    
    def create_email_paper_relation(self, email_id: str, paper_link: str):
        """
        创建邮件与论文的关联关系
        
        Args:
            email_id: 邮件ID
            paper_link: 论文链接
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                'INSERT OR IGNORE INTO email_paper_relations (email_id, paper_link) VALUES (?, ?)',
                (email_id, paper_link)
            )
            
            conn.commit()
    
    def save_paper(self, paper: Dict) -> bool:
        """
        保存单篇论文到数据库
        
        Args:
            paper: 论文信息
            
        Returns:
            是否保存成功
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # 检查论文是否已存在
                cursor.execute('SELECT 1 FROM papers WHERE link = ?', (paper.get("link", ""),))
                if cursor.fetchone():
                    return False
                    
                # 将列表转换为JSON字符串存储
                highlights = paper.get("highlights", [])
                applications = paper.get("applications", [])
                
                highlights_str = json.dumps(highlights) if isinstance(highlights, list) else str(highlights)
                applications_str = json.dumps(applications) if isinstance(applications, list) else str(applications)
                
                cursor.execute('''
                    INSERT OR IGNORE INTO papers 
                    (title, link, abstract, chinese_abstract, highlights, applications)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    paper.get("title", ""),
                    paper.get("link", ""),
                    paper.get("abstract", ""),
                    paper.get("chinese_abstract", ""),
                    highlights_str,
                    applications_str
                ))
                
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.Error as e:
                logger.error(f"保存论文时出错: {e}")
                return False
    
    def save_papers_batch(self, papers: List[Dict]):
        """
        批量保存论文到数据库
        
        Args:
            papers: 论文信息列表
        """
        if not papers:
            return
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # 使用事务批量插入
                saved_count = 0
                
                # 先获取所有已存在的论文链接
                existing_links = set()
                if papers:
                    links = [paper.get("link", "") for paper in papers if paper.get("link", "")]
                    if links:
                        placeholders = ', '.join(['?'] * len(links))
                        cursor.execute(f'SELECT link FROM papers WHERE link IN ({placeholders})', links)
                        for row in cursor.fetchall():
                            existing_links.add(row[0])
                
                for paper in papers:
                    link = paper.get("link", "")
                    # 检查论文是否已存在
                    if link in existing_links:
                        continue
                    
                    # 将列表转换为JSON字符串存储
                    highlights = paper.get("highlights", [])
                    applications = paper.get("applications", [])
                    
                    highlights_str = json.dumps(highlights) if isinstance(highlights, list) else str(highlights)
                    applications_str = json.dumps(applications) if isinstance(applications, list) else str(applications)
                    
                    cursor.execute('''
                        INSERT OR IGNORE INTO papers 
                        (title, link, abstract, chinese_abstract, highlights, applications)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        paper.get("title", ""),
                        link,
                        paper.get("abstract", ""),
                        paper.get("chinese_abstract", ""),
                        highlights_str,
                        applications_str
                    ))
                    
                    if cursor.rowcount > 0:
                        saved_count += 1
                        existing_links.add(link)  # 添加到已存在集合，避免重复检查
                
                conn.commit()
                logger.info(f"成功批量保存 {saved_count} 篇新论文（跳过 {len(papers) - saved_count} 篇已存在的论文）")
            except sqlite3.Error as e:
                logger.error(f"批量保存论文时出错: {e}")
                conn.rollback()
    
    def get_all_papers_with_receive_time(self) -> List[Dict]:
        """
        从数据库获取所有论文及接收时间
        
        Returns:
            论文信息列表（包含接收时间）
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 查询论文信息及关联的邮件接收时间
            cursor.execute('''
                SELECT p.title, p.link, p.abstract, p.chinese_abstract, p.highlights, p.applications, pe.receive_time
                FROM papers p
                LEFT JOIN email_paper_relations epr ON p.link = epr.paper_link
                LEFT JOIN processed_emails pe ON epr.email_id = pe.email_id
                ORDER BY p.created_at DESC
            ''')
            
            rows = cursor.fetchall()
        
        papers = []
        for row in rows:
            # 将JSON字符串转换回列表
            try:
                highlights = json.loads(row[4]) if row[4] else []
            except json.JSONDecodeError:
                highlights = []
                
            try:
                applications = json.loads(row[5]) if row[5] else []
            except json.JSONDecodeError:
                applications = []
            
            paper = {
                "title": row[0],
                "link": row[1],
                "abstract": row[2],
                "chinese_abstract": row[3],
                "highlights": highlights,
                "applications": applications,
                "receive_time": row[6] if row[6] else ""
            }
            papers.append(paper)
        
        return papers
    
    def save_to_csv(self, papers: List[Dict], filename: str = "scholar_results.csv"):
        """
        将论文信息保存到CSV文件
        
        Args:
            papers: 论文信息列表（此参数将被忽略）
            filename: 保存的文件名
        """
        try:
            # 总是从数据库获取所有论文，确保CSV文件与数据库同步
            all_papers = self.get_all_papers_with_receive_time()
            
            if not all_papers:
                logger.warning("没有论文数据可保存到CSV文件")
                return
            
            # 格式化每篇论文的数据
            formatted_papers = [self.format_paper_data(paper) for paper in all_papers]
            
            # 转换为DataFrame
            df = pd.DataFrame(formatted_papers)
            
            # 保存为CSV文件（覆盖模式）
            df.to_csv(filename, index=False, encoding="utf-8-sig")
            logger.info(f"成功将 {len(all_papers)} 篇论文保存到CSV文件: {filename}")
        except Exception as e:
            logger.error(f"保存CSV文件时出错: {e}")
    
    def save_to_excel(self, papers: List[Dict], filename: str = "scholar_results.xlsx"):
        """
        将论文信息保存到Excel文件
        
        Args:
            papers: 论文信息列表（此参数将被忽略）
            filename: 保存的文件名
        """
        try:
            # 总是从数据库获取所有论文，确保Excel文件与数据库同步
            all_papers = self.get_all_papers_with_receive_time()
            
            if not all_papers:
                logger.warning("没有论文数据可保存到Excel文件")
                return
            
            # 格式化每篇论文的数据
            formatted_papers = [self.format_paper_data(paper) for paper in all_papers]
            
            # 转换为DataFrame
            df = pd.DataFrame(formatted_papers)
            
            # 保存为Excel文件
            df.to_excel(filename, index=False)
            logger.info(f"成功将 {len(all_papers)} 篇论文保存到Excel文件: {filename}")
        except Exception as e:
            logger.error(f"保存Excel文件时出错: {e}")
    
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
            "应用领域": applications_str,
            "收件时间": paper.get("receive_time", "")
        }
        return formatted