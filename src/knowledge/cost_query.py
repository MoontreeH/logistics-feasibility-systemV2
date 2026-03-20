"""
成本查询引擎

支持环节级成本详细查询和分析
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from ..models.cost_result import CostResult, CostBreakdown
from ..cost_engine import CostCalculator
from ..models import CostParameters


@dataclass
class CostComponentDetail:
    """成本组件详情"""
    name: str
    amount: float
    unit: str
    rate: float
    quantity: float
    percentage: float
    description: str
    formula: str


@dataclass
class CostCategoryDetail:
    """成本类别详情"""
    category_name: str
    total_cost: float
    percentage: float
    components: List[CostComponentDetail]
    insights: List[str]


class CostQueryEngine:
    """
    成本查询引擎
    
    提供详细的成本查询和分析功能
    """
    
    # 成本环节中文映射
    CATEGORY_NAMES = {
        "order_processing": "订单处理",
        "inventory_holding": "库存持有",
        "picking": "拣选作业",
        "packaging": "包装",
        "processing": "加工",
        "loading": "集货装车",
        "transportation": "运输配送",
        "delivery": "末端交付",
        "reverse_logistics": "逆向处理",
        "overhead": "管理分摊",
    }
    
    def __init__(self, cost_result: CostResult = None):
        """
        初始化查询引擎
        
        Args:
            cost_result: 成本计算结果
        """
        self.cost_result = cost_result
        self.calculator = CostCalculator()
    
    def set_cost_result(self, cost_result: CostResult):
        """设置成本结果"""
        self.cost_result = cost_result
    
    def query_category(self, category: str) -> Optional[CostCategoryDetail]:
        """
        查询特定成本类别的详细信息
        
        Args:
            category: 成本类别代码
        
        Returns:
            成本类别详情
        """
        if not self.cost_result:
            return None
        
        breakdown = self.cost_result.breakdown
        total_cost = self.cost_result.total_monthly_cost
        
        # 获取类别成本
        category_cost = getattr(breakdown, category, 0)
        if category_cost == 0:
            return None
        
        percentage = (category_cost / total_cost * 100) if total_cost > 0 else 0
        
        # 获取组件详情
        components = self._get_category_components(category, category_cost)
        
        # 生成洞察
        insights = self._generate_category_insights(category, category_cost, percentage)
        
        return CostCategoryDetail(
            category_name=self.CATEGORY_NAMES.get(category, category),
            total_cost=category_cost,
            percentage=percentage,
            components=components,
            insights=insights
        )
    
    def _get_category_components(self, category: str, total: float) -> List[CostComponentDetail]:
        """获取成本类别的组件详情"""
        components = []
        params = self.cost_result.calculation_details.get("params", {}) if self.cost_result else {}
        
        if category == "order_processing":
            # 订单处理 = 按行计费 + 系统摊销
            lines = params.get("monthly_order_lines", 0)
            orders = params.get("monthly_order_count", 0)
            line_cost = lines * 2.5
            system_cost = orders * 1.0
            
            components.append(CostComponentDetail(
                name="按行计费",
                amount=line_cost,
                unit="元/行",
                rate=2.5,
                quantity=lines,
                percentage=(line_cost/total*100) if total > 0 else 0,
                description="订单处理人员薪酬分摊",
                formula=f"{lines}行 × 2.5元/行"
            ))
            
            components.append(CostComponentDetail(
                name="系统摊销",
                amount=system_cost,
                unit="元/单",
                rate=1.0,
                quantity=orders,
                percentage=(system_cost/total*100) if total > 0 else 0,
                description="IT系统维护费用分摊",
                formula=f"{orders}单 × 1.0元/单"
            ))
        
        elif category == "inventory_holding":
            # 库存持有 = 资金成本 + 风险成本 + 仓储租金
            inv_config = params.get("inventory_config", {})
            inv_amount = inv_config.get("avg_inventory_amount", 0)
            storage_days = inv_config.get("storage_days", 7)
            area = inv_config.get("warehouse_area_sqm", 10)
            
            capital_cost = inv_amount * 0.05 / 365 * storage_days
            risk_cost = inv_amount * 0.005
            warehouse_cost = area * 0.8 * storage_days
            
            components.append(CostComponentDetail(
                name="资金占用成本",
                amount=capital_cost,
                unit="年化5%",
                rate=0.05,
                quantity=inv_amount,
                percentage=(capital_cost/total*100) if total > 0 else 0,
                description="库存资金占用成本",
                formula=f"{inv_amount}元 × 5% ÷ 365 × {storage_days}天"
            ))
            
            components.append(CostComponentDetail(
                name="库存风险成本",
                amount=risk_cost,
                unit="比例0.5%",
                rate=0.005,
                quantity=inv_amount,
                percentage=(risk_cost/total*100) if total > 0 else 0,
                description="损耗、过期等风险",
                formula=f"{inv_amount}元 × 0.5%"
            ))
            
            components.append(CostComponentDetail(
                name="仓储租金",
                amount=warehouse_cost,
                unit="元/㎡/天",
                rate=0.8,
                quantity=area * storage_days,
                percentage=(warehouse_cost/total*100) if total > 0 else 0,
                description="仓库租赁费用",
                formula=f"{area}㎡ × 0.8元 × {storage_days}天"
            ))
        
        elif category == "picking":
            items = params.get("monthly_items", 0)
            components.append(CostComponentDetail(
                name="拣货作业",
                amount=total,
                unit="元/件",
                rate=0.5,
                quantity=items,
                percentage=100,
                description="拣货人员薪酬分摊",
                formula=f"{items}件 × 0.5元/件"
            ))
        
        elif category == "transportation":
            distance = params.get("monthly_distance_km", 0)
            variable_cost = distance * 3.5
            fixed_cost = 120 * 30
            
            components.append(CostComponentDetail(
                name="变动成本（燃油）",
                amount=variable_cost,
                unit="元/公里",
                rate=3.5,
                quantity=distance,
                percentage=(variable_cost/total*100) if total > 0 else 0,
                description="车辆燃油费用",
                formula=f"{distance}公里 × 3.5元/公里"
            ))
            
            components.append(CostComponentDetail(
                name="固定成本（折旧）",
                amount=fixed_cost,
                unit="元/天",
                rate=120,
                quantity=30,
                percentage=(fixed_cost/total*100) if total > 0 else 0,
                description="车辆折旧、保险等",
                formula=f"120元/天 × 30天"
            ))
        
        elif category == "delivery":
            orders = params.get("monthly_order_count", 0)
            unloading_cost = orders * 0.25 * 30
            
            components.append(CostComponentDetail(
                name="卸货作业",
                amount=unloading_cost,
                unit="元/小时",
                rate=30,
                quantity=orders * 0.25,
                percentage=(unloading_cost/total*100) if total > 0 else 0,
                description="卸货人工费用",
                formula=f"{orders}单 × 0.25小时 × 30元/小时"
            ))
            
            if total > unloading_cost:
                other_cost = total - unloading_cost
                components.append(CostComponentDetail(
                    name="其他费用",
                    amount=other_cost,
                    unit="元",
                    rate=0,
                    quantity=0,
                    percentage=(other_cost/total*100) if total > 0 else 0,
                    description="上楼费、等待费等",
                    formula="根据具体需求计算"
                ))
        
        else:
            # 其他类别简化处理
            components.append(CostComponentDetail(
                name=self.CATEGORY_NAMES.get(category, category),
                amount=total,
                unit="元",
                rate=0,
                quantity=0,
                percentage=100,
                description="综合成本",
                formula="详见费率配置"
            ))
        
        return components
    
    def _generate_category_insights(self, category: str, cost: float, percentage: float) -> List[str]:
        """生成成本类别洞察"""
        insights = []
        
        if percentage > 30:
            insights.append(f"该环节成本占比高达{percentage:.1f}%，是主要成本驱动因素，建议重点优化")
        elif percentage > 15:
            insights.append(f"该环节成本占比{percentage:.1f}%，属于中等成本项")
        else:
            insights.append(f"该环节成本占比{percentage:.1f}%，属于较低成本项")
        
        # 类别特定洞察
        if category == "transportation":
            insights.append("运输成本与配送距离和频次直接相关，可考虑路线优化")
        elif category == "delivery":
            insights.append("末端交付成本受上楼、等待等因素影响较大")
        elif category == "inventory_holding":
            insights.append("库存成本可通过提高周转率来降低")
        
        return insights
    
    def query_component(self, component_name: str) -> Optional[Dict[str, Any]]:
        """
        查询特定成本组件
        
        Args:
            component_name: 组件名称（如"上楼费"、"冷链包装"等）
        
        Returns:
            组件详情
        """
        if not self.cost_result:
            return None
        
        # 组件映射表
        component_mapping = {
            "上楼费": ("delivery", "上楼费用"),
            "冷链": ("packaging", "冷链包装"),
            "包装": ("packaging", "包装费用"),
            "运输": ("transportation", "运输费用"),
            "仓储": ("inventory_holding", "仓储费用"),
            "拣货": ("picking", "拣货费用"),
        }
        
        for key, (category, desc) in component_mapping.items():
            if key in component_name:
                category_detail = self.query_category(category)
                if category_detail:
                    return {
                        "component": component_name,
                        "category": category_detail.category_name,
                        "description": desc,
                        "total_cost": category_detail.total_cost,
                        "percentage": category_detail.percentage,
                        "details": category_detail.components
                    }
        
        return None
    
    def compare_scenarios(self, scenario_a: CostResult, scenario_b: CostResult) -> Dict[str, Any]:
        """
        对比两个场景的成本
        
        Args:
            scenario_a: 场景A成本结果
            scenario_b: 场景B成本结果
        
        Returns:
            对比分析结果
        """
        diff = scenario_a.total_monthly_cost - scenario_b.total_monthly_cost
        diff_pct = (diff / scenario_b.total_monthly_cost * 100) if scenario_b.total_monthly_cost > 0 else 0
        
        # 各环节对比
        category_comparison = []
        for category in self.CATEGORY_NAMES.keys():
            cost_a = getattr(scenario_a.breakdown, category, 0)
            cost_b = getattr(scenario_b.breakdown, category, 0)
            cat_diff = cost_a - cost_b
            
            if cost_a > 0 or cost_b > 0:
                category_comparison.append({
                    "category": self.CATEGORY_NAMES.get(category, category),
                    "scenario_a": cost_a,
                    "scenario_b": cost_b,
                    "difference": cat_diff,
                    "difference_pct": (cat_diff / cost_b * 100) if cost_b > 0 else 0
                })
        
        # 找出差异最大的环节
        max_diff_category = max(category_comparison, key=lambda x: abs(x["difference"])) if category_comparison else None
        
        return {
            "total_difference": diff,
            "total_difference_pct": diff_pct,
            "scenario_a_cost": scenario_a.total_monthly_cost,
            "scenario_b_cost": scenario_b.total_monthly_cost,
            "category_comparison": category_comparison,
            "max_difference_category": max_diff_category,
            "conclusion": f"场景A比场景B{'高' if diff > 0 else '低'}{abs(diff_pct):.1f}%"
        }
    
    def what_if_analysis(self, param_changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        假设分析（What-If Analysis）
        
        Args:
            param_changes: 参数变化，如{"daily_order_count": 200}
        
        Returns:
            分析结果
        """
        if not self.cost_result or not self.cost_result.calculation_details.get("params"):
            return {"error": "没有基础数据进行分析"}
        
        # 获取原始参数
        original_params = self.cost_result.calculation_details["params"]
        
        # 创建新参数
        new_params = original_params.copy()
        new_params.update(param_changes)
        
        # 重新计算成本
        try:
            from ..models import CostParameters
            cost_params = CostParameters(**new_params)
            
            new_result = self.calculator.calculate(
                cost_params,
                self.cost_result.business_type,
                "假设分析场景"
            )
            
            # 对比结果
            diff = new_result.total_monthly_cost - self.cost_result.total_monthly_cost
            diff_pct = (diff / self.cost_result.total_monthly_cost * 100) if self.cost_result.total_monthly_cost > 0 else 0
            
            return {
                "original_cost": self.cost_result.total_monthly_cost,
                "new_cost": new_result.total_monthly_cost,
                "difference": diff,
                "difference_pct": diff_pct,
                "param_changes": param_changes,
                "conclusion": f"调整后成本{'增加' if diff > 0 else '减少'}{abs(diff_pct):.1f}%",
                "new_cost_per_order": new_result.total_cost_per_order,
                "new_feasibility": new_result.feasibility_rating.value
            }
        
        except Exception as e:
            return {"error": f"分析失败: {str(e)}"}
    
    def format_category_report(self, category: str) -> str:
        """
        格式化成本类别报告
        
        Args:
            category: 成本类别
        
        Returns:
            格式化报告文本
        """
        detail = self.query_category(category)
        if not detail:
            return f"未找到'{category}'的成本信息"
        
        lines = [
            f"\n=== {detail.category_name}成本详情 ===",
            f"",
            f"【成本汇总】",
            f"总成本: ¥{detail.total_cost:,.2f}",
            f"占比: {detail.percentage:.2f}%",
            f"",
            f"【成本构成】",
        ]
        
        for comp in detail.components:
            lines.append(f"  • {comp.name}: ¥{comp.amount:,.2f} ({comp.percentage:.1f}%)")
            lines.append(f"    计算公式: {comp.formula}")
            lines.append(f"    说明: {comp.description}")
            lines.append("")
        
        lines.extend([
            f"【成本洞察】",
        ])
        for insight in detail.insights:
            lines.append(f"  💡 {insight}")
        
        return "\n".join(lines)


if __name__ == "__main__":
    # 测试成本查询引擎
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    from src.models import BusinessScenario, BusinessType, DeliveryRequirement
    
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
    from src.models import CostParameters
    from src.cost_engine import CostCalculator
    
    params = CostParameters.from_scenario(scenario)
    calculator = CostCalculator()
    result = calculator.calculate(params, "tob_enterprise", "测试")
    
    # 创建查询引擎
    query_engine = CostQueryEngine(result)
    
    # 测试查询
    print("="*60)
    print("成本查询引擎测试")
    print("="*60)
    
    # 查询订单处理成本
    print(query_engine.format_category_report("order_processing"))
    
    # 查询运输成本
    print(query_engine.format_category_report("transportation"))
