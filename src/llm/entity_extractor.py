"""
实体抽取模块

从用户自然语言描述中提取关键业务参数
"""

import yaml
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from .client import SiliconFlowClient


class EntityExtractor:
    """
    实体抽取器
    
    使用LLM从用户描述中提取结构化参数
    """
    
    # 必需参数列表
    REQUIRED_PARAMS = [
        "scenario_name",
        "daily_order_count",
        "avg_items_per_order",
        "avg_weight_kg",
        "delivery_distance_km"
    ]
    
    # 可选参数列表
    OPTIONAL_PARAMS = [
        "need_upstairs",
        "floor",
        "has_elevator",
        "need_cold_chain",
        "need_processing",
        "expected_return_rate"
    ]
    
    def __init__(self, client: SiliconFlowClient = None):
        """
        初始化抽取器
        
        Args:
            client: LLM客户端
        """
        self.client = client or SiliconFlowClient()
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """加载Prompt模板"""
        prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts.yaml"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompts = yaml.safe_load(f)
        return prompts.get('entity_extraction', '')
    
    def extract(self, user_input: str, business_type: str = None) -> Dict[str, Any]:
        """
        从用户输入中提取实体
        
        Args:
            user_input: 用户自然语言描述
            business_type: 业务类型（可选，用于辅助提取）
        
        Returns:
            提取的参数字典
        """
        # 构建Prompt
        prompt = self.prompt_template.format(user_input=user_input)
        
        messages = [
            {"role": "system", "content": "你是一个专业的物流参数提取助手。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.client.chat_completion(
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = self.client.extract_json_from_response(response)
            
            # 后处理：数据类型转换和默认值设置
            result = self._post_process(result, business_type)
            
            return result
            
        except Exception as e:
            print(f"实体抽取失败: {e}")
            return self._create_empty_result()
    
    def _post_process(self, result: Dict[str, Any], business_type: str = None) -> Dict[str, Any]:
        """
        后处理提取结果
        
        - 数据类型转换
        - 默认值设置
        - 业务类型特定处理
        """
        processed = {}
        
        # 场景名称
        processed["scenario_name"] = result.get("scenario_name") or "未命名场景"
        
        # 数值参数转换
        for param in ["daily_order_count", "avg_items_per_order", "floor"]:
            value = result.get(param)
            processed[param] = self._to_int(value)
        
        # 浮点数参数转换
        for param in ["avg_weight_kg", "delivery_distance_km", "expected_return_rate"]:
            value = result.get(param)
            processed[param] = self._to_float(value)
        
        # 布尔值参数转换
        for param in ["need_upstairs", "has_elevator", "need_cold_chain", "need_processing"]:
            value = result.get(param)
            processed[param] = self._to_bool(value)
        
        # 业务类型特定默认值
        if business_type == "meal_delivery":
            if processed.get("need_cold_chain") is None:
                processed["need_cold_chain"] = True
            if processed.get("need_processing") is None:
                processed["need_processing"] = True  # 餐配默认需要加工
            if processed.get("expected_return_rate") is None:
                processed["expected_return_rate"] = 0.05
        else:
            if processed.get("need_cold_chain") is None:
                processed["need_cold_chain"] = False
            if processed.get("need_processing") is None:
                processed["need_processing"] = False  # TOB默认不需要加工
            if processed.get("expected_return_rate") is None:
                processed["expected_return_rate"] = 0.01
        
        # 楼层默认值
        if processed.get("floor") is None or processed.get("floor") == 0:
            processed["floor"] = 1
        
        # 记录提取的实体
        processed["extracted_entities"] = result.get("extracted_entities", [])
        
        return processed
    
    def _to_int(self, value) -> Optional[int]:
        """转换为整数"""
        if value is None:
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _to_float(self, value) -> Optional[float]:
        """转换为浮点数"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _to_bool(self, value) -> Optional[bool]:
        """转换为布尔值"""
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ['true', 'yes', '是', '需要', '要']
        return bool(value)
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """创建空结果"""
        return {
            "scenario_name": "未命名场景",
            "daily_order_count": None,
            "avg_items_per_order": None,
            "avg_weight_kg": None,
            "delivery_distance_km": None,
            "need_upstairs": None,
            "floor": 1,
            "has_elevator": None,
            "need_cold_chain": None,
            "need_processing": None,
            "expected_return_rate": None,
            "extracted_entities": []
        }
    
    def get_missing_params(self, extracted: Dict[str, Any]) -> List[str]:
        """
        获取缺失的必需参数
        
        Args:
            extracted: 已提取的参数
        
        Returns:
            缺失参数列表
        """
        missing = []
        for param in self.REQUIRED_PARAMS:
            if extracted.get(param) is None:
                missing.append(param)
        return missing
    
    def is_complete(self, extracted: Dict[str, Any]) -> bool:
        """
        检查参数是否完整
        
        Args:
            extracted: 已提取的参数
        
        Returns:
            是否完整
        """
        return len(self.get_missing_params(extracted)) == 0
    
    def merge_with_defaults(self, extracted: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
        """
        将提取的参数与默认值合并
        
        Args:
            extracted: 提取的参数
            defaults: 默认参数
        
        Returns:
            合并后的参数
        """
        merged = defaults.copy()
        for key, value in extracted.items():
            if value is not None:
                merged[key] = value
        return merged


class RuleBasedExtractor:
    """
    基于规则的实体抽取器（备用方案）
    
    当LLM抽取失败时使用正则表达式进行抽取
    """
    
    # 正则表达式模式
    PATTERNS = {
        "daily_order_count": [
            r"每天(\d+)单",
            r"日订单?(\d+)",
            r"(\d+)单/天",
            r"日发(\d+)",
        ],
        "avg_items_per_order": [
            r"每单(\d+)件",
            r"每件?(\d+)个",
            r"(\d+)件/单",
        ],
        "avg_weight_kg": [
            r"(\d+(?:\.\d+)?)\s*公斤",
            r"(\d+(?:\.\d+)?)\s*kg",
            r"重量(?:约)?(\d+(?:\.\d+)?)",
        ],
        "delivery_distance_km": [
            r"(\d+(?:\.\d+)?)\s*公里",
            r"距离(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)km",
        ],
        "floor": [
            r"(\d+)楼",
            r"(\d+)层",
        ],
    }
    
    @classmethod
    def extract(cls, user_input: str) -> Dict[str, Any]:
        """
        使用规则抽取实体
        
        Args:
            user_input: 用户输入
        
        Returns:
            抽取的参数
        """
        result = {}
        
        for param, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match:
                    value = match.group(1)
                    if param in ["daily_order_count", "avg_items_per_order", "floor"]:
                        result[param] = int(float(value))
                    else:
                        result[param] = float(value)
                    break
        
        # 布尔值抽取
        result["need_upstairs"] = any(kw in user_input for kw in ["上楼", "搬运", "楼层"])
        result["has_elevator"] = not any(kw in user_input for kw in ["无电梯", "没电梯", "楼梯"])
        result["need_cold_chain"] = any(kw in user_input for kw in ["冷链", "冷藏", "冷冻"])
        result["need_processing"] = any(kw in user_input for kw in ["加工", "切割", "清洗"])
        
        return result


if __name__ == "__main__":
    # 测试实体抽取
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    extractor = EntityExtractor()
    
    test_cases = [
        "我们想接一个企业客户，叫ABC公司，每天100单办公用品，每单大概5件，重量10公斤，送到20公里外的写字楼，需要上3楼",
        "有个餐厅需要每天配送50单生鲜食材，每单20件，30公斤，距离15公里，需要冷链",
    ]
    
    print("实体抽取测试：\n")
    for test_input in test_cases:
        print(f"输入: {test_input}")
        result = extractor.extract(test_input)
        print(f"提取结果:")
        for key, value in result.items():
            if key != "extracted_entities":
                print(f"  {key}: {value}")
        
        missing = extractor.get_missing_params(result)
        if missing:
            print(f"缺失参数: {missing}")
        else:
            print("✅ 参数完整")
        print("-" * 50)
