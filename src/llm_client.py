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
    
    def __init__(self, api_key: str):
        """
        初始化大模型客户端
        
        Args:
            api_key: API密钥
        """
        self.api_key = api_key
        self.model = "gpt-3.5-turbo"
    
    def get_paper_analysis(self, title: str, abstract: str) -> Dict:
        """
        调用大模型API生成论文分析
        
        Args:
            title: 论文标题
            abstract: 论文摘要
            
        Returns:
            大模型返回的分析结果
        """
        # 构建提示词
        prompt = f"""
        请根据以下信息，为我生成一篇论文的中文摘要、研究亮点（3-5点）和潜在应用领域：

        标题：{title}
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
        
        # 发送请求（注释掉实际请求以避免在没有API密钥时出错）
        # response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
        # result = response.json()
        
        # 模拟返回结果
        # 在实际使用中，需要取消注释上面的代码并移除下面的模拟代码
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