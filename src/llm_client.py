#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
大模型客户端模块
负责调用大模型API进行论文分析
"""

import json
import time
from typing import Dict
from openai import OpenAI, APIError, RateLimitError, APIConnectionError
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('llm_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class LLMClient:
    """
    大模型客户端类
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", 
                 model: str = "gpt-3.5-turbo"):
        """
        初始化大模型客户端
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"大模型客户端初始化成功，使用模型: {model}")
        except Exception as e:
            logger.error(f"大模型客户端初始化失败: {e}")
            raise
    
    def get_paper_analysis(self, title: str, abstract: str, link: str = "") -> Dict:
        """
        调用大模型API生成论文分析
        
        Args:
            title: 论文标题
            abstract: 论文摘要
            link: 论文链接
            
        Returns:
            大模型返回的分析结果
        """
        # 构建提示词
        prompt = f"""
        你的任务是根据提供的论文信息，生成一篇论文的中文摘要、研究亮点（3 - 5点）和潜在应用领域。以下是相关信息：
        <标题>{title}</标题>
        <链接>{link}</链接>
        <英文摘要>{abstract}</英文摘要>

        在生成中文摘要时，需要准确翻译英文摘要的内容，确保语言通顺、表意清晰。
        对于研究亮点，从英文摘要中提取论文的核心创新点、重要发现或独特贡献，整理成3 - 5条简洁明了的表述。
        在确定潜在应用领域时，根据论文的研究内容和成果，分析其可能产生实际作用的领域。
        请严格按照以下JSON格式返回结果，不要包含其他内容：
        {{
            "chinese_abstract": "中文摘要",
            "highlights": ["亮点1", "亮点2", "亮点3"],
            "applications": ["应用领域1", "应用领域2"]
        }}
        """
        
        max_retries = 3
        retry_delay = 1  # 初始重试延迟（秒）
        
        for attempt in range(max_retries):
            try:
                logger.info(f"正在调用大模型API分析论文: {title[:50]}... (第 {attempt + 1} 次尝试)")
                # 使用OpenAI客户端发送请求
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    timeout=30  # 添加超时设置
                )
                
                # 获取响应内容
                content = response.choices[0].message.content
                logger.info(f"成功获取大模型响应，正在解析结果...")
                
                try:
                    # 尝试解析返回的JSON内容
                    # 首先尝试直接解析
                    result = json.loads(content)
                    logger.info("成功解析大模型返回的JSON结果")
                    return result
                except json.JSONDecodeError:
                    # 如果直接解析失败，尝试提取代码块中的JSON
                    try:
                        # 查找代码块标记
                        start_marker = "```json"
                        end_marker = "```"
                        
                        start_idx = content.find(start_marker)
                        if start_idx != -1:
                            start_idx += len(start_marker)
                            end_idx = content.find(end_marker, start_idx)
                            if end_idx != -1:
                                json_str = content[start_idx:end_idx].strip()
                                result = json.loads(json_str)
                                logger.info("成功从代码块中提取并解析JSON结果")
                                return result
                    except json.JSONDecodeError:
                        pass
                    
                    # 如果所有解析都失败，返回默认值
                    logger.warning("无法解析大模型返回的结果，使用默认值")
                    return self._get_default_result(title)
                    
            except RateLimitError as e:
                # 处理限流错误
                if attempt < max_retries - 1:  # 不是最后一次尝试
                    wait_time = retry_delay * (2 ** attempt)  # 指数退避
                    logger.warning(f"遇到API限流错误，{wait_time}秒后进行第{attempt + 1}次重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"API限流错误，已达到最大重试次数: {e}")
                    return self._get_default_result(title)
                    
            except APIConnectionError as e:
                # 处理连接错误
                if attempt < max_retries - 1:  # 不是最后一次尝试
                    wait_time = retry_delay * (2 ** attempt)  # 指数退避
                    logger.warning(f"遇到API连接错误，{wait_time}秒后进行第{attempt + 1}次重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"API连接错误，已达到最大重试次数: {e}")
                    return self._get_default_result(title)
                    
            except APIError as e:
                # 处理其他API错误
                if attempt < max_retries - 1:  # 不是最后一次尝试
                    wait_time = retry_delay * (2 ** attempt)  # 指数退避
                    logger.warning(f"遇到API错误，{wait_time}秒后进行第{attempt + 1}次重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"API错误，已达到最大重试次数: {e}")
                    return self._get_default_result(title)
                    
            except Exception as e:
                # 处理其他未预期的错误
                logger.error(f"调用大模型API时发生未预期错误: {e}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(f"{wait_time}秒后进行第{attempt + 1}次重试...")
                    time.sleep(wait_time)
                else:
                    return self._get_default_result(title)
        
        # 所有重试都失败后返回默认值
        logger.error("所有重试都失败，返回默认值")
        return self._get_default_result(title)
    
    def _get_default_result(self, title: str) -> Dict:
        """
        获取默认的分析结果
        
        Args:
            title: 论文标题
            
        Returns:
            默认分析结果
        """
        return {
            "chinese_abstract": f"这是论文《{title}》的中文摘要示例",
            "highlights": ["亮点1", "亮点2", "亮点3"],
            "applications": ["应用领域1", "应用领域2"]
        }
    
    def set_model(self, model_name: str):
        """
        设置使用的大模型
        
        Args:
            model_name: 模型名称
        """
        self.model = model_name
        logger.info(f"已更新大模型为: {model_name}")
    
    def test_api_connection(self):
        """
        测试大模型API连接是否正常
        
        Returns:
            bool: API连接是否正常
        """
        try:
            logger.info("正在测试大模型API连接...")
            # 发送一个简单的测试请求
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "测试API连接"}],
                temperature=0.7,
                timeout=10
            )
            logger.info("大模型API连接测试成功")
            return True
        except Exception as e:
            logger.error(f"大模型API连接测试失败: {e}")
            return False