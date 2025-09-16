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
    
    # 根据配置决定是否创建大模型客户端实例
    llm_client_obj = None
    if config_obj.use_llm:
        llm_client_obj = LLMClient(
            config_obj.llm_api_key,
            config_obj.llm_api_base_url,
            config_obj.llm_model_name
        )
        print("大模型处理已启用")
    else:
        print("大模型处理已禁用，仅收集论文基本信息")
    
    # 创建数据管理器实例
    data_manager_obj = DataManager(config_obj.database_path)
    
    try:
        # 连接邮箱
        print("正在连接邮箱...")
        email_client_obj.connect()
        
        # 初始化统计信息
        total_processed_emails = 0
        total_new_papers = 0
        all_papers = []  # 仅存储当前会话处理的论文
        
        print("开始流式处理邮件...")
        
        # 使用流式处理方式分批处理邮件
        batch_count = 0
        for email_batch in email_client_obj.get_emails_batch(
            max_emails=config_obj.max_emails, 
            batch_size=5,  # 每批处理5封邮件
            sender=config_obj.scholar_sender, 
            folder=config_obj.email_folder
        ):
            batch_count += 1
            print(f"正在处理第 {batch_count} 批邮件，本批包含 {len(email_batch)} 封邮件")
            
            # 处理每封邮件
            for email_id in email_batch:
                # 检查邮件是否已处理
                if data_manager_obj.is_email_processed(email_id):
                    print(f"  邮件 ID {email_id} 已处理过，跳过...")
                    continue
                    
                print(f"  正在处理邮件 ID: {email_id}")
                try:
                    # 一次性获取邮件内容和接收时间
                    email_info = email_client_obj.get_email_info(email_id)
                    email_content = email_info["content"]
                    receive_time = email_info["receive_time"]
                    print(f"  邮件接收时间: {receive_time}")
                except Exception as e:
                    print(f"  获取邮件 {email_id} 信息失败: {e}")
                    continue
                
                # 解析邮件中的论文信息
                papers = paper_parser_obj.extract_paper_info(email_content)
                print(f"  从邮件中提取到 {len(papers)} 篇论文")
                
                # 处理每篇论文
                new_papers_in_email = 0
                for paper in papers:
                    # 添加接收时间到论文信息中
                    paper["receive_time"] = receive_time
                    
                    # 检查论文是否已存在
                    if data_manager_obj.is_paper_exists(paper['link']):
                        print(f"    论文 '{paper['title'][:50]}...' 已存在，跳过...")
                        # 仍然创建邮件与论文的关联
                        data_manager_obj.create_email_paper_relation(email_id, paper['link'])
                        continue
                        
                    # 根据配置决定是否使用大模型处理
                    if config_obj.use_llm and llm_client_obj:
                        print(f"    正在分析论文: {paper['title'][:50]}...")
                        try:
                            # 调用大模型API获取分析结果
                            llm_result = llm_client_obj.get_paper_analysis(
                                paper['title'], 
                                paper['abstract'],
                                paper['link']
                            )
                            
                            # 合并原始信息和分析结果
                            paper.update(llm_result)
                        except Exception as e:
                            print(f"    分析论文 '{paper['title'][:50]}...' 时出错: {e}")
                            # 使用默认值继续处理
                            paper.update({
                                "chinese_abstract": "",
                                "highlights": [],
                                "applications": []
                            })
                    else:
                        # 不使用大模型时，添加默认值
                        paper.update({
                            "chinese_abstract": "",
                            "highlights": [],
                            "applications": []
                        })
                        print(f"    收集论文信息: {paper['title'][:50]}...")
                    
                    # 保存到数据库
                    if data_manager_obj.save_paper(paper):
                        total_new_papers += 1
                        new_papers_in_email += 1
                        
                        # 创建邮件与论文的关联
                        data_manager_obj.create_email_paper_relation(email_id, paper['link'])
                        
                        # 添加到当前会话处理的论文列表
                        all_papers.append(paper)
                    else:
                        print(f"    论文 '{paper['title'][:50]}...' 保存失败或已存在")
                
                # 标记邮件为已处理（即使其中没有新论文）
                data_manager_obj.mark_email_processed(email_id, receive_time)
                total_processed_emails += 1
                
                print(f"  从邮件 {email_id} 中新增 {new_papers_in_email} 篇论文")
            
            # 每处理完一批邮件就保存一次CSV文件，确保文件与数据库同步
            if new_papers_in_email > 0:  # 只有当有新论文时才保存
                print(f"  已处理完第 {batch_count} 批邮件，正在保存数据...")
                data_manager_obj.save_to_csv([], config_obj.output_file)  # 传入空列表，让方法从数据库读取所有数据
                print(f"  结果已保存到 {config_obj.output_file}")
        
        # 最终总结
        print("\n处理完成!")
        print(f"总共处理了 {total_processed_emails} 封邮件")
        print(f"本次新增 {total_new_papers} 篇论文")
        if all_papers:
            print(f"当前会话处理了 {len(all_papers)} 篇新论文")
        else:
            print("没有新的论文需要处理")
        
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 关闭邮箱连接
        try:
            email_client_obj.close()
            print("邮箱连接已关闭")
        except Exception as e:
            print(f"关闭邮箱连接时出现错误: {e}")


if __name__ == "__main__":
    main()