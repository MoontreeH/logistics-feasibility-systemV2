"""
意图识别模块

识别用户输入的业务类型（TOB企业购 / 餐配业务）
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Tuple
from .client import SiliconFlowClient


class IntentClassifier:
    """
    意图分类器
    
    使用LLM判断用户描述的业务类型
    """
    
    def __init__(self, client: SiliconFlowClient = None):
        """
        初始化分类器
        
        Args:
            client: LLM客户端，如未提供则自动创建
        """
        self.client = client or SiliconFlowClient()
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """加载Prompt模板"""
        prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts.yaml"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompts = yaml.safe_load(f)
        return prompts.get('intent_classification', '')
    
    def classify(self, user_input: str) -> Dict[str, Any]:
        """
        识别用户意图
        
        Args:
            user_input: 用户输入的自然语言描述
        
        Returns:
            分类结果，包含：
            - business_type: 业务类型
            - confidence: 置信度
            - reasoning: 判断理由
        """
        # 构建Prompt
        prompt = self.prompt_template.format(user_input=user_input)
        
        messages = [
            {"role": "system", "content": "你是一个专业的物流业务分类助手。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.client.chat_completion(
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = self.client.extract_json_from_response(response)
            
            # 验证结果格式
            if "business_type" not in result:
                result["business_type"] = "uncertain"
            if "confidence" not in result:
                result["confidence"] = 0.5
            if "reasoning" not in result:
                result["reasoning"] = "未提供判断理由"
            
            return result
            
        except Exception as e:
            return {
                "business_type": "uncertain",
                "confidence": 0.0,
                "reasoning": f"分类失败: {str(e)}"
            }
    
    def classify_with_fallback(self, user_input: str) -> Tuple[str, float, str]:
        """
        带降级处理的分类
        
        Args:
            user_input: 用户输入
        
        Returns:
            (业务类型, 置信度, 理由) 元组
        """
        result = self.classify(user_input)
        
        business_type = result.get("business_type", "uncertain")
        confidence = result.get("confidence", 0.0)
        reasoning = result.get("reasoning", "")
        
        # 关键词降级策略
        if confidence < 0.6 or business_type == "uncertain":
            business_type, confidence, reasoning = self._keyword_fallback(
                user_input, business_type, confidence, reasoning
            )
        
        return business_type, confidence, reasoning
    
    def _keyword_fallback(
        self, 
        user_input: str, 
        current_type: str, 
        current_confidence: float,
        current_reasoning: str
    ) -> Tuple[str, float, str]:
        """
        关键词降级策略
        
        当LLM置信度低时，使用关键词匹配作为备用方案
        """
        user_input_lower = user_input.lower()
        
        # 餐配业务关键词
        meal_keywords = [
            "餐厅", "食堂", "餐饮", "食材", "生鲜", "蔬菜", "肉类",
            "冷链", "冷藏", "冷冻", "餐配", "配送", "厨房", "后厨",
            "水果", "海鲜", "食材配送", "餐饮食材"
        ]
        
        # TOB企业购关键词
        tob_keywords = [
            "企业", "公司", "办公", "写字楼", "园区", "工厂",
            "办公用品", "劳保", "福利", "采购", "批量", "物资",
            "行政", "后勤", "办公耗材", "文具"
        ]
        
        meal_score = sum(1 for kw in meal_keywords if kw in user_input_lower)
        tob_score = sum(1 for kw in tob_keywords if kw in tob_keywords if kw in user_input_lower)
        
        if meal_score > tob_score and meal_score > 0:
            return "meal_delivery", 0.6, f"关键词匹配（餐配相关词出现{meal_score}次）"
        elif tob_score > meal_score and tob_score > 0:
            return "tob_enterprise", 0.6, f"关键词匹配（TOB相关词出现{tob_score}次）"
        else:
            return current_type, current_confidence, current_reasoning


if __name__ == "__main__":
    # 测试意图分类器
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    classifier = IntentClassifier()
    
    test_cases = [
        "我们想接一个企业客户，每天100单办公用品，送到写字楼",
        "有个餐厅需要每天配送生鲜食材，需要冷链",
        "学校食堂需要配送蔬菜和肉类",
        "某科技公司采购办公耗材"
    ]
    
    print("意图识别测试：\n")
    for test_input in test_cases:
        result = classifier.classify_with_fallback(test_input)
        print(f"输入: {test_input}")
        print(f"结果: 类型={result[0]}, 置信度={result[1]:.2f}")
        print(f"理由: {result[2]}")
        print("-" * 50)
