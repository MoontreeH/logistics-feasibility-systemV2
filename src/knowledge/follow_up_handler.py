"""
追问处理模块

处理用户的追问，支持临时计算和灵活应答
"""

import re
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from ..models.cost_result import CostResult
from .cost_query import CostQueryEngine


@dataclass
class ConversationContext:
    """对话上下文"""
    current_result: Optional[CostResult] = None
    current_params: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    last_query: Optional[str] = None
    last_category: Optional[str] = None


class FollowUpHandler:
    """
    追问处理器
    
    处理用户对评估结果的追问，包括：
    - 环节成本查询
    - 假设分析（What-If）
    - 对比分析
    - 一般性咨询
    """
    
    def __init__(self):
        """初始化追问处理器"""
        self.context = ConversationContext()
        self.query_engine = CostQueryEngine()
        
        # 注册查询处理器
        self.query_handlers: Dict[str, Callable] = {
            "category_query": self._handle_category_query,
            "component_query": self._handle_component_query,
            "what_if": self._handle_what_if,
            "comparison": self._handle_comparison,
            "general": self._handle_general_query,
        }
    
    def set_context(self, cost_result: CostResult, params: Dict[str, Any]):
        """设置对话上下文"""
        self.context.current_result = cost_result
        self.context.current_params = params
        self.query_engine.set_cost_result(cost_result)
    
    def handle_follow_up(self, user_question: str) -> Dict[str, Any]:
        """
        处理用户追问
        
        Args:
            user_question: 用户问题
        
        Returns:
            回答结果
        """
        # 记录对话历史
        self.context.conversation_history.append({
            "role": "user",
            "content": user_question
        })
        
        # 识别问题类型
        question_type = self._classify_question(user_question)
        
        # 调用对应处理器
        handler = self.query_handlers.get(question_type, self._handle_general_query)
        response = handler(user_question)
        
        # 记录回答
        self.context.conversation_history.append({
            "role": "assistant",
            "content": response.get("text_answer", "")
        })
        
        self.context.last_query = user_question
        
        return response
    
    def _classify_question(self, question: str) -> str:
        """
        分类用户问题类型
        
        Args:
            question: 用户问题
        
        Returns:
            问题类型
        """
        question_lower = question.lower()
        
        # 环节成本查询
        category_keywords = [
            "订单处理", "库存", "拣选", "包装", "运输", "配送", 
            "末端", "逆向", "管理", "成本构成", "怎么算", "为什么"
        ]
        for kw in category_keywords:
            if kw in question:
                return "category_query"
        
        # 具体组件查询
        component_keywords = ["上楼费", "冷链", "燃油", "租金", "人工"]
        for kw in component_keywords:
            if kw in question:
                return "component_query"
        
        # 假设分析
        what_if_keywords = ["如果", "假设", "改成", "增加到", "减少到", "会怎样"]
        for kw in what_if_keywords:
            if kw in question:
                return "what_if"
        
        # 对比分析
        comparison_keywords = ["对比", "比较", "差异", "区别", "哪个更"]
        for kw in comparison_keywords:
            if kw in question:
                return "comparison"
        
        return "general"
    
    def _handle_category_query(self, question: str) -> Dict[str, Any]:
        """处理环节成本查询"""
        if not self.context.current_result:
            return {
                "type": "error",
                "text_answer": "请先完成成本评估，再查询具体环节"
            }
        
        # 识别查询的环节
        category_map = {
            "订单处理": "order_processing",
            "库存": "inventory_holding",
            "拣选": "picking",
            "包装": "packaging",
            "加工": "processing",
            "装车": "loading",
            "运输": "transportation",
            "配送": "delivery",
            "末端": "delivery",
            "逆向": "reverse_logistics",
            "退货": "reverse_logistics",
            "管理": "overhead",
        }
        
        category = None
        for cn_name, en_name in category_map.items():
            if cn_name in question:
                category = en_name
                self.context.last_category = en_name
                break
        
        # 如果没有识别到，使用上次查询的类别
        if not category and self.context.last_category:
            category = self.context.last_category
        
        if not category:
            return {
                "type": "category_query",
                "text_answer": "请明确您想查询哪个环节的成本，例如：订单处理、运输配送、末端交付等"
            }
        
        # 获取详细报告
        report = self.query_engine.format_category_report(category)
        
        # 提取关键数据
        detail = self.query_engine.query_category(category)
        
        return {
            "type": "category_query",
            "text_answer": report,
            "data": {
                "category": category,
                "category_name": detail.category_name if detail else category,
                "total_cost": detail.total_cost if detail else 0,
                "percentage": detail.percentage if detail else 0,
                "components": [
                    {
                        "name": c.name,
                        "amount": c.amount,
                        "formula": c.formula
                    }
                    for c in (detail.components if detail else [])
                ]
            }
        }
    
    def _handle_component_query(self, question: str) -> Dict[str, Any]:
        """处理组件查询"""
        if not self.context.current_result:
            return {
                "type": "error",
                "text_answer": "请先完成成本评估"
            }
        
        # 查询组件
        result = self.query_engine.query_component(question)
        
        if result:
            text_answer = f"""
【{result['component']}详情】
所属类别: {result['category']}
总成本: ¥{result['total_cost']:,.2f}
占比: {result['percentage']:.2f}%

成本构成:
"""
            for comp in result['details']:
                text_answer += f"  • {comp.name}: ¥{comp.amount:,.2f}\n"
                text_answer += f"    计算公式: {comp.formula}\n"
            
            return {
                "type": "component_query",
                "text_answer": text_answer,
                "data": result
            }
        else:
            return {
                "type": "component_query",
                "text_answer": f"未找到'{question}'的相关成本信息，请尝试查询具体的成本环节"
            }
    
    def _handle_what_if(self, question: str) -> Dict[str, Any]:
        """处理假设分析"""
        if not self.context.current_result:
            return {
                "type": "error",
                "text_answer": "请先完成成本评估"
            }
        
        # 提取参数变化
        param_changes = self._extract_param_changes(question)
        
        if not param_changes:
            return {
                "type": "what_if",
                "text_answer": "请明确您想调整的参数，例如：'如果日订单增加到200单会怎样？'"
            }
        
        # 执行假设分析
        result = self.query_engine.what_if_analysis(param_changes)
        
        if "error" in result:
            return {
                "type": "what_if",
                "text_answer": f"分析失败: {result['error']}"
            }
        
        text_answer = f"""
【假设分析结果】

参数调整: {result['param_changes']}

成本变化:
  原成本: ¥{result['original_cost']:,.2f}/月
  新成本: ¥{result['new_cost']:,.2f}/月
  差异: ¥{result['difference']:+,.2f}/月 ({result['difference_pct']:+.1f}%)

新单均成本: ¥{result['new_cost_per_order']:.2f}
可行性评级: {result['new_feasibility']}

结论: {result['conclusion']}
"""
        
        return {
            "type": "what_if",
            "text_answer": text_answer,
            "data": result
        }
    
    def _extract_param_changes(self, question: str) -> Dict[str, Any]:
        """从问题中提取参数变化"""
        changes = {}
        
        # 日订单数
        order_match = re.search(r'(\d+)\s*单', question)
        if order_match and ('订单' in question or '单量' in question):
            daily_orders = int(order_match.group(1))
            changes['monthly_order_count'] = daily_orders * 30
        
        # 距离
        distance_match = re.search(r'(\d+(?:\.\d+)?)\s*公里', question)
        if distance_match and ('距离' in question or '公里' in question):
            distance = float(distance_match.group(1))
            # 假设每天配送，月距离 = 日距离 * 30
            daily_distance = distance  # 简化处理
            changes['monthly_distance_km'] = daily_distance * 30
        
        # 件数
        items_match = re.search(r'(\d+)\s*件', question)
        if items_match and ('件' in question or '数量' in question):
            items = int(items_match.group(1))
            # 需要根据当前订单数计算总件数
            if self.context.current_params:
                monthly_orders = self.context.current_params.get('monthly_order_count', 300)
                daily_orders = monthly_orders / 30
                changes['monthly_items'] = int(daily_orders * items)
        
        # 上楼
        if '不上楼' in question or '楼下' in question:
            changes['need_upstairs'] = False
            changes['total_floors'] = 0
        elif '上楼' in question:
            changes['need_upstairs'] = True
        
        return changes
    
    def _handle_comparison(self, question: str) -> Dict[str, Any]:
        """处理对比分析"""
        return {
            "type": "comparison",
            "text_answer": "对比分析功能需要两个场景数据。请先使用'假设分析'功能创建对比场景。"
        }
    
    def _handle_general_query(self, question: str) -> Dict[str, Any]:
        """处理一般性查询"""
        # 使用LLM生成回答
        from ..llm import SiliconFlowClient
        
        client = SiliconFlowClient()
        
        # 构建上下文
        context_info = ""
        if self.context.current_result:
            context_info = f"""
当前评估结果:
- 业务类型: {self.context.current_result.business_type}
- 月度总成本: ¥{self.context.current_result.total_monthly_cost:,.2f}
- 单均成本: ¥{self.context.current_result.total_cost_per_order:.2f}
- 可行性评级: {self.context.current_result.feasibility_rating.value}
"""
        
        prompt = f"""你是物流成本专家，请回答用户的问题。

{context_info}

用户问题: {question}

请基于以上信息，给出专业、简洁的回答。如果问题与当前评估无关，请说明。"""
        
        try:
            response = client.chat_completion(
                messages=[
                    {"role": "system", "content": "你是物流成本分析专家"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            answer = response["choices"][0]["message"]["content"]
            
            return {
                "type": "general",
                "text_answer": answer
            }
        
        except Exception as e:
            return {
                "type": "general",
                "text_answer": f"抱歉，我无法回答这个问题。错误: {str(e)}"
            }
    
    def get_conversation_summary(self) -> str:
        """获取对话摘要"""
        if not self.context.conversation_history:
            return "暂无对话记录"
        
        lines = ["\n【对话记录】"]
        for msg in self.context.conversation_history:
            role = "用户" if msg["role"] == "user" else "系统"
            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)


if __name__ == "__main__":
    # 测试追问处理
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    from src.models import BusinessScenario, BusinessType, DeliveryRequirement, CostParameters
    from src.cost_engine import CostCalculator
    
    # 创建测试场景
    scenario = BusinessScenario(
        business_type=BusinessType.TOB_ENTERPRISE,
        scenario_name="测试场景",
        daily_order_count=100,
        avg_order_lines=5,
        avg_items_per_order=5,
        avg_weight_kg=10.0,
        delivery_distance_km=20.0,
        delivery_requirement=DeliveryRequirement(need_upstairs=True, floor=3),
    )
    
    # 计算成本
    params = CostParameters.from_scenario(scenario)
    calculator = CostCalculator()
    result = calculator.calculate(params, "tob_enterprise", "测试")
    
    # 创建追问处理器
    handler = FollowUpHandler()
    handler.set_context(result, params.dict())
    
    # 测试追问
    test_questions = [
        "运输成本为什么这么高？",
        "如果日订单增加到150单会怎样？",
        "上楼费具体是多少？",
    ]
    
    print("="*60)
    print("追问处理测试")
    print("="*60)
    
    for question in test_questions:
        print(f"\n用户: {question}")
        response = handler.handle_follow_up(question)
        print(f"\n系统: {response['text_answer'][:300]}...")
        print("-"*60)
