"""
建议生成引擎

基于数据分析生成量化、可执行的建议
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from ..models.cost_result import CostResult


@dataclass
class Suggestion:
    """建议项"""
    category: str
    title: str
    description: str
    current_cost: float
    potential_savings: float
    savings_percentage: float
    implementation_difficulty: str  # easy/medium/hard
    priority: str  # high/medium/low
    data_support: str  # 数据支持说明
    action_steps: List[str]


class SuggestionEngine:
    """
    建议生成引擎
    
    基于成本数据分析生成量化建议
    """
    
    def __init__(self):
        """初始化建议引擎"""
        self.rates = self._load_rates()
    
    def _load_rates(self) -> Dict[str, Any]:
        """加载费率配置"""
        rates_path = Path(__file__).parent.parent.parent / "config" / "rates.yaml"
        with open(rates_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def generate_suggestions(self, cost_result: CostResult, params: Dict[str, Any] = None) -> List[Suggestion]:
        """
        生成建议列表
        
        Args:
            cost_result: 成本计算结果
            params: 业务参数
        
        Returns:
            建议列表
        """
        suggestions = []
        
        # 获取成本结构
        cost_structure = cost_result.cost_structure
        breakdown = cost_result.breakdown
        
        # 1. 基于成本占比的建议
        suggestions.extend(self._generate_cost_based_suggestions(cost_structure, breakdown, params))
        
        # 2. 基于业务特征的建议
        if params:
            suggestions.extend(self._generate_business_based_suggestions(cost_result, params))
        
        # 3. 基于行业基准的建议
        suggestions.extend(self._generate_benchmark_suggestions(cost_result, params))
        
        # 按优先级和节省金额排序
        suggestions.sort(key=lambda x: (x.priority == 'high', x.savings_percentage), reverse=True)
        
        return suggestions[:5]  # 返回前5条建议
    
    def _generate_cost_based_suggestions(
        self, 
        cost_structure: Dict[str, float], 
        breakdown,
        params: Dict[str, Any]
    ) -> List[Suggestion]:
        """基于成本结构生成建议"""
        suggestions = []
        
        # 运输成本占比高
        transport_pct = cost_structure.get('运输配送', 0)
        if transport_pct > 30:
            current_cost = breakdown.transportation
            # 路线优化可节省10-15%
            savings = current_cost * 0.12
            suggestions.append(Suggestion(
                category="运输优化",
                title="优化配送路线，提升装载率",
                description="当前运输成本占比过高，通过路线优化和装载率提升可显著降低成本",
                current_cost=current_cost,
                potential_savings=savings,
                savings_percentage=12.0,
                implementation_difficulty="medium",
                priority="high",
                data_support=f"运输成本占比{transport_pct:.1f}%，高于行业平均25%。通过路线优化可减少约12%的行驶里程",
                action_steps=[
                    "使用TMS系统进行路线规划",
                    "合并相近区域订单，提高单车装载率至85%以上",
                    "设置配送时间窗口，减少等待时间"
                ]
            ))
        
        # 末端交付占比高
        delivery_pct = cost_structure.get('末端交付', 0)
        if delivery_pct > 25:
            current_cost = breakdown.delivery
            # 协商楼下交货可节省30-50%上楼费
            savings = current_cost * 0.35
            suggestions.append(Suggestion(
                category="末端优化",
                title="协商楼下交货或收取上楼费",
                description="上楼配送成本占比高，建议与客户协商楼下交货或收取上楼费",
                current_cost=current_cost,
                potential_savings=savings,
                savings_percentage=35.0,
                implementation_difficulty="easy",
                priority="high",
                data_support=f"末端交付成本占比{delivery_pct:.1f}%，其中上楼费用约占60%。协商楼下交货可减少35%成本",
                action_steps=[
                    "与客户协商楼下交货",
                    "如必须上楼，收取10-15元/层上楼费",
                    "优先配送有电梯的楼宇"
                ]
            ))
        
        # 库存持有占比高
        inventory_pct = cost_structure.get('库存持有', 0)
        if inventory_pct > 15:
            current_cost = breakdown.inventory_holding
            # 提高周转率可节省20-30%
            savings = current_cost * 0.25
            suggestions.append(Suggestion(
                category="库存优化",
                title="提高库存周转率",
                description="库存持有成本较高，通过提高周转率可降低资金占用和仓储成本",
                current_cost=current_cost,
                potential_savings=savings,
                savings_percentage=25.0,
                implementation_difficulty="medium",
                priority="medium",
                data_support=f"库存持有成本占比{inventory_pct:.1f}%。将周转天数从7天降至5天可减少25%成本",
                action_steps=[
                    "实施JIT（准时制）配送",
                    "优化安全库存设置",
                    "提高需求预测准确性"
                ]
            ))
        
        # 订单处理占比高
        order_pct = cost_structure.get('订单处理', 0)
        if order_pct > 20:
            current_cost = breakdown.order_processing
            # 批量处理可节省15-20%
            savings = current_cost * 0.18
            suggestions.append(Suggestion(
                category="流程优化",
                title="推行批量订单处理",
                description="订单处理成本占比高，通过批量处理可提高人效",
                current_cost=current_cost,
                potential_savings=savings,
                savings_percentage=18.0,
                implementation_difficulty="easy",
                priority="medium",
                data_support=f"订单处理成本占比{order_pct:.1f}%。批量处理可将人均处理行数从1000行/天提升至1200行/天",
                action_steps=[
                    "推行波次拣选",
                    "优化订单合并策略",
                    "引入自动化分拣设备"
                ]
            ))
        
        return suggestions
    
    def _generate_business_based_suggestions(
        self, 
        cost_result: CostResult, 
        params: Dict[str, Any]
    ) -> List[Suggestion]:
        """基于业务特征生成建议"""
        suggestions = []
        
        # 单均件数少
        items_per_order = params.get('avg_items_per_order', 5)
        if items_per_order < 5:
            suggestions.append(Suggestion(
                category="业务优化",
                title="推广批量订单，提高单均件数",
                description="当前单均件数较少，固定成本摊薄不足",
                current_cost=cost_result.total_monthly_cost,
                potential_savings=cost_result.total_monthly_cost * 0.08,
                savings_percentage=8.0,
                implementation_difficulty="medium",
                priority="medium",
                data_support=f"当前单均件数{items_per_order}件，提升至8件可降低单件成本约8%",
                action_steps=[
                    "设置起送量门槛",
                    "推出批量采购优惠",
                    "引导客户合并下单"
                ]
            ))
        
        # 配送距离长
        distance = params.get('delivery_distance_km', 20)
        if distance > 30:
            suggestions.append(Suggestion(
                category="网络优化",
                title="考虑设立前置仓或中转站",
                description="配送距离较长，运输成本高",
                current_cost=cost_result.breakdown.transportation,
                potential_savings=cost_result.breakdown.transportation * 0.20,
                savings_percentage=20.0,
                implementation_difficulty="hard",
                priority="low",
                data_support=f"当前配送距离{distance}公里，超过30公里。设立前置仓可减少20%运输成本",
                action_steps=[
                    "评估前置仓选址",
                    "计算盈亏平衡点",
                    "逐步推进网络优化"
                ]
            ))
        
        # 退货率高
        return_rate = params.get('return_rate', 0.01)
        if return_rate > 0.05:
            suggestions.append(Suggestion(
                category="质量优化",
                title="降低退货率",
                description="退货率较高，增加逆向物流成本",
                current_cost=cost_result.breakdown.reverse_logistics,
                potential_savings=cost_result.breakdown.reverse_logistics * 0.30,
                savings_percentage=30.0,
                implementation_difficulty="medium",
                priority="high",
                data_support=f"当前退货率{return_rate:.1%}，降至3%可减少30%逆向成本",
                action_steps=[
                    "加强出库质检",
                    "优化包装防护",
                    "改善温控管理"
                ]
            ))
        
        return suggestions
    
    def _generate_benchmark_suggestions(
        self, 
        cost_result: CostResult, 
        params: Dict[str, Any]
    ) -> List[Suggestion]:
        """基于行业基准生成建议"""
        suggestions = []
        
        # 单均成本对比
        cost_per_order = cost_result.total_cost_per_order
        
        # TOB业务基准
        if cost_result.business_type == "tob_enterprise":
            benchmark = 50  # TOB行业平均单均成本
            if cost_per_order > benchmark * 1.3:
                gap = cost_per_order - benchmark
                suggestions.append(Suggestion(
                    category="成本对标",
                    title="单均成本高于行业平均，需全面优化",
                    description=f"当前单均成本¥{cost_per_order:.2f}，高于行业平均¥{benchmark:.2f}",
                    current_cost=cost_result.total_monthly_cost,
                    potential_savings=cost_result.total_monthly_cost * 0.15,
                    savings_percentage=15.0,
                    implementation_difficulty="hard",
                    priority="high",
                    data_support=f"行业平均单均成本¥{benchmark:.2f}，当前¥{cost_per_order:.2f}，高出{((cost_per_order/benchmark-1)*100):.1f}%",
                    action_steps=[
                        "全面梳理成本结构",
                        "识别高成本环节",
                        "制定降本计划"
                    ]
                ))
        
        # 餐配业务基准
        else:
            benchmark = 80
            if cost_per_order > benchmark * 1.3:
                suggestions.append(Suggestion(
                    category="成本对标",
                    title="单均成本高于行业平均",
                    description=f"当前单均成本¥{cost_per_order:.2f}，高于行业平均¥{benchmark:.2f}",
                    current_cost=cost_result.total_monthly_cost,
                    potential_savings=cost_result.total_monthly_cost * 0.12,
                    savings_percentage=12.0,
                    implementation_difficulty="hard",
                    priority="high",
                    data_support=f"餐配行业平均单均成本¥{benchmark:.2f}，当前¥{cost_per_order:.2f}",
                    action_steps=[
                        "优化冷链配送网络",
                        "提高装载率",
                        "减少温控损耗"
                    ]
                ))
        
        return suggestions
    
    def format_suggestions(self, suggestions: List[Suggestion]) -> str:
        """
        格式化建议报告
        
        Args:
            suggestions: 建议列表
        
        Returns:
            格式化文本
        """
        if not suggestions:
            return "暂无优化建议"
        
        lines = [
            "\n" + "="*60,
            "【优化建议】（按优先级排序）",
            "="*60,
            ""
        ]
        
        for i, sug in enumerate(suggestions, 1):
            priority_icon = "🔴" if sug.priority == "high" else "🟡" if sug.priority == "medium" else "🟢"
            difficulty_text = {"easy": "容易", "medium": "中等", "hard": "困难"}.get(sug.implementation_difficulty, "未知")
            
            lines.extend([
                f"{priority_icon} 建议{i}: {sug.title}",
                f"   类别: {sug.category} | 实施难度: {difficulty_text} | 优先级: {sug.priority}",
                f"",
                f"   问题描述: {sug.description}",
                f"",
                f"   📊 数据支持: {sug.data_support}",
                f"",
                f"   💰 预期节省: ¥{sug.potential_savings:,.2f}/月 ({sug.savings_percentage:.1f}%)",
                f"",
                f"   📝 行动步骤:",
            ])
            
            for step in sug.action_steps:
                lines.append(f"      • {step}")
            
            lines.append("")
            lines.append("-"*60)
            lines.append("")
        
        # 汇总
        total_savings = sum(s.potential_savings for s in suggestions)
        total_savings_pct = (total_savings / suggestions[0].current_cost * 100) if suggestions else 0
        
        lines.extend([
            "📈 优化潜力汇总",
            f"   预计总节省: ¥{total_savings:,.2f}/月",
            f"   成本降低幅度: {total_savings_pct:.1f}%",
            f"   建议实施数量: {len(suggestions)}项",
            ""
        ])
        
        return "\n".join(lines)


if __name__ == "__main__":
    # 测试建议引擎
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
        avg_items_per_order=3,  # 单均件数少
        avg_weight_kg=10.0,
        delivery_distance_km=20.0,
        delivery_requirement=DeliveryRequirement(need_upstairs=True, floor=3),
        expected_return_rate=0.02,
    )
    
    # 计算成本
    params = CostParameters.from_scenario(scenario)
    calculator = CostCalculator()
    result = calculator.calculate(params, "tob_enterprise", "测试")
    
    # 生成建议
    engine = SuggestionEngine()
    suggestions = engine.generate_suggestions(result, params.dict())
    
    print(engine.format_suggestions(suggestions))
