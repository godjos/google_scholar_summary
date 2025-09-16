#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
大模型客户端模块
负责调用大模型API进行论文分析
"""

import json
from typing import Dict
from openai import OpenAI, APIError


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
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
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
        {
            "chinese_abstract": "中文摘要",
            "highlights": ["亮点1", "亮点2", "亮点3"],
            "applications": ["应用领域1", "应用领域2"]
        }
        """
        
        try:
            # 使用OpenAI客户端发送请求
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            # 获取响应内容
            content = response.choices[0].message.content
            
            try:
                # 尝试解析返回的JSON内容
                # 首先尝试直接解析
                return json.loads(content)
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
                            return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
                
                # 如果所有解析都失败，返回默认值
                return {
                    "chinese_abstract": f"这是论文《{title}》的中文摘要示例",
                    "highlights": ["亮点1", "亮点2", "亮点3"],
                    "applications": ["应用领域1", "应用领域2"]
                }
                
        except APIError as e:
            # 出错时返回默认值
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