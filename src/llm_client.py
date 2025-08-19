#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
大模型客户端模块
负责调用大模型API进行论文分析
"""

import json
import requests
from typing import Dict


class LLMClient:
    """
    大模型客户端类
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", 
                 model: str = "gpt-3.5-turbo", api_path: str = "v1/chat/completions"):
        """
        初始化大模型客户端
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
            api_path: API路径
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.api_path = api_path
    
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
        请根据以下信息，为我生成一篇论文的中文摘要、研究亮点（3-5点）和潜在应用领域：

        标题：{title}
        链接：{link}
        摘要：{abstract}

        请严格按照以下JSON格式返回，不要包含其他内容：
        {{
            "chinese_abstract": "中文摘要",
            "highlights": ["亮点1", "亮点2", "亮点3"],
            "applications": ["应用领域1", "应用领域2"]
        }}
        """
        
        # 构建请求头
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建请求数据
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        
        # 发送请求
        response = requests.post(f"{self.base_url}/{self.api_path}", headers=headers, json=data)
        result = response.json()
        
        # 如果请求成功，返回结果
        if response.status_code == 200 and "choices" in result:
            content = result["choices"][0]["message"]["content"]
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # 如果解析失败，返回原始内容
                return {
                    "chinese_abstract": content,
                    "highlights": [],
                    "applications": []
                }
        else:
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