#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Google Scholar 邮件通知处理器
该脚本连接到QQ邮箱，获取Google Scholar Alerts邮件，
并使用大模型API对论文进行分析和摘要。
"""

import imaplib
import email
from email.header import decode_header
import re
import json
import pandas as pd
import requests
import os
from typing import List, Dict


class ScholarAlertProcessor:
    def __init__(self, email_address: str, auth_code: str, llm_api_key: str):
        """
        初始化处理器
        
        Args:
            email_address: QQ邮箱地址
            auth_code: QQ邮箱授权码
            llm_api_key: 大模型API密钥
        """
        self.email_address = email_address
        self.auth_code = auth_code
        self.llm_api_key = llm_api_key
        self.mail = None

    def connect_to_email(self):
        """
        连接到QQ邮箱IMAP服务器
        """
        # 连接到QQ邮箱的IMAP服务器
        self.mail = imaplib.IMAP4_SSL("imap.qq.com")
        # 登录
        self.mail.login(self.email_address, self.auth_code)
        print("成功连接到QQ邮箱")

    def search_scholar_emails(self, max_emails: int = 10) -> List[str]:
        """
        搜索Google Scholar Alerts邮件
        
        Args:
            max_emails: 最大处理邮件数
            
        Returns:
            邮件ID列表
        """
        # 选择收件箱
        self.mail.select("inbox")
        
        # 搜索发件人为scholaralerts-noreply@google.com的邮件
        status, messages = self.mail.search(None, 'FROM "scholaralerts-noreply@google.com"')
        
        # 获取邮件ID列表
        email_ids = messages[0].split()
        
        # 返回最新的几封邮件
        return email_ids[-max_emails:] if len(email_ids) > max_emails else email_ids

    def parse_email_content(self, email_id: str) -> List[Dict[str, str]]:
        """
        解析邮件内容，提取论文信息
        
        Args:
            email_id: 邮件ID
            
        Returns:
            论文信息列表，每个元素包含标题、链接和摘要
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
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()
        
        # 提取论文信息
        papers = self._extract_paper_info(body)
        return papers

    def _extract_paper_info(self, body: str) -> List[Dict[str, str]]:
        """
        从邮件正文中提取论文信息
        
        Args:
            body: 邮件正文
            
        Returns:
            论文信息列表
        """
        # 这里需要根据实际邮件格式编写正则表达式
        # 示例格式，需要根据实际情况调整
        papers = []
        
        # 示例正则表达式，需要根据实际邮件内容调整
        # 假设邮件格式包含标题和摘要信息
        pattern = r"Title: (.*?)\nLink: (.*?)\nAbstract: (.*?)\n\n"
        matches = re.findall(pattern, body, re.DOTALL)
        
        for match in matches:
            papers.append({
                "title": match[0].strip(),
                "link": match[1].strip(),
                "abstract": match[2].strip()
            })
        
        return papers

    def get_summary_from_llm(self, title: str, abstract: str) -> Dict:
        """
        调用大模型API生成论文摘要
        
        Args:
            title: 论文标题
            abstract: 论文摘要
            
        Returns:
            大模型返回的分析结果
        """
        # 示例使用OpenAI API
        prompt = f"""
        请根据以下信息，为我生成一篇论文的中文摘要、研究亮点（3-5点）和潜在应用领域：

        标题：{title}
        摘要：{abstract}

        请以JSON格式返回，格式如下：
        {{
            "chinese_abstract": "中文摘要",
            "highlights": ["亮点1", "亮点2", "亮点3"],
            "applications": ["应用领域1", "应用领域2"]
        }}
        """
        
        # 这里是示例，实际使用时需要根据具体的API进行调整
        headers = {
            "Authorization": f"Bearer {self.llm_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        
        # 注释掉实际请求，避免在没有API密钥时出错
        # response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
        # return response.json()
        
        # 模拟返回结果
        return {
            "chinese_abstract": "这是中文摘要示例",
            "highlights": ["亮点1", "亮点2", "亮点3"],
            "applications": ["应用领域1", "应用领域2"]
        }

    def process_emails(self, max_emails: int = 10) -> List[Dict]:
        """
        处理邮件并生成论文分析结果
        
        Args:
            max_emails: 最大处理邮件数
            
        Returns:
            所有论文的分析结果
        """
        # 连接邮箱
        self.connect_to_email()
        
        # 搜索邮件
        email_ids = self.search_scholar_emails(max_emails)
        
        all_papers = []
        
        # 处理每封邮件
        for email_id in email_ids:
            print(f"正在处理邮件 ID: {email_id}")
            papers = self.parse_email_content(email_id)
            
            # 处理每篇论文
            for paper in papers:
                print(f"正在分析论文: {paper['title'][:50]}...")
                # 调用大模型API获取分析结果
                llm_result = self.get_summary_from_llm(paper['title'], paper['abstract'])
                
                # 合并原始信息和分析结果
                paper.update(llm_result)
                all_papers.append(paper)
        
        return all_papers

    def save_results(self, papers: List[Dict], filename: str = "scholar_results.csv"):
        """
        将结果保存到CSV文件
        
        Args:
            papers: 论文信息列表
            filename: 保存的文件名
        """
        # 转换为DataFrame
        df = pd.DataFrame(papers)
        
        # 保存为CSV文件
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"结果已保存到 {filename}")

    def close_connection(self):
        """
        关闭邮箱连接
        """
        if self.mail:
            self.mail.close()
            self.mail.logout()
            print("邮箱连接已关闭")


def main():
    """
    主函数
    """
    # 配置信息（实际使用时应从环境变量或配置文件中读取）
    EMAIL_ADDRESS = os.getenv("QQ_EMAIL_ADDRESS", "your_email@qq.com")
    AUTH_CODE = os.getenv("QQ_EMAIL_AUTH_CODE", "your_auth_code")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "your_api_key")
    
    # 创建处理器实例
    processor = ScholarAlertProcessor(EMAIL_ADDRESS, AUTH_CODE, LLM_API_KEY)
    
    try:
        # 处理邮件
        papers = processor.process_emails(max_emails=5)
        
        # 保存结果
        processor.save_results(papers, "scholar_alerts_analysis.csv")
        
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
    
    finally:
        # 关闭连接
        processor.close_connection()


if __name__ == "__main__":
    main()