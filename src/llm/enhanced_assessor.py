"""
增强版智能评估器

集成成本查询、数据驱动建议、追问处理、知识库等功能
"""

from typing import Dict, Any, Optional
from .client import SiliconFlowClient
from .intent_classifier import IntentClassifier
from .entity_extractor import EntityExtractor
from .parameter_validator import ParameterValidator
from .dialogue_manager import DialogueManager
from ..models import CostParameters
from ..cost_engine import CostCalculator
from ..knowledge import CostQueryEngine, SuggestionEngine, KnowledgeBase, FollowUpHandler


class EnhancedAssessor:
    """
    增强版智能评估器
    
    提供完整的评估、查询、建议、追问处理能力
    """
    
    def __init__(self):
        """初始化增强版评估器"""
        self.client = SiliconFlowClient()
        self.intent_classifier = IntentClassifier(self.client)
        self.entity_extractor = EntityExtractor(self.client)
        self.dialogue_manager = DialogueManager(self.client)
        self.cost_calculator = CostCalculator()
        
        # 新增功能模块
        self.cost_query_engine = CostQueryEngine()
        self.suggestion_engine = SuggestionEngine()
        self.knowledge_base = KnowledgeBase()
        self.follow_up_handler = FollowUpHandler()
        
        # 当前评估状态
        self.current_result = None
        self.current_params = None
        self.current_scenario = None
    
    def assess_from_text(self, user_input: str) -> Dict[str, Any]:
        """
        从自然语言文本进行完整评估（增强版）
        
        Args:
            user_input: 用户自然语言描述
        
        Returns:
            评估结果（包含详细报告和建议）
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
            
            # 6. 保存当前状态
            self.current_result = cost_result
            self.current_params = cost_params.dict()
            self.current_scenario = scenario
            
            # 7. 初始化追问处理器
            self.follow_up_handler.set_context(cost_result, self.current_params)
            self.cost_query_engine.set_cost_result(cost_result)
            
            # 8. 生成数据驱动的建议
            suggestions = self.suggestion_engine.generate_suggestions(
                cost_result, 
                self.current_params
            )
            
            # 9. 获取相关知识
            relevant_knowledge = self.knowledge_base.get_relevant_knowledge(
                business_type,
                cost_result.cost_structure
            )
            
            # 10. 生成增强版报告
            enhanced_report = self._generate_enhanced_report(
                cost_result, 
                suggestions, 
                relevant_knowledge
            )
            
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
                "suggestions": suggestions,
                "relevant_knowledge": relevant_knowledge,
                "report": enhanced_report,
                "can_ask_follow_up": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": "评估过程出错",
                "message": str(e)
            }
    
    def _generate_enhanced_report(
        self, 
        cost_result, 
        suggestions, 
        relevant_knowledge
    ) -> str:
        """生成增强版报告"""
        lines = [
            f"\n{'='*60}",
            f"  {cost_result.scenario_name} - 智能成本评估报告",
            f"{'='*60}",
            f"",
            f"【成本汇总】",
            f"  月度总成本: ¥{cost_result.total_monthly_cost:,.2f}",
            f"  单均成本: ¥{cost_result.total_cost_per_order:.2f}",
            f"  单件成本: ¥{cost_result.total_cost_per_item:.2f}",
            f"",
            f"【成本结构分析】",
        ]
        
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
    
    def handle_follow_up(self, user_question: str) -> Dict[str, Any]:
        """
        处理用户追问
        
        Args:
            user_question: 用户问题
        
        Returns:
            回答结果
        """
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
    
    def query_cost_category(self, category: str) -> str:
        """
        查询成本类别详情
        
        Args:
            category: 成本类别
        
        Returns:
            详细报告
        """
        if not self.cost_query_engine.cost_result:
            return "请先完成成本评估"
        
        return self.cost_query_engine.format_category_report(category)
    
    def what_if_analysis(self, param_changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        假设分析
        
        Args:
            param_changes: 参数变化
        
        Returns:
            分析结果
        """
        if not self.cost_query_engine.cost_result:
            return {"error": "请先完成成本评估"}
        
        return self.cost_query_engine.what_if_analysis(param_changes)
    
    def get_cost_insights(self) -> Dict[str, Any]:
        """
        获取成本洞察
        
        Returns:
            洞察信息
        """
        if not self.current_result:
            return {"error": "请先完成成本评估"}
        
        insights = {
            "total_cost": self.current_result.total_monthly_cost,
            "cost_per_order": self.current_result.total_cost_per_order,
            "feasibility": self.current_result.feasibility_rating.value,
            "top_cost_categories": sorted(
                self.current_result.cost_structure.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3],
            "risks": self.current_result.risk_factors,
            "suggestions_count": len(self.current_result.optimization_suggestions)
        }
        
        return insights
    
    def reset(self):
        """重置评估器状态"""
        self.current_result = None
        self.current_params = None
        self.current_scenario = None
        self.follow_up_handler = FollowUpHandler()


if __name__ == "__main__":
    # 测试增强版评估器
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    assessor = EnhancedAssessor()
    
    print("="*60)
    print("增强版智能评估器测试")
    print("="*60)
    
    # 测试评估
    test_input = "我们想接一个企业客户，叫ABC公司，每天100单办公用品，每单5件，重量10公斤，送到20公里外的写字楼，需要上3楼"
    
    print(f"\n输入: {test_input}\n")
    
    result = assessor.assess_from_text(test_input)
    
    if result["success"]:
        print(result["report"])
        
        # 测试追问
        print("\n" + "="*60)
        print("测试追问功能")
        print("="*60)
        
        follow_up_questions = [
            "运输成本为什么这么高？",
            "如果日订单增加到150单会怎样？",
        ]
        
        for question in follow_up_questions:
            print(f"\n用户: {question}")
            response = assessor.handle_follow_up(question)
            print(f"\n系统: {response['answer'][:400]}...")
    else:
        print(f"评估失败: {result['message']}")
