"""
自适应智能评估器

集成成本环节识别、确认和选择性计算功能
支持订单利润综合评估
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
from ..models import CostParameters, CostLinkConfig, CostLinkConfirmation
from ..cost_engine import SelectiveCostCalculator
from ..knowledge import CostQueryEngine, SuggestionEngine, KnowledgeBase, FollowUpHandler


class AdaptiveAssessor:
    """
    自适应智能评估器
    
    支持：
    1. 识别业务涉及的成本环节
    2. 向用户确认环节配置
    3. 支持自定义环节的添加
    4. 根据确认的环节进行选择性计算
    5. 订单利润综合评估（按需触发）
    """
    
    # 对话状态
    STATE_IDLE = "idle"                          # 空闲
    STATE_COLLECTING_PARAMS = "collecting_params" # 收集参数
    STATE_CONFIRMING_LINKS = "confirming_links"   # 确认环节
    STATE_CONFIRMING_CUSTOM = "confirming_custom" # 确认自定义环节
    STATE_CALCULATED = "calculated"               # 已计算
    STATE_PROFIT_ASSESSMENT = "profit_assessment" # 订单利润评估
    
    def __init__(self):
        """初始化自适应评估器"""
        self.client = SiliconFlowClient()
        self.intent_classifier = IntentClassifier(self.client)
        self.entity_extractor = EntityExtractor(self.client)
        self.dialogue_manager = DialogueManager(self.client)
        self.link_identifier = CostLinkIdentifier(self.client)
        self.link_confirmation_handler = CostLinkConfirmationHandler()
        
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
    
    def assess_from_text(self, user_input: str) -> Dict[str, Any]:
        """
        从自然语言文本进行评估（自适应版本）
        
        Args:
            user_input: 用户输入
        
        Returns:
            评估结果或确认请求
        """
        # 记录对话历史
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # 根据当前状态处理
        if self.state == self.STATE_CONFIRMING_LINKS:
            # 处理环节确认回复
            return self._handle_link_confirmation(user_input)
        
        elif self.state == self.STATE_CONFIRMING_CUSTOM:
            # 处理自定义环节确认
            return self._handle_custom_link_confirmation(user_input)
        
        elif self.state == self.STATE_COLLECTING_PARAMS:
            # 继续收集参数
            return self._continue_collecting_params(user_input)
        
        elif self.state == self.STATE_PROFIT_ASSESSMENT:
            # 处理订单利润评估
            return self._handle_profit_assessment(user_input)
        
        elif self.state == self.STATE_CALCULATED:
            # 已计算完成，检查是否触发订单利润评估
            if self._should_trigger_profit_assessment(user_input):
                return self._start_profit_assessment(user_input)
            else:
                # 处理其他追问
                return self._handle_follow_up_question(user_input)
        
        else:
            # 开始新的评估
            return self._start_new_assessment(user_input)
    
    def _start_new_assessment(self, user_input: str) -> Dict[str, Any]:
        """开始新的评估"""
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
            
            # 2. 实体抽取
            extracted_params = self.entity_extractor.extract(user_input, business_type)
            
            # 3. 检查参数完整性
            missing_params = self.entity_extractor.get_missing_params(extracted_params)
            
            if missing_params:
                self.state = self.STATE_COLLECTING_PARAMS
                self.pending_confirmation = {
                    "business_type": business_type,
                    "extracted_params": extracted_params,
                    "missing_params": missing_params
                }
                return {
                    "success": False,
                    "state": self.state,
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
                    "state": self.state,
                    "error": "参数校验失败",
                    "message": f"参数错误: {errors}",
                    "business_type": business_type,
                    "extracted_params": extracted_params
                }
            
            # 5. 创建业务场景
            scenario = ParameterValidator.create_scenario(extracted_params, business_type)
            cost_params = CostParameters.from_scenario(scenario)
            
            # 6. 识别成本环节
            link_config = self.link_identifier.identify_from_text(user_input, business_type)
            self.current_link_config = link_config
            cost_params.link_config = link_config
            
            # 7. 检查是否需要确认环节
            uncertain_links = link_config.get_links_needing_confirmation()
            
            if uncertain_links:
                self.state = self.STATE_CONFIRMING_LINKS
                self.current_scenario = scenario
                self.current_params = cost_params
                
                # 生成确认对话框
                confirmation_dialog = self.link_identifier.format_confirmation_dialog(link_config)
                
                return {
                    "success": False,
                    "state": self.state,
                    "needs_confirmation": True,
                    "message": "请确认成本环节配置",
                    "confirmation_dialog": confirmation_dialog,
                    "uncertain_links": [l.name for l in uncertain_links],
                    "business_type": business_type,
                    "scenario": scenario.dict()
                }
            
            # 8. 不需要确认，直接计算
            return self._perform_calculation(scenario, cost_params, link_config)
            
        except Exception as e:
            return {
                "success": False,
                "state": self.state,
                "error": "评估过程出错",
                "message": str(e)
            }
    
    def _handle_link_confirmation(self, user_response: str) -> Dict[str, Any]:
        """处理环节确认回复"""
        # 解析用户回复
        confirmation = self.link_confirmation_handler.parse_confirmation(
            user_response, self.current_link_config
        )
        
        # 检查是否是自定义环节请求
        if confirmation.get("custom_link_request"):
            self.state = self.STATE_CONFIRMING_CUSTOM
            return {
                "success": False,
                "state": self.state,
                "needs_custom_link": True,
                "message": "请详细描述您提到的额外成本环节，包括：\n1. 环节名称\n2. 费用产生的动因\n3. 计算方式或费率",
                "user_request": confirmation["custom_link_request"]
            }
        
        # 应用确认结果
        self.current_link_config = self.link_confirmation_handler.apply_confirmation(
            self.current_link_config, confirmation
        )
        
        # 更新参数中的配置
        self.current_params.link_config = self.current_link_config
        
        # 检查是否还有未确认的环节
        need_more, need_links = self.link_confirmation_handler.check_need_more_data(
            self.current_link_config
        )
        
        if need_more and not confirmation.get("action") == "confirm_all":
            # 还有未确认的环节
            confirmation_dialog = self.link_identifier.format_confirmation_dialog(
                self.current_link_config
            )
            return {
                "success": False,
                "state": self.state,
                "needs_confirmation": True,
                "message": "还有环节需要确认",
                "confirmation_dialog": confirmation_dialog,
                "uncertain_links": need_links
            }
        
        # 所有环节已确认，执行计算
        self.state = self.STATE_CALCULATED
        return self._perform_calculation(
            self.current_scenario, 
            self.current_params, 
            self.current_link_config
        )
    
    def _handle_custom_link_confirmation(self, user_description: str) -> Dict[str, Any]:
        """处理自定义环节确认"""
        # 分析用户描述的自定义环节
        analysis = self.link_identifier.analyze_custom_link(user_description)
        
        if not analysis:
            # 分析失败，询问是否继续
            return {
                "success": False,
                "state": self.state,
                "message": "无法自动分析该环节。请提供以下信息：\n1. 环节名称\n2. 费率（元/单位）\n3. 计量单位（如：单、件、公里等）",
                "can_skip": True
            }
        
        # 检查是否可以合并到基础环节
        if analysis.get("can_merge_with_base"):
            merge_target = analysis.get("suggested_merge_target")
            return {
                "success": False,
                "state": self.state,
                "needs_merge_decision": True,
                "message": f"系统分析该环节可以合并到【{merge_target}】环节计算，是否同意合并？\n\n"
                          f"环节名称: {analysis.get('link_name')}\n"
                          f"计算方式: {analysis.get('calculation_method')}\n"
                          f"费用动因: {analysis.get('cost_driver')}",
                "analysis": analysis,
                "options": [
                    {"value": "merge", "label": f"同意合并到{merge_target}"},
                    {"value": "separate", "label": "作为独立环节计算"},
                    {"value": "skip", "label": "跳过此环节"}
                ]
            }
        
        # 添加为独立自定义环节
        custom_link = self.current_link_config.add_custom_link(
            name=analysis.get("link_name", "自定义环节"),
            description=analysis.get("description", ""),
            formula=analysis.get("calculation_method"),
            rate=self._parse_rate(analysis.get("estimated_rate")),
            unit=analysis.get("unit", "单")
        )
        
        # 返回环节确认状态
        self.state = self.STATE_CONFIRMING_LINKS
        return {
            "success": False,
            "state": self.state,
            "custom_link_added": True,
            "message": f"已添加自定义环节【{custom_link.name}】\n"
                      f"费率: {custom_link.custom_rate} 元/{custom_link.custom_unit}\n\n"
                      f"是否还有其他环节需要确认？",
            "link_config_summary": self.current_link_config.get_confirmation_summary()
        }
    
    def _perform_calculation(
        self, 
        scenario, 
        cost_params: CostParameters, 
        link_config: CostLinkConfig
    ) -> Dict[str, Any]:
        """执行成本计算"""
        # 使用选择性计算器
        cost_result = self.cost_calculator.calculate(
            params=cost_params,
            business_type=scenario.business_type.value,
            scenario_name=scenario.scenario_name,
            link_config=link_config
        )
        
        # 保存状态
        self.current_result = cost_result
        self.current_params = cost_params
        self.current_scenario = scenario
        self.state = self.STATE_CALCULATED
        
        # 初始化知识模块
        self.follow_up_handler.set_context(cost_result, cost_params.dict())
        self.cost_query_engine.set_cost_result(cost_result)
        
        # 生成数据驱动的建议
        suggestions = self.suggestion_engine.generate_suggestions(
            cost_result, 
            cost_params.dict()
        )
        
        # 获取相关知识
        relevant_knowledge = self.knowledge_base.get_relevant_knowledge(
            scenario.business_type.value,
            cost_result.cost_structure
        )
        
        # 生成增强版报告
        enhanced_report = self._generate_adaptive_report(
            cost_result, 
            link_config,
            suggestions, 
            relevant_knowledge
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
            "report": enhanced_report,
            "can_ask_follow_up": True
        }
    
    def _generate_adaptive_report(
        self, 
        cost_result, 
        link_config: CostLinkConfig,
        suggestions, 
        relevant_knowledge
    ) -> str:
        """生成自适应评估报告"""
        lines = [
            f"\n{'='*60}",
            f"  {cost_result.scenario_name} - 智能成本评估报告",
            f"{'='*60}",
            f"",
            f"【成本环节配置】",
        ]
        
        # 显示计算的环节
        calc_details = cost_result.calculation_details
        calculated = calc_details.get("calculated_links", [])
        skipped = calc_details.get("skipped_links", [])
        custom = calc_details.get("custom_costs", {})
        
        if calculated:
            lines.append(f"✅ 参与计算的环节 ({len(calculated)}个):")
            for link in calculated:
                lines.append(f"   • {link}")
        
        if custom:
            lines.append(f"\n➕ 自定义环节 ({len(custom)}个):")
            for name, cost in custom.items():
                lines.append(f"   • {name}: ¥{cost:,.2f}")
        
        if skipped:
            lines.append(f"\n❌ 未参与的环节 ({len(skipped)}个):")
            for link in skipped:
                lines.append(f"   • {link}")
        
        lines.extend([
            f"",
            f"【成本汇总】",
            f"  月度总成本: ¥{cost_result.total_monthly_cost:,.2f}",
            f"  单均成本: ¥{cost_result.total_cost_per_order:.2f}",
            f"  单件成本: ¥{cost_result.total_cost_per_item:.2f}",
            f"",
            f"【成本结构分析】",
        ])
        
        # 成本结构（按占比排序）
        sorted_structure = sorted(
            cost_result.cost_structure.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        for category, percentage in sorted_structure:
            lines.append(f"  • {category}: {percentage:.1f}%")
        
        # 可行性评级
        lines.extend([
            f"",
            f"【可行性评级】 {cost_result.feasibility_rating.value.upper()}",
        ])
        
        # 风险提示
        if cost_result.risk_factors:
            lines.extend([
                f"",
                f"【风险提示】",
            ])
            for risk in cost_result.risk_factors:
                lines.append(f"  ⚠️ {risk}")
        
        # 数据驱动的建议
        if suggestions:
            lines.append(self.suggestion_engine.format_suggestions(suggestions))
        
        # 行业知识
        if relevant_knowledge:
            lines.extend([
                f"",
                f"{'='*60}",
                f"【相关行业知识】",
                f"{'='*60}",
            ])
            for item in relevant_knowledge:
                lines.append(f"\n📚 {item.title}")
                lines.append(f"   {item.content}")
                lines.append(f"   来源: {item.source}")
        
        # 追问提示
        lines.extend([
            f"",
            f"{'='*60}",
            f"您可以继续询问：",
            f"  • 具体环节成本详情（如：运输成本怎么算的？）",
            f"  • 假设分析（如：如果日订单增加到200单会怎样？）",
            f"  • 优化建议详情（如：如何降低上楼成本？）",
            f"{'='*60}",
        ])
        
        return "\n".join(lines)
    
    def _continue_collecting_params(self, user_input: str) -> Dict[str, Any]:
        """继续收集参数"""
        # 这里可以实现参数补充逻辑
        # 简化处理：提示用户重新开始
        return {
            "success": False,
            "state": self.state,
            "message": "请提供完整业务信息后重新提交",
            "can_restart": True
        }
    
    def _should_trigger_profit_assessment(self, user_input: str) -> bool:
        """
        判断是否应触发订单利润评估
        
        Args:
            user_input: 用户输入
        
        Returns:
            是否应该触发
        """
        has_logistics = self.current_result is not None
        return should_trigger_profit_assessment(user_input, has_logistics)
    
    def _start_profit_assessment(self, user_input: str) -> Dict[str, Any]:
        """
        开始订单利润评估
        
        Args:
            user_input: 用户输入
        
        Returns:
            响应结果
        """
        # 获取物流成本
        logistics_cost = self.current_result.total_cost_per_order if self.current_result else 0
        
        # 开始利润评估
        result = self.profit_handler.start_assessment(logistics_cost, user_input)
        
        if result["status"] == "completed":
            # 直接完成
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
            # 需要收集更多信息
            self.state = self.STATE_PROFIT_ASSESSMENT
            return {
                "success": False,
                "state": self.state,
                "needs_profit_input": True,
                "message": result["message"],
                "missing_fields": result.get("missing_fields", [])
            }
    
    def _handle_profit_assessment(self, user_input: str) -> Dict[str, Any]:
        """
        处理订单利润评估输入
        
        Args:
            user_input: 用户输入
        
        Returns:
            处理结果
        """
        result = self.profit_handler.process_input(user_input)
        
        if result["status"] == "completed":
            self.profit_assessment_result = self.profit_handler.current_assessment
            self.state = self.STATE_CALCULATED
            return {
                "success": True,
                "state": self.state,
                "profit_assessment": result["assessment"],
                "message": result["message"],
                "has_profit_assessment": True,
                "feasibility": result.get("feasibility"),
                "profit_margin": result.get("profit_margin")
            }
        else:
            # 继续收集
            return {
                "success": False,
                "state": self.state,
                "needs_profit_input": True,
                "message": result["message"],
                "missing_fields": result.get("missing_fields", [])
            }
    
    def _handle_follow_up_question(self, user_input: str) -> Dict[str, Any]:
        """
        处理普通追问
        
        Args:
            user_input: 用户输入
        
        Returns:
            回答结果
        """
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
            # 尝试从字符串提取数字
            import re
            numbers = re.findall(r'\d+\.?\d*', str(rate_value))
            if numbers:
                return float(numbers[0])
        except:
            pass
        return None
    
    def handle_follow_up(self, user_question: str) -> Dict[str, Any]:
        """处理用户追问"""
        if not self.current_result:
            return {
                "success": False,
                "message": "请先完成成本评估，再提问"
            }
        
        response = self.follow_up_handler.handle_follow_up(user_question)
        
        return {
            "success": True,
            "type": response.get("type", "general"),
            "answer": response.get("text_answer", ""),
            "data": response.get("data")
        }
    
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
    
    def get_current_state(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "state": self.state,
            "has_result": self.current_result is not None,
            "has_scenario": self.current_scenario is not None,
            "has_profit_assessment": self.profit_assessment_result is not None,
            "link_config": self.current_link_config.to_dict() if self.current_link_config else None
        }
    
    def get_profit_assessment_report(self) -> Optional[str]:
        """获取订单利润评估报告"""
        if self.profit_assessment_result:
            return self.profit_assessment_result.to_report()
        return None


if __name__ == "__main__":
    # 测试自适应评估器
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    assessor = AdaptiveAssessor()
    
    print("="*60)
    print("自适应智能评估器测试")
    print("="*60)
    
    # 测试评估
    test_input = "我们想接一个企业客户，叫ABC公司，每天100单办公用品，每单5件，重量10公斤，送到20公里外的写字楼，需要上3楼"
    
    print(f"\n输入: {test_input}\n")
    
    result = assessor.assess_from_text(test_input)
    
    if result.get("needs_confirmation"):
        print(result["confirmation_dialog"])
        print("\n用户回复: 确认全部")
        result = assessor.assess_from_text("确认全部")
    
    if result["success"]:
        print(result["report"])
    else:
        print(f"评估失败: {result['message']}")
