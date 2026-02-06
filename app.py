#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Google Scholar 邮件通知处理器
主程序入口
"""

import sys
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import cycle

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.config import Config
from src.email_client import EmailClient
from src.paper_parser import PaperParser
from src.llm_client import LLMClient
from src.data_manager import DataManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def analyze_paper_with_client(llm_client, paper):
    """
    使用指定的LLM客户端分析论文
    
    Args:
        llm_client: LLM客户端实例
        paper: 论文信息字典
        
    Returns:
        分析结果
    """
    try:
        logger.info(f"正在使用API密钥分析论文: {paper['title'][:50]}...")
        llm_result = llm_client.get_paper_analysis(
            paper['title'], 
            paper['abstract'],
            paper['link']
        )
        return llm_result
    except Exception as e:
        logger.error(f"使用API密钥分析论文 '{paper['title'][:50]}...' 时出错: {e}")
        return None


def analyze_paper_parallel(llm_clients, paper):
    """
    使用多个LLM客户端并行分析论文
    
    Args:
        llm_clients: LLM客户端实例列表
        paper: 论文信息字典
        
    Returns:
        分析结果
    """
    if not llm_clients:
        return None
        
    # 如果只有一个客户端，直接使用
    if len(llm_clients) == 1:
        return analyze_paper_with_client(llm_clients[0], paper)
    
    # 使用线程池并行处理
    with ThreadPoolExecutor(max_workers=len(llm_clients)) as executor:
        # 提交所有任务
        future_to_client = {
            executor.submit(analyze_paper_with_client, client, paper): client 
            for client in llm_clients
        }
        
        # 返回第一个成功的任务结果
        for future in as_completed(future_to_client):
            result = future.result()
            if result is not None:
                return result
    
    # 如果所有客户端都失败，返回默认值
    return {
        "chinese_abstract": f"这是论文《{paper['title']}》的中文摘要示例",
        "highlights": ["亮点1", "亮点2", "亮点3"],
        "applications": ["应用领域1", "应用领域2"]
    }


def process_paper_with_llm(paper, email_id, receive_time, llm_client, data_manager):
    """
    使用LLM处理单篇论文
    
    Args:
        paper: 论文信息字典
        email_id: 邮件ID
        receive_time: 邮件接收时间
        llm_client: LLM客户端实例
        data_manager: 数据管理器实例
        
    Returns:
        处理结果（是否成功）
    """
    # 添加接收时间到论文信息中
    paper["receive_time"] = receive_time
    
    # 检查论文是否已存在
    if data_manager.is_paper_exists(paper['link']):
        logger.info(f"论文 '{paper['title'][:50]}...' 已存在，跳过...")
        # 仍然创建邮件与论文的关联
        data_manager.create_email_paper_relation(email_id, paper['link'])
        return False
    
    # 分析论文
    llm_result = analyze_paper_with_client(llm_client, paper)
    
    if llm_result is not None:
        # 合并原始信息和分析结果
        paper.update(llm_result)
    else:
        # 使用默认值
        paper.update({
            "chinese_abstract": "",
            "highlights": [],
            "applications": []
        })
    
    # 保存到数据库
    if data_manager.save_paper(paper):
        # 创建邮件与论文的关联
        data_manager.create_email_paper_relation(email_id, paper['link'])
        return True
    else:
        logger.warning(f"论文 '{paper['title'][:50]}...' 保存失败或已存在")
        return False


def process_paper_without_llm(paper, email_id, receive_time, data_manager):
    """
    不使用LLM处理单篇论文
    
    Args:
        paper: 论文信息字典
        email_id: 邮件ID
        receive_time: 邮件接收时间
        data_manager: 数据管理器实例
        
    Returns:
        处理结果（是否成功）
    """
    # 添加接收时间到论文信息中
    paper["receive_time"] = receive_time
    
    # 检查论文是否已存在
    if data_manager.is_paper_exists(paper['link']):
        logger.info(f"论文 '{paper['title'][:50]}...' 已存在，跳过...")
        # 仍然创建邮件与论文的关联
        data_manager.create_email_paper_relation(email_id, paper['link'])
        return False
    
    # 不使用大模型时，添加默认值
    paper.update({
        "chinese_abstract": "",
        "highlights": [],
        "applications": []
    })
    logger.info(f"收集论文信息: {paper['title'][:50]}...")
    
    # 保存到数据库
    if data_manager.save_paper(paper):
        # 创建邮件与论文的关联
        data_manager.create_email_paper_relation(email_id, paper['link'])
        return True
    else:
        logger.warning(f"论文 '{paper['title'][:50]}...' 保存失败或已存在")
        return False


def process_email(email_id, email_client, paper_parser, data_manager, config, llm_clients):
    """
    处理单封邮件
    
    Args:
        email_id: 邮件ID
        email_client: 邮箱客户端实例
        paper_parser: 论文解析器实例
        data_manager: 数据管理器实例
        config: 配置对象
        llm_clients: LLM客户端实例列表
        
    Returns:
        tuple: (新增论文数量, 处理的论文列表)
    """
    # 检查邮件是否已处理
    if data_manager.is_email_processed(email_id):
        logger.info(f"邮件 ID {email_id} 已处理过，跳过...")
        # 即使邮件已处理，也将其标记为已读
        if email_client.mark_email_as_read(email_id, config.email_folder):
            logger.info(f"邮件 {email_id} 已标记为已读")
        else:
            logger.warning(f"无法将邮件 {email_id} 标记为已读")
        return 0, []
        
    logger.info(f"正在处理邮件 ID: {email_id}")
    try:
        # 一次性获取邮件内容和接收时间
        email_info = email_client.get_email_info(email_id)
        email_content = email_info["content"]
        receive_time = email_info["receive_time"]
        logger.info(f"邮件接收时间: {receive_time}")
    except Exception as e:
        logger.error(f"获取邮件 {email_id} 信息失败: {e}")
        return 0, []
    
    # 解析邮件中的论文信息
    papers = paper_parser.extract_paper_info(email_content)
    logger.info(f"从邮件中提取到 {len(papers)} 篇论文")
    
    # 初始化新增论文计数器
    new_papers_count = 0
    processed_papers = []
    
    # 处理每篇论文
    if config.use_llm and llm_clients:
        # 如果启用了LLM且有API密钥
        logger.info(f"顺序处理 {len(papers)} 篇论文...")
        
        # 创建API密钥循环迭代器
        api_cycle = cycle(llm_clients)
        
        for paper in papers:
            # 分配API密钥
            client = next(api_cycle)
            try:
                # 顺序处理
                result = process_paper_with_llm(
                    paper, 
                    email_id, 
                    receive_time, 
                    client, 
                    data_manager
                )
                if result:
                    new_papers_count += 1
                    processed_papers.append(paper)
            except Exception as e:
                logger.error(f"处理论文 '{paper['title'][:50]}...' 时出错: {e}")
                
    else:
        # 不使用大模型时，顺序处理论文
        for paper in papers:
            if process_paper_without_llm(paper, email_id, receive_time, data_manager):
                new_papers_count += 1
                processed_papers.append(paper)
    
    # 标记邮件为已处理（即使其中没有新论文）
    data_manager.mark_email_processed(email_id, receive_time)
    # 标记邮件为已读
    if email_client.mark_email_as_read(email_id, config.email_folder):
        logger.info(f"邮件 {email_id} 已标记为已读")
    else:
        logger.warning(f"无法将邮件 {email_id} 标记为已读")
    
    logger.info(f"从邮件 {email_id} 中新增 {new_papers_count} 篇论文")
    return new_papers_count, processed_papers


def main():
    """
    主函数
    """
    # 加载配置
    config = Config()
    
    # 创建邮箱客户端实例
    email_client = EmailClient(
        config.email_address, 
        config.auth_code,
        config.imap_server,
        config.imap_port
    )
    
    # 创建论文解析器实例
    paper_parser = PaperParser()
    
    # 根据配置决定是否创建大模型客户端实例
    llm_clients = []
    if config.use_llm:
        for api_key in config.llm_api_keys:
            llm_client = LLMClient(
                api_key,
                config.llm_api_base_url,
                config.llm_model_name
            )
            llm_clients.append(llm_client)
        logger.info(f"大模型处理已启用，已加载 {len(llm_clients)} 个API密钥")
        
        # 跳过耗时的API连接测试，直接开始处理
        # 如果密钥无效，将在实际处理时报错
        if not llm_clients:
             logger.error("未找到有效的API密钥，请检查配置")
             sys.exit(1)
        
    else:
        logger.info("大模型处理已禁用，仅收集论文基本信息")
    
    # 创建数据管理器实例
    data_manager = DataManager(config.database_path)
    
    # 启动时清理重复标题的论文
    logger.info("正在检查并清理数据库中的重复标题论文...")
    data_manager.remove_duplicate_titles()
    
    try:
        # 连接邮箱
        logger.info("正在连接邮箱...")
        email_client.connect()
        
        # 检查配置的邮箱文件夹是否存在
        logger.info(f"正在检查邮箱文件夹 '{config.email_folder}' 是否存在...")
        folder_exists = email_client.check_folder_exists(config.email_folder)
        if not folder_exists:
            logger.warning(f"配置的邮箱文件夹 '{config.email_folder}' 不存在，将使用默认文件夹 'inbox'")
            # 更新配置为默认文件夹
            config.email_folder = "inbox"
            logger.info("已切换到默认文件夹 'inbox'")
        
        # 初始化统计信息
        total_processed_emails = 0
        total_new_papers = 0
        all_processed_papers = []  # 仅存储当前会话处理的论文
        
        logger.info("开始流式处理邮件...")
        
        # 使用流式处理方式分批处理邮件
        batch_count = 0
        for email_batch in email_client.get_emails_batch(
            max_emails=config.max_emails, 
            batch_size=5,  # 每批处理5封邮件
            sender=config.scholar_sender, 
            folder=config.email_folder
        ):
            batch_count += 1
            logger.info(f"正在处理第 {batch_count} 批邮件，本批包含 {len(email_batch)} 封邮件")
            
            # 初始化每批邮件新增论文计数器
            batch_new_papers = 0
            
            # 处理每封邮件
            for email_id in email_batch:
                new_papers, processed_papers = process_email(
                    email_id, 
                    email_client, 
                    paper_parser, 
                    data_manager, 
                    config, 
                    llm_clients
                )
                batch_new_papers += new_papers
                total_new_papers += new_papers
                all_processed_papers.extend(processed_papers)
                total_processed_emails += 1
            
            # 每处理完一批邮件就保存一次CSV文件，确保文件与数据库同步
            if batch_new_papers > 0:  # 只有当有新论文时才保存
                logger.info(f"已处理完第 {batch_count} 批邮件，正在保存数据...")
                data_manager.save_to_csv([], config.output_file)  # 传入空列表，让方法从数据库读取所有数据
                # 同时保存HTML报告 (保存到 reports 文件夹)
                html_filename = 'index.html'
                html_path = os.path.join('reports', html_filename)
                data_manager.save_to_html([], html_path)
                logger.info(f"结果已保存到 {config.output_file} 和 {html_path}")
        
        # 最终总结
        logger.info("\n处理完成!")
        logger.info(f"总共处理了 {total_processed_emails} 封邮件")
        logger.info(f"本次新增 {total_new_papers} 篇论文")
        if all_processed_papers:
            logger.info(f"当前会话处理了 {len(all_processed_papers)} 篇新论文")
        else:
            logger.info("没有新的论文需要处理")
            
        # 始终重新生成HTML报告，以确保包含最新的排序和格式更新
        logger.info("正在生成最新的HTML报告...")
        html_filename = 'index.html'
        html_path = os.path.join('reports', html_filename)
        data_manager.save_to_html([], html_path)
        logger.info(f"HTML报告已生成: {html_path}")
        
    except Exception as e:
        logger.error(f"处理过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 关闭邮箱连接
        try:
            email_client.close()
            logger.info("邮箱连接已关闭")
        except Exception as e:
            logger.error(f"关闭邮箱连接时出现错误: {e}")


if __name__ == "__main__":
    main()