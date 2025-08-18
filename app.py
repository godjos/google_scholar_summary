#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Google Scholar 邮件通知处理器
主程序入口
"""

import sys
import os

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.config import Config
from src.email_client import EmailClient
from src.paper_parser import PaperParser
from src.llm_client import LLMClient
from src.data_manager import DataManager


def main():
    """
    主函数
    """
    # 加载配置
    config_obj = Config()
    
    # 创建邮箱客户端实例
    email_client_obj = EmailClient(
        config_obj.email_address, 
        config_obj.auth_code
    )
    
    # 创建论文解析器实例
    paper_parser_obj = PaperParser()
    
    # 创建大模型客户端实例
    llm_client_obj = LLMClient(config_obj.llm_api_key)
    
    # 创建数据管理器实例
    data_manager_obj = DataManager()
    
    try:
        # 连接邮箱
        print("正在连接邮箱...")
        email_client_obj.connect()
        
        # 搜索Google Scholar邮件
        print("正在搜索Google Scholar邮件...")
        email_ids = email_client_obj.search_scholar_emails(config_obj.max_emails)
        print(f"找到 {len(email_ids)} 封邮件")
        
        all_papers = []
        
        # 处理每封邮件
        for email_id in email_ids:
            print(f"正在处理邮件 ID: {email_id}")
            # 获取邮件内容
            email_content = email_client_obj.get_email_content(email_id)
            
            # 解析邮件中的论文信息
            papers = paper_parser_obj.extract_paper_info(email_content)
            print(f"从邮件中提取到 {len(papers)} 篇论文")
            
            # 处理每篇论文
            for paper in papers:
                print(f"正在分析论文: {paper['title'][:50]}...")
                # 调用大模型API获取分析结果
                llm_result = llm_client_obj.get_paper_analysis(
                    paper['title'], 
                    paper['abstract']
                )
                
                # 合并原始信息和分析结果
                paper.update(llm_result)
                all_papers.append(paper)
        
        # 保存结果
        print(f"总共处理了 {len(all_papers)} 篇论文")
        data_manager_obj.save_to_csv(all_papers, config_obj.output_file)
        print(f"结果已保存到 {config_obj.output_file}")
        
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
    
    finally:
        # 关闭邮箱连接
        email_client_obj.close()
        print("邮箱连接已关闭")


if __name__ == "__main__":
    main()