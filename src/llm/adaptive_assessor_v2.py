"""
自适应智能评估器 V2

增强功能：
- 智能参数收集和确认
- 部分计算能力（缺失数据时计算可计算部分）
- 计算前环节和数据确认
- 优化的错误处理和用户交互
"""

from typing import Dict, List, Optional, Any
from .client import SiliconFlowClient
from .intent_classifier import IntentClassifier
from .entity_extractor import EntityExtractor
from .parameter_validator import ParameterValidator
from .dialogue_manager import DialogueManager
from .cost_link_identifier import CostLinkIdentifier, CostLinkConfirmationHandler
from .order_profit_handler import (
    OrderProfitHandler,
    should_trigger_profit_assessment,
    OrderProfitIntentDetector
)
from .smart_parameter_collector import SmartParameterCollector, ParameterStatus
from ..models import CostParameters, CostLinkConfig, CostLinkConfirmation, BusinessScenario
from ..cost_engine import SelectiveCostCalculator
from ..knowledge import CostQueryEngine, SuggestionEngine, KnowledgeBase, FollowUpHandler


class AdaptiveAssessorV2:
    """
    自适应智能评估器 V2
    
    增强功能：
    1. 智能参数收集和确认
    2. 部分计算能力
    3. 计算前确认
    4. 优化的错误处理
    """
    
    # 对话状态
    STATE_IDLE = "idle"
    STATE_COLLECTING_PARAMS = "collecting_params"
    STATE_CONFIRMING_PARAMS = "confirming_params"  # 新增：参数确认
    STATE_CONFIRMING_LINKS = "confirming_links"
    STATE_CONFIRMING_CUSTOM = "confirming_custom"
    STATE_CALCULATED = "calculated"
    STATE_PROFIT_ASSESSMENT = "profit_assessment"
    
    def __init__(self):
        """初始化评估器"""
        self.client = SiliconFlowClient()
        self.intent_classifier = IntentClassifier(self.client)
        self.entity_extractor = EntityExtractor(self.client)
        self.dialogue_manager = DialogueManager(self.client)
        self.link_identifier = CostLinkIdentifier(self.client)
        self.link_confirmation_handler = CostLinkConfirmationHandler()
        self.parameter_collector = SmartParameterCollector()
        
        # 使用选择性成本计算器
        self.cost_calculator = SelectiveCostCalculator()
        
        # 知识模块
        self.cost_query_engine = CostQueryEngine()
        self.suggestion_engine = SuggestionEngine()
        self.knowledge_base = KnowledgeBase()
        self.follow_up_handler = FollowUpHandler()
        
        # 订单利润评估处理器
        self.profit_handler = OrderProfitHandler(self.client)
        
        # 当前状态
        self.state = self.STATE_IDLE
        self.current_result = None
        self.current_params = None
        self.current_scenario = None
        self.current_link_config = None
        self.pending_confirmation = None
        self.conversation_history = []
        self.profit_assessment_result = None
        self.business_type = None
    
    def assess_from_text(self, user_input: str) -> Dict[str, Any]:
        """
        从自然语言文本进行评估（V2版本）
        
        Args:
            user_input: 用户输入
        
        Returns:
            评估结果或确认请求
        """
        # 记录对话历史
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # 根据当前状态处理
        if self.state == self.STATE_COLLECTING_PARAMS:
            return self._handle_parameter_collection(user_input)
        
        elif self.state == self.STATE_CONFIRMING_PARAMS:
            return self._handle_parameter_confirmation(user_input)
        
        elif self.state == self.STATE_CONFIRMING_LINKS:
            return self._handle_link_confirmation(user_input)
        
        elif self.state == self.STATE_CONFIRMING_CUSTOM:
            return self._handle_custom_link_confirmation(user_input)
        
        elif self.state == self.STATE_PROFIT_ASSESSMENT:
            return self._handle_profit_assessment(user_input)
        
        elif self.state == self.STATE_CALCULATED:
            if self._should_trigger_profit_assessment(user_input):
                return self._start_profit_assessment(user_input)
            else:
                return self._handle_follow_up_question(user_input)
        
        else:
            return self._start_new_assessment(user_input)
    
    def _start_new_assessment(self, user_input: str) -> Dict[str, Any]:
        """开始新的评估（V2版本）"""
        try:
            # 1. 意图识别
            business_type, confidence, reasoning = self.intent_classifier.classify_with_fallback(user_input)
            
            if business_type == "uncertain":
                return {
                    "success": False,
                    "state": self.state,
                    "error": "无法识别业务类型",
                    "message": "请明确说明是TOB企业购业务还是餐配业务",
                    "confidence": confidence
                }
            
            self.business_type = business_type
            
            # 2. 使用智能参数收集器提取参数
            result = self.parameter_collector.extract_from_text(user_input, business_type)
            
            # 3. 检查是否有缺失的必需参数
            if result["missing_params"]:
                self.state = self.STATE_COLLECTING_PARAMS
                return {
                    "success": False,
                    "state": self.state,
                    "needs_more_info": True,
                    "message": self.parameter_collector.generate_collection_prompt(),
                    "missing_params": [p.name for p in result["missing_params"]],
                    "extracted_params": result["parameters"],
                    "can_calculate_partial": result["can_calculate_partial"]
                }
            
            # 4. 参数完整，进入确认阶段
            self.state = self.STATE_CONFIRMING_PARAMS
            return {
                "success": False,
                "state": self.state,
                "needs_confirmation": True,
                "message": self.parameter_collector.generate_pre_calculation_summary(),
                "parameters": result["parameters"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "state": self.state,
                "error": "评估过程出错",
                "message": str(e)
            }
    
    def _handle_parameter_collection(self, user_input: str) -> Dict[str, Any]:
        """处理参数收集"""
        result = self.parameter_collector.process_user_response(user_input)
        
        # 检查是否还有缺失的必需参数
        if result["missing_required"]:
            # 继续收集
            return {
                "success": False,
                "state": self.state,
                "needs_more_info": True,
                "message": self.parameter_collector.generate_collection_prompt(),
                "missing_params": result["missing_required"],
                "extracted_count": result["extracted_count"]
            }
        
        # 没有缺失的必需参数了
        # 如果有默认值被应用，通知用户
        if result.get("applied_defaults"):
            defaults_list = "\n".join([f"  • {d['description']}: {d['value']}" 
                                    for d in result["applied_defaults"]])
            defaults_msg = f"已应用默认值：\n{defaults_list}"
        else:
            defaults_msg = ""
        
        # 进入参数确认阶段
        self.state = self.STATE_CONFIRMING_PARAMS
        confirm_msg = self.parameter_collector.generate_pre_calculation_summary()
        if defaults_msg:
            confirm_msg = defaults_msg + "\n\n" + confirm_msg
        
        return {
            "success": False,
            "state": self.state,
            "needs_confirmation": True,
            "message": confirm_msg
        }
    
    def _handle_parameter_confirmation(self, user_input: str) -> Dict[str, Any]:
        """处理参数确认"""
        user_input_lower = user_input.strip().lower()
        
        if user_input_lower in ["确认", "确定", "是的", "ok", "yes"]:
            # 用户确认，开始计算
            return self._proceed_with_calculation()
        
        elif user_input_lower.startswith("修改") or "=" in user_input:
            # 用户要修改参数
            self._parse_parameter_modification(user_input)
            return {
                "success": False,
                "state": self.state,
                "message": "已更新参数，请再次确认：\n" + 
                          self.parameter_collector.generate_pre_calculation_summary()
            }
        
        elif user_input_lower.startswith("补充"):
            # 用户要补充参数
            self._parse_parameter_addition(user_input)
            return {
                "success": False,
                "state": self.state,
                "message": "已补充参数，请再次确认：\n" + 
                          self.parameter_collector.generate_pre_calculation_summary()
            }
        
        else:
            # 无法理解的回复，重新询问
            return {
                "success": False,
                "state": self.state,
                "message": "请回复'确认'开始计算，或'修改XX=值'修改参数"
            }
    
    def _proceed_with_calculation(self) -> Dict[str, Any]:
        """继续执行计算"""
        # 获取最终参数
        params_dict = self.parameter_collector.get_final_parameters()
        
        # 创建业务场景
        try:
            scenario = BusinessScenario(
                business_type=self.business_type,
                **params_dict
            )
        except Exception as e:
            return {
                "success": False,
                "state": self.state,
                "error": "创建业务场景失败",
                "message": str(e)
            }
        
        # 创建成本参数
        cost_params = CostParameters.from_scenario(scenario)
        
        # 识别成本环节
        link_config = self.link_identifier.identify_from_text(
            self.conversation_history[0]["content"], 
            self.business_type
        )
        self.current_link_config = link_config
        cost_params.link_config = link_config
        
        # 检查是否需要确认环节
        uncertain_links = link_config.get_links_needing_confirmation()
        
        if uncertain_links:
            self.state = self.STATE_CONFIRMING_LINKS
            self.current_scenario = scenario
            self.current_params = cost_params
            
            confirmation_dialog = self.link_identifier.format_confirmation_dialog(link_config)
            
            return {
                "success": False,
                "state": self.state,
                "needs_confirmation": True,
                "confirmation_dialog": confirmation_dialog,
                "uncertain_links": [l.name for l in uncertain_links],
                "business_type": self.business_type,
                "scenario": scenario.dict()
            }
        
        # 直接计算
        return self._perform_calculation(scenario, cost_params, link_config)
    
    def _parse_parameter_modification(self, user_input: str):
        """解析参数修改"""
        # 格式：修改XX=值 或 XX=值
        patterns = [
            r'修改\s*(\w+)\s*[=:]\s*(\w+)',
            r'(\w+)\s*[=:]\s*(\w+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_input)
            if match:
                param_name = match.group(1)
                value = match.group(2)
                
                # 尝试转换为数值
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except:
                    pass
                
                self.parameter_collector.update_parameter(param_name, value)
                break
    
    def _parse_parameter_addition(self, user_input: str):
        """解析参数补充"""
        # 与修改逻辑相同
        self._parse_parameter_modification(user_input)
    
    def _handle_link_confirmation(self, user_input: str) -> Dict[str, Any]:
        """处理环节确认（继承原有逻辑）"""
        confirmation = self.link_confirmation_handler.parse_confirmation(
            user_input, self.current_link_config
        )
        
        if confirmation.get("custom_link_request"):
            self.state = self.STATE_CONFIRMING_CUSTOM
            return {
                "success": False,
                "state": self.state,
                "needs_custom_link": True,
                "message": "请详细描述您提到的额外成本环节"
            }
        
        self.current_link_config = self.link_confirmation_handler.apply_confirmation(
            self.current_link_config, confirmation
        )
        
        self.current_params.link_config = self.current_link_config
        
        need_more, need_links = self.link_confirmation_handler.check_need_more_data(
            self.current_link_config
        )
        
        if need_more and not confirmation.get("action") == "confirm_all":
            confirmation_dialog = self.link_identifier.format_confirmation_dialog(
                self.current_link_config
            )
            return {
                "success": False,
                "state": self.state,
                "needs_confirmation": True,
                "confirmation_dialog": confirmation_dialog,
                "uncertain_links": need_links
            }
        
        self.state = self.STATE_CALCULATED
        return self._perform_calculation(
            self.current_scenario,
            self.current_params,
            self.current_link_config
        )
    
    def _handle_custom_link_confirmation(self, user_input: str) -> Dict[str, Any]:
        """处理自定义环节确认（继承原有逻辑）"""
        analysis = self.link_identifier.analyze_custom_link(user_input)
        
        if not analysis:
            return {
                "success": False,
                "state": self.state,
                "message": "无法自动分析该环节，请提供费率信息",
                "can_skip": True
            }
        
        if analysis.get("can_merge_with_base"):
            return {
                "success": False,
                "state": self.state,
                "needs_merge_decision": True,
                "message": f"该环节可以合并到【{analysis.get('suggested_merge_target')}】计算",
                "analysis": analysis
            }
        
        custom_link = self.current_link_config.add_custom_link(
            name=analysis.get("link_name", "自定义环节"),
            description=analysis.get("description", ""),
            formula=analysis.get("calculation_method"),
            rate=self._parse_rate(analysis.get("estimated_rate")),
            unit=analysis.get("unit", "单")
        )
        
        self.state = self.STATE_CONFIRMING_LINKS
        return {
            "success": False,
            "state": self.state,
            "custom_link_added": True,
            "message": f"已添加自定义环节【{custom_link.name}】"
        }
    
    def _perform_calculation(self, scenario, cost_params, link_config) -> Dict[str, Any]:
        """执行计算（继承原有逻辑）"""
        cost_result = self.cost_calculator.calculate(
            params=cost_params,
            business_type=scenario.business_type.value,
            scenario_name=scenario.scenario_name,
            link_config=link_config
        )
        
        self.current_result = cost_result
        self.current_params = cost_params
        self.current_scenario = scenario
        self.state = self.STATE_CALCULATED
        
        self.follow_up_handler.set_context(cost_result, cost_params.dict())
        self.cost_query_engine.set_cost_result(cost_result)
        
        suggestions = self.suggestion_engine.generate_suggestions(
            cost_result,
            cost_params.dict()
        )
        
        relevant_knowledge = self.knowledge_base.get_relevant_knowledge(
            scenario.business_type.value,
            cost_result.cost_structure
        )
        
        return {
            "success": True,
            "state": self.state,
            "business_type": scenario.business_type.value,
            "scenario": {
                "name": scenario.scenario_name,
                "daily_orders": scenario.daily_order_count,
                "distance_km": scenario.delivery_distance_km,
            },
            "cost_result": cost_result,
            "link_config": link_config.to_dict(),
            "suggestions": suggestions,
            "relevant_knowledge": relevant_knowledge,
            "can_ask_follow_up": True
        }
    
    def _should_trigger_profit_assessment(self, user_input: str) -> bool:
        """判断是否应触发订单利润评估"""
        has_logistics = self.current_result is not None
        return should_trigger_profit_assessment(user_input, has_logistics)
    
    def _start_profit_assessment(self, user_input: str) -> Dict[str, Any]:
        """开始订单利润评估"""
        logistics_cost = self.current_result.total_cost_per_order if self.current_result else 0
        
        result = self.profit_handler.start_assessment(logistics_cost, user_input)
        
        if result["status"] == "completed":
            self.profit_assessment_result = self.profit_handler.current_assessment
            self.state = self.STATE_CALCULATED
            return {
                "success": True,
                "state": self.state,
                "profit_assessment": result["assessment"],
                "message": result["message"],
                "has_profit_assessment": True
            }
        else:
            self.state = self.STATE_PROFIT_ASSESSMENT
            return {
                "success": False,
                "state": self.state,
                "needs_profit_input": True,
                "message": result["message"],
                "missing_fields": result.get("missing_fields", [])
            }
    
    def _handle_profit_assessment(self, user_input: str) -> Dict[str, Any]:
        """处理订单利润评估输入"""
        result = self.profit_handler.process_input(user_input)
        
        if result["status"] == "completed":
            self.profit_assessment_result = self.profit_handler.current_assessment
            self.state = self.STATE_CALCULATED
            return {
                "success": True,
                "state": self.state,
                "profit_assessment": result["assessment"],
                "message": result["message"],
                "has_profit_assessment": True
            }
        else:
            return {
                "success": False,
                "state": self.state,
                "needs_profit_input": True,
                "message": result["message"]
            }
    
    def _handle_follow_up_question(self, user_input: str) -> Dict[str, Any]:
        """处理普通追问"""
        response = self.follow_up_handler.handle_follow_up(user_input)
        
        return {
            "success": True,
            "type": response.get("type", "general"),
            "answer": response.get("text_answer", ""),
            "data": response.get("data"),
            "state": self.state
        }
    
    def _parse_rate(self, rate_value) -> Optional[float]:
        """解析费率值"""
        if rate_value is None:
            return None
        try:
            if isinstance(rate_value, (int, float)):
                return float(rate_value)
            import re
            numbers = re.findall(r'\d+\.?\d*', str(rate_value))
            if numbers:
                return float(numbers[0])
        except:
            pass
        return None
    
    def reset(self):
        """重置评估器状态"""
        self.state = self.STATE_IDLE
        self.current_result = None
        self.current_params = None
        self.current_scenario = None
        self.current_link_config = None
        self.pending_confirmation = None
        self.conversation_history = []
        self.follow_up_handler = FollowUpHandler()
        self.profit_handler.reset()
        self.profit_assessment_result = None
        self.parameter_collector = SmartParameterCollector()
        self.business_type = None
    
    def get_current_state(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "state": self.state,
            "has_result": self.current_result is not None,
            "has_scenario": self.current_scenario is not None,
            "has_profit_assessment": self.profit_assessment_result is not None,
            "link_config": self.current_link_config.to_dict() if self.current_link_config else None
        }


if __name__ == "__main__":
    # 测试V2版本
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    print("="*60)
    print("自适应智能评估器 V2 测试")
    print("="*60)
    
    assessor = AdaptiveAssessorV2()
    
    # 测试1: 不完整输入，触发参数收集
    print("\n【测试1】不完整输入")
    test_input = "每天50单，送到15公里外"
    print(f"用户: {test_input}")
    
    result = assessor.assess_from_text(test_input)
    print(f"状态: {result['state']}")
    print(f"需要更多信息: {result.get('needs_more_info')}")
    if result.get('message'):
        print(f"系统回复:\n{result['message']}")
    
    # 测试2: 用户补全参数
    print("\n【测试2】用户补全参数")
    user_reply = "每单3件，重量8公斤，客户是XYZ公司"
    print(f"用户: {user_reply}")
    
    result = assessor.assess_from_text(user_reply)
    print(f"状态: {result['state']}")
    if result.get('needs_confirmation'):
        print("进入参数确认阶段")
        print(f"确认信息:\n{result['message']}")
