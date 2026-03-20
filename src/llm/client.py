"""
硅基流动API客户端

封装对SiliconFlow API的调用
"""

import os
import json
import requests
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class SiliconFlowClient:
    """
    硅基流动API客户端
    
    支持DeepSeek-V3等模型，用于自然语言理解任务
    """
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        初始化客户端
        
        Args:
            api_key: API密钥，默认从环境变量读取
            model: 模型名称，默认从环境变量读取
        """
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY")
        self.api_url = os.getenv("SILICONFLOW_API_URL", "https://api.siliconflow.cn/v1/chat/completions")
        self.model = model or os.getenv("SILICONFLOW_MODEL", "deepseek-ai/DeepSeek-V3")
        
        if not self.api_key:
            raise ValueError("API密钥未设置，请设置SILICONFLOW_API_KEY环境变量")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        response_format: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        调用对话补全API
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            temperature: 温度参数，控制随机性（0-2）
            max_tokens: 最大生成token数
            response_format: 响应格式，如 {"type": "json_object"}
        
        Returns:
            API响应结果
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if response_format:
            payload["response_format"] = response_format
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"API调用失败: {str(e)}")
    
    def extract_json_from_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        从API响应中提取JSON内容
        
        Args:
            response: API原始响应
        
        Returns:
            解析后的JSON字典
        """
        try:
            content = response["choices"][0]["message"]["content"]
            # 清理可能的markdown代码块标记
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            return json.loads(content)
        except (KeyError, json.JSONDecodeError) as e:
            raise Exception(f"无法从响应中提取JSON: {str(e)}")
    
    def test_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            连接是否成功
        """
        try:
            messages = [
                {"role": "user", "content": "你好，这是一个测试消息，请回复'连接成功'"}
            ]
            response = self.chat_completion(messages, max_tokens=50)
            return "choices" in response
        except Exception as e:
            print(f"连接测试失败: {e}")
            return False


if __name__ == "__main__":
    # 测试客户端
    client = SiliconFlowClient()
    print(f"使用模型: {client.model}")
    print("测试API连接...")
    
    if client.test_connection():
        print("✅ API连接成功！")
        
        # 简单对话测试
        messages = [
            {"role": "user", "content": "请将以下信息转换为JSON格式：客户名称是ABC公司，每天100单"}
        ]
        
        response = client.chat_completion(
            messages,
            response_format={"type": "json_object"}
        )
        
        result = client.extract_json_from_response(response)
        print(f"测试响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    else:
        print("❌ API连接失败，请检查API密钥")
