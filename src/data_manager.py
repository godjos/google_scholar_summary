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
import os

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
                    relevance_score INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 检查relevance_score列是否存在(用于旧表迁移)
            cursor.execute("PRAGMA table_info(papers)")
            columns = [column[1] for column in cursor.fetchall()]
            if "relevance_score" not in columns:
                logger.info("Updating database schema: adding relevance_score column")
                cursor.execute("ALTER TABLE papers ADD COLUMN relevance_score INTEGER DEFAULT 0")
            
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
    
    def format_paper_data(self, paper: Dict) -> Dict:
        """
        格式化论文数据用于导出
        """
        highlights = paper.get("highlights", [])
        if isinstance(highlights, list):
            highlights_str = "; ".join(highlights)
        else:
            highlights_str = str(highlights)
            
        applications = paper.get("applications", [])
        if isinstance(applications, list):
            applications_str = "; ".join(applications)
        else:
            applications_str = str(applications)
            
        return {
            "Title": paper.get("title", ""),
            "Link": paper.get("link", ""),
            "Abstract": paper.get("abstract", ""),
            "Chinese Abstract": paper.get("chinese_abstract", ""),
            "Highlights": highlights_str,
            "Applications": applications_str,
            "Relevance Score": paper.get("relevance_score", 0),
            "Receive Time": paper.get("receive_time", ""),
            "Created At": paper.get("created_at", "")
        }

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
        检查论文是否已存在 (通过链接)
        
        Args:
            paper_link: 论文链接
            
        Returns:
            是否已存在
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM papers WHERE link = ?', (paper_link,))
            return cursor.fetchone() is not None

    def is_title_exists(self, title: str) -> bool:
        """
        检查论文标题是否已存在 (忽略大小写)
        
        Args:
            title: 论文标题
            
        Returns:
            是否已存在
        """
        if not title:
            return False
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 使用 LOWER() 函数进行不区分大小写的比较
            # 同时去除首尾空格
            clean_title = title.strip().lower()
            cursor.execute('SELECT 1 FROM papers WHERE LOWER(title) = ?', (clean_title,))
            return cursor.fetchone() is not None

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

    def remove_duplicate_titles(self):
        """
        删除数据库中重复标题的论文，保留相关度最高（或最新）的记录
        使用标准化标题（小写+去空格）进行比较
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                # 1. 查找重复的标题 (基于标准化后的标题分组)
                cursor.execute('''
                    SELECT LOWER(TRIM(title)), COUNT(*) 
                    FROM papers 
                    GROUP BY LOWER(TRIM(title)) 
                    HAVING COUNT(*) > 1
                ''')
                duplicate_groups = cursor.fetchall()
                
                if not duplicate_groups:
                    logger.info("未发现重复标题的论文")
                    return

                logger.info(f"发现 {len(duplicate_groups)} 组重复标题，开始清理...")
                deleted_count = 0
                
                for group_row in duplicate_groups:
                    normalized_title = group_row[0]
                    
                    # 获取该标准化标题的所有记录
                    cursor.execute('''
                        SELECT id, link, relevance_score, title 
                        FROM papers 
                        WHERE LOWER(TRIM(title)) = ? 
                        ORDER BY relevance_score DESC, created_at DESC
                    ''', (normalized_title,))
                    records = cursor.fetchall()
                    
                    if not records:
                        continue
                        
                    # 保留第一条（分数最高/最新的），删除其他的
                    keep_id = records[0][0]
                    keep_title = records[0][3]
                    to_delete = records[1:]
                    
                    # 如果有不同的大小写变体，记录一下我们保留了哪一个
                    if len(to_delete) > 0:
                         logger.debug(f"保留: '{keep_title}' (ID: {keep_id}), 删除 {len(to_delete)} 个副本")
                    
                    for row in to_delete:
                        del_id = row[0]
                        del_link = row[1]
                        
                        # 删除关联表中的记录
                        cursor.execute('DELETE FROM email_paper_relations WHERE paper_link = ?', (del_link,))
                        
                        # 删除论文记录
                        cursor.execute('DELETE FROM papers WHERE id = ?', (del_id,))
                        deleted_count += 1
                        
                conn.commit()
                logger.info(f"清理完成，共删除了 {deleted_count} 篇重复论文")
                
            except sqlite3.Error as e:
                logger.error(f"清理重复论文时出错: {e}")
                conn.rollback()

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
                title = paper.get("title", "")
                link = paper.get("link", "")
                
                # 检查论文链接是否已存在
                cursor.execute('SELECT 1 FROM papers WHERE link = ?', (link,))
                if cursor.fetchone():
                    return False

                # 检查论文标题是否已存在 (忽略大小写)
                cursor.execute('SELECT 1 FROM papers WHERE LOWER(title) = ?', (title.strip().lower(),))
                if cursor.fetchone():
                    logger.info(f"论文标题已存在(忽略大小写): {title[:50]}... 跳过保存")
                    # 如果标题存在，我们要确保新的链接(如果有的话)也不会被当作新论文处理
                    # 但在这里我们只是跳过保存，不建立email关联，或者建立?
                    # 按照用户要求: "对于数据库中存在的相同标题文章直接跳过"
                    return False
                    
                # 将列表转换为JSON字符串存储
                highlights = paper.get("highlights", [])
                applications = paper.get("applications", [])
                
                highlights_str = json.dumps(highlights) if isinstance(highlights, list) else str(highlights)
                applications_str = json.dumps(applications) if isinstance(applications, list) else str(applications)
                
                cursor.execute('''
                    INSERT OR IGNORE INTO papers 
                    (title, link, abstract, chinese_abstract, highlights, applications, relevance_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    title,
                    link,
                    paper.get("abstract", ""),
                    paper.get("chinese_abstract", ""),
                    highlights_str,
                    applications_str,
                    paper.get("relevance_score", 0)
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
                
                # 1. 预先获取已存在的链接
                existing_links = set()
                links = [p.get("link", "") for p in papers if p.get("link", "")]
                if links:
                    placeholders = ', '.join(['?'] * len(links))
                    cursor.execute(f'SELECT link FROM papers WHERE link IN ({placeholders})', links)
                    for row in cursor.fetchall():
                        existing_links.add(row[0])

                # 2. 预先获取已存在的标题 (构建标准化标题集合)
                existing_normalized_titles = set()
                titles = [p.get("title", "") for p in papers if p.get("title", "")]
                if titles:
                    # 我们需要检查数据库中所有与这批标题"相似"的标题
                    # 最简单的方法是 fetch all titles that match lower(...)
                    # 但为了效率，我们可以只查出所有存在的 title，或者逐个查?
                    # 考虑到批量可能只有几篇，逐个查或者 `LOWER(title) IN (...)` 是可行的
                    # SQLite 的 LOWER(title) IN (...) 可能无法利用索引，但标题列通常没有索引?
                    # 这里的优化策略：先查出所有相关的，或者这里直接用循环检查算了，反正批量不大
                    
                    # 更好：使用 set 存储所有标准化后的标题
                    # 如果数据量大，这不高效。但考虑到每次批量只有 5-10 篇，我们可以接受?
                    # 或者：SELECT LOWER(title) FROM papers WHERE LOWER(title) IN (lower(t1), lower(t2)...)
                    
                    lower_titles = [t.strip().lower() for t in titles]
                    placeholders = ', '.join(['?'] * len(lower_titles))
                    cursor.execute(f'SELECT LOWER(title) FROM papers WHERE LOWER(title) IN ({placeholders})', lower_titles)
                    for row in cursor.fetchall():
                        existing_normalized_titles.add(row[0])
                
                for paper in papers:
                    link = paper.get("link", "")
                    title = paper.get("title", "")
                    normalized_title = title.strip().lower()
                    
                    # 检查论文链接是否已存在
                    if link in existing_links:
                        continue
                        
                    # 检查标题是否已存在 (忽略大小写)
                    if normalized_title in existing_normalized_titles:
                        continue
                    
                    # 将列表转换为JSON字符串存储
                    highlights = paper.get("highlights", [])
                    applications = paper.get("applications", [])
                    
                    highlights_str = json.dumps(highlights) if isinstance(highlights, list) else str(highlights)
                    applications_str = json.dumps(applications) if isinstance(applications, list) else str(applications)
                    
                    cursor.execute('''
                        INSERT OR IGNORE INTO papers 
                        (title, link, abstract, chinese_abstract, highlights, applications, relevance_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        title,
                        link,
                        paper.get("abstract", ""),
                        paper.get("chinese_abstract", ""),
                        highlights_str,
                        applications_str,
                        paper.get("relevance_score", 0)
                    ))
                    
                    if cursor.rowcount > 0:
                        saved_count += 1
                        existing_links.add(link)
                        existing_normalized_titles.add(normalized_title) # 防止同一批次中有重复标题
                
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
            # 按相关度降序，然后按收件时间降序 (用户要求的"收集时间")
            # 使用 GROUP BY p.id 避免因关联多封邮件而导致重复出现
            cursor.execute('''
                SELECT p.title, p.link, p.abstract, p.chinese_abstract, p.highlights, p.applications, MAX(pe.receive_time), p.created_at, p.relevance_score
                FROM papers p
                LEFT JOIN email_paper_relations epr ON p.link = epr.paper_link
                LEFT JOIN processed_emails pe ON epr.email_id = pe.email_id
                GROUP BY p.id
                ORDER BY p.relevance_score DESC, MAX(pe.receive_time) DESC
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
                "receive_time": row[6] if row[6] else "",
                "created_at": row[7] if row[7] else "",
                "relevance_score": row[8] if row[8] is not None else 0
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
        格式化论文数据用于导出
        """
        highlights = paper.get("highlights", [])
        if isinstance(highlights, list):
            highlights_str = "; ".join(highlights)
        else:
            highlights_str = str(highlights)
            
        applications = paper.get("applications", [])
        if isinstance(applications, list):
            applications_str = "; ".join(applications)
        else:
            applications_str = str(applications)
            
        return {
            "Title": paper.get("title", ""),
            "Link": paper.get("link", ""),
            "Abstract": paper.get("abstract", ""),
            "Chinese Abstract": paper.get("chinese_abstract", ""),
            "Highlights": highlights_str,
            "Applications": applications_str,
            "Relevance Score": paper.get("relevance_score", 0),
            "Receive Time": paper.get("receive_time", ""),
            "Created At": paper.get("created_at", "")
        }

    def save_to_html(self, papers: List[Dict], filename: str = "scholar_results.html"):
        """
        将论文信息保存到HTML文件（静态分页模式）
        解决单文件过大无法打开的问题。
        结构：
        - reports/index.html (第1页 + Dashboard)
        - reports/page_2.html (第2页)
        - reports/page_3.html (第3页)
        ...
        """
        try:
            # 总是从数据库获取所有论文
            all_papers = self.get_all_papers_with_receive_time()
            
            if not all_papers:
                logger.warning("没有论文数据可保存到HTML文件")
                return
            
            # 计算统计数据 (只在首页显示或计算一次)
            stats = self._calculate_stats(all_papers)
            
            total_papers = len(all_papers)
            page_size = 50
            total_pages = (total_papers + page_size - 1) // page_size
            
            # 确保目录存在
            output_dir = os.path.dirname(filename)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                logger.info(f"创建输出目录: {output_dir}")
                
            # 清理旧的分页文件 (可选，防止混淆)
            # ...

            logger.info(f"开始生成静态分页HTML报告，共 {total_papers} 篇论文，分 {total_pages} 页...")
            
            base_name = os.path.basename(filename) # index.html
            
            for page in range(1, total_pages + 1):
                start_idx = (page - 1) * page_size
                end_idx = min(start_idx + page_size, total_papers)
                page_papers = all_papers[start_idx:end_idx]
                
                # 确定当页文件名
                if page == 1:
                    current_filename = filename
                else:
                    current_filename = os.path.join(output_dir, f"page_{page}.html")
                
                # 生成页面内容
                html_content = self._generate_html_content(
                    papers=page_papers,
                    stats=stats,
                    current_page=page,
                    total_pages=total_pages,
                    total_papers=total_papers
                )
                
                with open(current_filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                    
            logger.info(f"成功生成分页报告，主文件: {filename}, 共 {total_pages} 页")
            
        except Exception as e:
            logger.error(f"保存HTML文件时出错: {e}")
            import traceback
            traceback.print_exc()

    def _calculate_stats(self, papers: List[Dict]) -> Dict:
        """计算Dashboard统计数据"""
        total = len(papers)
        total_score = sum(p.get("relevance_score", 0) for p in papers)
        avg_score = round(total_score / total, 1) if total > 0 else 0
        high_rel = sum(1 for p in papers if p.get("relevance_score", 0) >= 8)
        
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        recent = sum(1 for p in papers if p.get("receive_time", "").startswith(today))
        
        # 分布
        dist = {"high": 0, "med": 0, "low": 0}
        for p in papers:
            s = p.get("relevance_score", 0)
            if s >= 8: dist["high"] += 1
            elif s >= 4: dist["med"] += 1
            else: dist["low"] += 1
            
        # 趋势 (最近14天)
        date_counts = {}
        for p in papers:
            rt = p.get("receive_time", "")
            if rt:
                d = rt.split(' ')[0]
                date_counts[d] = date_counts.get(d, 0) + 1
        
        sorted_dates = sorted(date_counts.keys())[-14:]
        trend = {"labels": sorted_dates, "data": [date_counts[d] for d in sorted_dates]}
        
        return {
            "total": total,
            "avg_score": avg_score,
            "high_rel": high_rel,
            "recent": recent,
            "distribution": dist,
            "trend": trend
        }

    def _generate_html_content(self, papers: List[Dict], stats: Dict, current_page: int, total_pages: int, total_papers: int) -> str:
        """
        生成静态页面HTML内容 (Server-Side Rendering)
        """
        
        # 1. 生成 Dashboard HTML (仅在第一页显示，或者折叠显示)
        dashboard_html = ""
        if current_page == 1:
            dashboard_html = f"""
            <div class="dashboard">
                <div class="chart-card">
                    <div class="chart-title">📊 关键指标</div>
                    <div class="stats-grid">
                        <div class="stat-item"><div class="stat-value">{stats['total']}</div><div class="stat-label">总论文数</div></div>
                        <div class="stat-item"><div class="stat-value">{stats['avg_score']}</div><div class="stat-label">平均相关度</div></div>
                        <div class="stat-item"><div class="stat-value">{stats['high_rel']}</div><div class="stat-label">强相关(8+)</div></div>
                        <div class="stat-item"><div class="stat-value">{stats['recent']}</div><div class="stat-label">今日新增</div></div>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-title">🎯 相关度分布</div>
                    <canvas id="scoreChart"></canvas>
                </div>
                <div class="chart-card" style="grid-column: span 1 / -1;">
                    <div class="chart-title">📅 每日收录趋势</div>
                    <canvas id="trendChart" height="80"></canvas>
                </div>
            </div>
            """
        
        # 2. 生成论文列表 HTML
        papers_html = ""
        for paper in papers:
            score = paper.get("relevance_score", 0)
            rel_class = 'low-relevance'
            if score >= 8: rel_class = 'high-relevance'
            elif score >= 4: rel_class = 'medium-relevance'
            
            highlights = paper.get("highlights", [])
            hl_html = "".join([f'<span class="tag">{h}</span>' for h in highlights]) if isinstance(highlights, list) else ""
            
            applications = paper.get("applications", [])
            app_html = "".join([f'<span class="tag app">{a}</span>' for a in applications]) if isinstance(applications, list) else ""
            
            chinese_abstract = ""
            if paper.get("chinese_abstract"):
                chinese_abstract = f'<div class="chinese-abstract"><strong>摘要:</strong> {paper.get("chinese_abstract")}</div>'
            
            papers_html += f"""
            <div class="paper-card {rel_class}">
                <div class="paper-header">
                    <h2 class="paper-title"><a href="{paper.get("link", "")}" target="_blank">{paper.get("title", "")}</a></h2>
                    <span class="relevance-badge">评分: {score}</span>
                </div>
                <div class="paper-meta">
                    <span>📅 {paper.get("receive_time", "未知")}</span>
                    <span>📝 {paper.get("created_at", "未知")}</span>
                </div>
                {chinese_abstract}
                <div class="tags">{hl_html}</div>
                <div class="tags" style="margin-top:5px">{app_html}</div>
                <details style="margin-top:10px; color:var(--text-secondary); font-size:13px;">
                    <summary>原始摘要</summary>
                    <p>{paper.get("abstract", "")}</p>
                </details>
            </div>
            """

        # 3. 生成分页导航 HTML
        pagination_html = '<div class="pagination">'
        
        # 上一页
        if current_page > 1:
            prev_link = "index.html" if current_page == 2 else f"page_{current_page-1}.html"
            pagination_html += f'<a href="{prev_link}" class="page-link">上一页</a>'
        else:
            pagination_html += '<span class="page-link disabled">上一页</span>'
            
        # 简单的页码显示 (优化：只显示周围的页码)
        start_p = max(1, current_page - 2)
        end_p = min(total_pages, current_page + 2)
        
        if start_p > 1:
            pagination_html += '<a href="index.html" class="page-link">1</a>'
            if start_p > 2: pagination_html += '<span class="page-sep">...</span>'
            
        for p in range(start_p, end_p + 1):
            if p == current_page:
                pagination_html += f'<span class="page-link active">{p}</span>'
            else:
                link = "index.html" if p == 1 else f"page_{p}.html"
                pagination_html += f'<a href="{link}" class="page-link">{p}</a>'
                
        if end_p < total_pages:
            if end_p < total_pages - 1: pagination_html += '<span class="page-sep">...</span>'
            pagination_html += f'<a href="page_{total_pages}.html" class="page-link">{total_pages}</a>'
            
        # 下一页
        if current_page < total_pages:
            pagination_html += f'<a href="page_{current_page+1}.html" class="page-link">下一页</a>'
        else:
             pagination_html += '<span class="page-link disabled">下一页</span>'
             
        pagination_html += f'<span style="margin-left:15px; color:#5f6368;">共 {total_papers} 篇</span></div>'

        # 4. 注入 Chart.js 数据脚本 (仅第一页需要)
        chart_script = ""
        if current_page == 1:
            chart_script = f"""
            <script>
                document.addEventListener('DOMContentLoaded', () => {{
                    const stats = {json.dumps(stats, ensure_ascii=False)};
                    
                    new Chart(document.getElementById('scoreChart'), {{
                        type: 'doughnut',
                        data: {{
                            labels: ['强相关', '中等', '弱相关'],
                            datasets: [{{ 
                                data: [stats.distribution.high, stats.distribution.med, stats.distribution.low], 
                                backgroundColor: ['#ea4335', '#fbbc04', '#dadce0'] 
                            }}]
                        }},
                        options: {{ responsive: true, plugins: {{ legend: {{ position: 'right' }} }} }}
                    }});
                    
                    new Chart(document.getElementById('trendChart'), {{
                        type: 'bar',
                        data: {{
                            labels: stats.trend.labels,
                            datasets: [{{ 
                                label: '收录数量', 
                                data: stats.trend.data, 
                                backgroundColor: '#4285f4', 
                                borderRadius: 4 
                            }}]
                        }},
                        options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true }} }} }}
                    }});
                }});
            </script>
            """

        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google Scholar 汇总 - 第 {current_page} 页</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{ --primary-color: #4285f4; --secondary-color: #34a853; --bg-color: #f8f9fa; --card-bg: #ffffff; --text-primary: #202124; --text-secondary: #5f6368; --border-color: #dadce0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; background-color: var(--bg-color); color: var(--text-primary); margin: 0; padding: 0; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        header {{ background-color: var(--card-bg); padding: 15px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); position: sticky; top: 0; z-index: 100; margin-bottom: 20px; }}
        .header-content {{ max-width: 1400px; margin: 0 auto; padding: 0 20px; display: flex; justify-content: space-between; align-items: center; }}
        h1 {{ margin: 0; color: var(--primary-color); font-size: 22px; }}
        
        .dashboard {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .chart-card {{ background: var(--card-bg); padding: 20px; border-radius: 8px; box-shadow: 0 1px 2px rgba(60,64,67,0.3); }}
        .chart-title {{ font-size: 16px; font-weight: 600; margin-bottom: 15px; color: var(--text-secondary); }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }}
        .stat-item {{ text-align: center; padding: 10px; background: #f1f3f4; border-radius: 8px; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: var(--primary-color); }}
        .stat-label {{ font-size: 12px; color: var(--text-secondary); }}

        .paper-list {{ display: flex; flex-direction: column; gap: 20px; }}
        .paper-card {{ background-color: var(--card-bg); border-radius: 8px; padding: 20px; box-shadow: 0 1px 2px rgba(60,64,67,0.3); border-left: 5px solid transparent; }}
        .paper-card.high-relevance {{ border-left-color: #ea4335; }}
        .paper-card.medium-relevance {{ border-left-color: #fbbc04; }}
        .paper-card.low-relevance {{ border-left-color: #dadce0; }}
        .paper-header {{ display: flex; justify-content: space-between; align-items: flex-start; }}
        .paper-title {{ margin: 0 0 10px 0; font-size: 18px; color: var(--primary-color); }}
        .paper-title a {{ text-decoration: none; color: inherit; }}
        .paper-title a:hover {{ text-decoration: underline; }}
        .relevance-badge {{ padding: 2px 8px; border-radius: 12px; font-weight: bold; font-size: 12px; background: #f1f3f4; float: right; }}
        .high-relevance .relevance-badge {{ background-color: #fce8e6; color: #c5221f; }}
        .medium-relevance .relevance-badge {{ background-color: #fef7e0; color: #b06000; }}
        .paper-meta {{ font-size: 12px; color: var(--text-secondary); margin-bottom: 10px; display: flex; gap: 15px; }}
        .chinese-abstract {{ background-color: #f8f9fa; padding: 10px; margin: 10px 0; border-left: 4px solid var(--secondary-color); font-size: 14px; }}
        .tags {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 5px; }}
        .tag {{ font-size: 12px; padding: 3px 10px; border-radius: 12px; background-color: #e8f0fe; color: #1967d2; }}
        .tag.app {{ background-color: #e6f4ea; color: #137333; }}

        .pagination {{ display: flex; justify-content: center; align-items: center; padding: 30px 0; gap: 5px; }}
        .page-link {{ padding: 8px 12px; border: 1px solid var(--border-color); background: var(--card-bg); border-radius: 4px; text-decoration: none; color: var(--text-primary); }}
        .page-link:hover {{ background: #f1f3f4; }}
        .page-link.active {{ background: var(--primary-color); color: white; border-color: var(--primary-color); }}
        .page-link.disabled {{ color: var(--text-secondary); cursor: not-allowed; background: #f1f3f4; }}
    </style>
</head>
<body>

<header>
    <div class="header-content">
        <h1>Google Scholar Summary <small>第 {current_page} 页</small></h1>
        <div style="font-size: 14px; color: var(--text-secondary);">共 {total_papers} 篇</div>
    </div>
</header>

<div class="container">
    {dashboard_html}
    
    <div class="paper-list">
        {papers_html}
    </div>
    
    {pagination_html}
</div>

{chart_script}

</body>
</html>
"""
