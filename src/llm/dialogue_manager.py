"""
对话管理模块

管理多轮对话，收集缺失参数
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from .client import SiliconFlowClient
from .entity_extractor import EntityExtractor


class DialogueManager:
    """
    对话管理器
    
    管理多轮对话，逐步收集业务参数
    """
    
    def __init__(self, client: SiliconFlowClient = None):
        """
        初始化对话管理器
        
        Args:
            client: LLM客户端
        """
        self.client = client or SiliconFlowClient()
        self.extractor = EntityExtractor(client)
        self.prompt_template = self._load_prompt()
        
        # 对话状态
        self.reset()
    
    def reset(self):
        """重置对话状态"""
        self.collected_params: Dict[str, Any] = {}
        self.business_type: Optional[str] = None
        self.conversation_history: List[Dict[str, str]] = []
        self.current_question: Optional[str] = None
    
    def _load_prompt(self) -> str:
        """加载Prompt模板"""
        prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts.yaml"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompts = yaml.safe_load(f)
        return prompts.get('parameter_completion', '')
    
    def start_dialogue(self, user_input: str, business_type: str = None) -> Dict[str, Any]:
        """
        开始对话
        
        Args:
            user_input: 用户初始输入
            business_type: 业务类型（如已识别）
        
        Returns:
            对话状态
        """
        self.reset()
        self.business_type = business_type
        
        # 记录用户输入
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # 提取参数
        extracted = self.extractor.extract(user_input, business_type)
        self.collected_params.update(extracted)
        
        # 检查是否完整
        return self._check_completeness()
    
    def continue_dialogue(self, user_input: str) -> Dict[str, Any]:
        """
        继续对话
        
        Args:
            user_input: 用户回复
        
        Returns:
            对话状态
        """
        # 记录用户输入
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # 尝试从回复中提取参数
        extracted = self.extractor.extract(user_input, self.business_type)
        
        # 更新已收集的参数
        for key, value in extracted.items():
            if value is not None and key != "extracted_entities":
                self.collected_params[key] = value
        
        # 检查是否完整
        return self._check_completeness()
    
    def _check_completeness(self) -> Dict[str, Any]:
        """
        检查参数完整性
        
        Returns:
            对话状态字典
        """
        missing = self.extractor.get_missing_params(self.collected_params)
        
        if not missing:
            # 参数完整
            return {
                "status": "complete",
                "params": self.collected_params,
                "business_type": self.business_type,
                "message": "参数收集完成"
            }
        else:
            # 需要继续收集
            next_question = self._generate_question(missing)
            self.current_question = next_question
            
            return {
                "status": "incomplete",
                "collected_params": self.collected_params,
                "missing_params": missing,
                "next_question": next_question,
                "business_type": self.business_type
            }
    
    def _generate_question(self, missing_params: List[str]) -> str:
        """
        生成询问问题
        
        Args:
            missing_params: 缺失参数列表
        
        Returns:
            问题文本
        """
        # 参数描述映射
        param_descriptions = {
            "scenario_name": "客户名称或场景名称",
            "daily_order_count": "每天大概有多少订单",
            "avg_items_per_order": "平均每单有多少件商品",
            "avg_weight_kg": "平均每单重量大约多少公斤",
            "delivery_distance_km": "配送距离大概多少公里",
        }
        
        # 优先询问第一个缺失参数
        param = missing_params[0]
        description = param_descriptions.get(param, param)
        
        # 构建Prompt
        collected_str = "\n".join([f"- {k}: {v}" for k, v in self.collected_params.items() if v is not None])
        missing_str = ", ".join(missing_params)
        
        prompt = self.prompt_template.format(
            collected_params=collected_str,
            missing_params=missing_str
        )
        
        messages = [
            {"role": "system", "content": "你是一个专业的物流业务顾问。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.client.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=200
            )
            
            question = response["choices"][0]["message"]["content"].strip()
            
            # 如果LLM生成的问题太短，使用默认问题
            if len(question) < 10:
                question = self._get_default_question(param)
            
            return question
            
        except Exception as e:
            # 使用默认问题
            return self._get_default_question(param)
    
    def _get_default_question(self, param: str) -> str:
        """
        获取默认问题
        
        Args:
            param: 参数名
        
        Returns:
            默认问题文本
        """
        questions = {
            "scenario_name": "请问客户名称是什么？",
            "daily_order_count": "请问每天大概有多少订单？（例如：每天50单）",
            "avg_items_per_order": "请问平均每单有多少件商品？（例如：每单10件）",
            "avg_weight_kg": "请问平均每单重量大约多少公斤？（例如：20公斤）",
            "delivery_distance_km": "请问配送距离大概多少公里？（例如：15公里）",
        }
        
        return questions.get(param, f"请提供 {param} 的信息")
    
    def get_collected_params(self) -> Dict[str, Any]:
        """
        获取已收集的参数
        
        Returns:
            参数字典
        """
        return self.collected_params.copy()
    
    def is_complete(self) -> bool:
        """
        检查是否收集完成
        
        Returns:
            是否完成
        """
        return self.extractor.is_complete(self.collected_params)


if __name__ == "__main__":
    # 测试对话管理
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    manager = DialogueManager()
    
    # 模拟对话
    print("对话管理测试：\n")
    
    # 第一轮：用户提供部分信息
    user_input1 = "我们想接一个企业客户，每天大概100单"
    print(f"用户: {user_input1}")
    
    result1 = manager.start_dialogue(user_input1, "tob_enterprise")
    print(f"系统状态: {result1['status']}")
    print(f"已收集: {result1.get('collected_params', {})}")
    print(f"缺失: {result1.get('missing_params', [])}")
    print(f"下一个问题: {result1.get('next_question', '无')}")
    print("-" * 50)
    
    # 第二轮：用户补充信息
    user_input2 = "每单大概5件，重量10公斤"
    print(f"用户: {user_input2}")
    
    result2 = manager.continue_dialogue(user_input2)
    print(f"系统状态: {result2['status']}")
    print(f"已收集: {result2.get('collected_params', {})}")
    print(f"缺失: {result2.get('missing_params', [])}")
    if result2['status'] == 'incomplete':
        print(f"下一个问题: {result2.get('next_question', '无')}")
    print("-" * 50)
    
    # 第三轮：用户补充剩余信息
    user_input3 = "配送距离20公里"
    print(f"用户: {user_input3}")
    
    result3 = manager.continue_dialogue(user_input3)
    print(f"系统状态: {result3['status']}")
    if result3['status'] == 'complete':
        print(f"完整参数: {result3['params']}")
