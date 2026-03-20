"""
智能评估主模块

集成意图识别、实体抽取、成本计算、可行性评估的完整流程
"""

from typing import Dict, Any, Optional
from .client import SiliconFlowClient
from .intent_classifier import IntentClassifier
from .entity_extractor import EntityExtractor
from .parameter_validator import ParameterValidator
from .dialogue_manager import DialogueManager
from ..models import CostParameters
from ..cost_engine import CostCalculator


class SmartAssessor:
    """
    智能评估器
    
    提供从自然语言输入到成本评估结果的完整流程
    """
    
    def __init__(self):
        """初始化智能评估器"""
        self.client = SiliconFlowClient()
        self.intent_classifier = IntentClassifier(self.client)
        self.entity_extractor = EntityExtractor(self.client)
        self.dialogue_manager = DialogueManager(self.client)
        self.cost_calculator = CostCalculator()
    
    def assess_from_text(self, user_input: str) -> Dict[str, Any]:
        """
        从自然语言文本进行完整评估
        
        Args:
            user_input: 用户自然语言描述
        
        Returns:
            评估结果
        """
        try:
            # 1. 意图识别
            business_type, confidence, reasoning = self.intent_classifier.classify_with_fallback(user_input)
            
            if business_type == "uncertain":
                return {
                    "success": False,
                    "error": "无法识别业务类型",
                    "message": "请明确说明是TOB企业购业务还是餐配业务",
                    "confidence": confidence
                }
            
            # 2. 实体抽取
            extracted_params = self.entity_extractor.extract(user_input, business_type)
            
            # 3. 检查参数完整性
            missing_params = self.entity_extractor.get_missing_params(extracted_params)
            
            if missing_params:
                # 参数不完整，返回缺失信息
                return {
                    "success": False,
                    "error": "参数不完整",
                    "message": f"缺少以下必需参数: {missing_params}",
                    "business_type": business_type,
                    "extracted_params": extracted_params,
                    "missing_params": missing_params,
                    "can_continue": True
                }
            
            # 4. 参数校验
            is_valid, errors = ParameterValidator.validate(extracted_params)
            if not is_valid:
                return {
                    "success": False,
                    "error": "参数校验失败",
                    "message": f"参数错误: {errors}",
                    "business_type": business_type,
                    "extracted_params": extracted_params
                }
            
            # 5. 创建业务场景并计算成本
            scenario = ParameterValidator.create_scenario(extracted_params, business_type)
            cost_params = CostParameters.from_scenario(scenario)
            
            cost_result = self.cost_calculator.calculate(
                params=cost_params,
                business_type=business_type,
                scenario_name=scenario.scenario_name
            )
            
            # 6. 返回完整结果
            return {
                "success": True,
                "business_type": business_type,
                "confidence": confidence,
                "reasoning": reasoning,
                "scenario": {
                    "name": scenario.scenario_name,
                    "daily_orders": scenario.daily_order_count,
                    "distance_km": scenario.delivery_distance_km,
                },
                "cost_result": cost_result,
                "report": cost_result.to_report()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": "评估过程出错",
                "message": str(e)
            }
    
    def start_dialogue_assessment(self, user_input: str) -> Dict[str, Any]:
        """
        启动对话式评估
        
        Args:
            user_input: 用户初始输入
        
        Returns:
            对话状态
        """
        # 1. 意图识别
        business_type, confidence, reasoning = self.intent_classifier.classify_with_fallback(user_input)
        
        # 2. 启动对话
        dialogue_state = self.dialogue_manager.start_dialogue(user_input, business_type)
        
        return {
            "business_type": business_type,
            "confidence": confidence,
            "reasoning": reasoning,
            **dialogue_state
        }
    
    def continue_dialogue_assessment(self, user_input: str) -> Dict[str, Any]:
        """
        继续对话式评估
        
        Args:
            user_input: 用户回复
        
        Returns:
            对话状态或评估结果
        """
        # 继续对话
        dialogue_state = self.dialogue_manager.continue_dialogue(user_input)
        
        # 如果参数收集完成，进行成本计算
        if dialogue_state["status"] == "complete":
            params = dialogue_state["params"]
            business_type = dialogue_state["business_type"]
            
            # 校验参数
            is_valid, errors = ParameterValidator.validate(params)
            if not is_valid:
                return {
                    "success": False,
                    "error": "参数校验失败",
                    "message": f"参数错误: {errors}",
                    "dialogue_state": dialogue_state
                }
            
            # 创建场景并计算成本
            scenario = ParameterValidator.create_scenario(params, business_type)
            cost_params = CostParameters.from_scenario(scenario)
            
            cost_result = self.cost_calculator.calculate(
                params=cost_params,
                business_type=business_type,
                scenario_name=scenario.scenario_name
            )
            
            return {
                "success": True,
                "status": "complete",
                "business_type": business_type,
                "scenario": {
                    "name": scenario.scenario_name,
                    "daily_orders": scenario.daily_order_count,
                    "distance_km": scenario.delivery_distance_km,
                },
                "cost_result": cost_result,
                "report": cost_result.to_report()
            }
        
        # 参数还未收集完成
        return {
            "success": True,
            "status": "incomplete",
            **dialogue_state
        }
    
    def quick_assess(self, user_input: str) -> str:
        """
        快速评估（简化接口）
        
        Args:
            user_input: 用户输入
        
        Returns:
            评估报告文本
        """
        result = self.assess_from_text(user_input)
        
        if result["success"]:
            return result["report"]
        else:
            return f"评估失败: {result['message']}"


if __name__ == "__main__":
    # 测试智能评估器
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    assessor = SmartAssessor()
    
    # 测试完整评估
    test_cases = [
        "我们想接一个企业客户，叫ABC公司，每天100单办公用品，每单5件，重量10公斤，送到20公里外的写字楼，需要上3楼",
        "有个餐厅需要每天配送50单生鲜食材，每单20件，30公斤，距离15公里，需要冷链",
    ]
    
    print("=" * 60)
    print("智能评估测试")
    print("=" * 60)
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n测试案例 {i}:")
        print(f"输入: {test_input}")
        print("-" * 60)
        
        result = assessor.assess_from_text(test_input)
        
        if result["success"]:
            print(f"✅ 评估成功")
            print(f"业务类型: {result['business_type']}")
            print(f"置信度: {result['confidence']:.2f}")
            print("\n评估报告:")
            print(result["report"])
        else:
            print(f"❌ 评估失败")
            print(f"错误: {result['message']}")
            if result.get("missing_params"):
                print(f"缺失参数: {result['missing_params']}")
        
        print("=" * 60)
