"""
成本结果模型

定义成本计算结果的数据结构
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class FeasibilityRating(str, Enum):
    """可行性评级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CostBreakdown(BaseModel):
    """
    成本明细
    
    9大环节的成本明细
    """
    # 1. 订单处理
    order_processing: float = Field(default=0, description="订单处理成本")
    
    # 2. 库存持有
    inventory_holding: float = Field(default=0, description="库存持有成本")
    
    # 3. 拣选作业
    picking: float = Field(default=0, description="拣选作业成本")
    
    # 4. 加工包装
    packaging: float = Field(default=0, description="包装成本")
    processing: float = Field(default=0, description="加工成本")
    
    # 5. 集货装车
    loading: float = Field(default=0, description="集货装车成本")
    
    # 6. 运输配送
    transportation: float = Field(default=0, description="运输配送成本")
    
    # 7. 末端交付
    delivery: float = Field(default=0, description="末端交付成本")
    
    # 8. 逆向处理
    reverse_logistics: float = Field(default=0, description="逆向处理成本")
    
    # 9. 管理分摊
    overhead: float = Field(default=0, description="管理及间接费用")
    
    def get_total(self) -> float:
        """计算总成本"""
        return (
            self.order_processing +
            self.inventory_holding +
            self.picking +
            self.packaging +
            self.processing +
            self.loading +
            self.transportation +
            self.delivery +
            self.reverse_logistics +
            self.overhead
        )
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            "订单处理": self.order_processing,
            "库存持有": self.inventory_holding,
            "拣选作业": self.picking,
            "加工包装": self.packaging + self.processing,
            "集货装车": self.loading,
            "运输配送": self.transportation,
            "末端交付": self.delivery,
            "逆向处理": self.reverse_logistics,
            "管理分摊": self.overhead,
        }


class CostResult(BaseModel):
    """
    成本计算结果
    
    包含总成本、单位成本、成本结构、可行性评级等
    """
    
    # 基本信息
    scenario_name: str = Field(..., description="场景名称")
    business_type: str = Field(..., description="业务类型")
    
    # 成本明细
    breakdown: CostBreakdown = Field(default_factory=CostBreakdown)
    
    # 汇总数据
    total_monthly_cost: float = Field(default=0, description="月度总成本")
    total_cost_per_order: float = Field(default=0, description="单均成本")
    total_cost_per_item: float = Field(default=0, description="单件成本")
    
    # 成本结构分析
    cost_structure: Dict[str, float] = Field(default_factory=dict, description="成本结构占比")
    
    # 可行性评估
    feasibility_rating: FeasibilityRating = Field(default=FeasibilityRating.MEDIUM, description="可行性评级")
    gross_margin_estimate: Optional[float] = Field(default=None, description="预估毛利率")
    
    # 风险提示
    risk_factors: List[str] = Field(default_factory=list, description="风险因素")
    
    # 优化建议
    optimization_suggestions: List[str] = Field(default_factory=list, description="优化建议")
    
    # 计算详情
    calculation_details: Dict[str, Any] = Field(default_factory=dict, description="计算详情")
    
    def calculate_summary(self, monthly_order_count: int, monthly_item_count: int):
        """计算汇总数据"""
        self.total_monthly_cost = self.breakdown.get_total()
        if monthly_order_count > 0:
            self.total_cost_per_order = self.total_monthly_cost / monthly_order_count
        if monthly_item_count > 0:
            self.total_cost_per_item = self.total_monthly_cost / monthly_item_count
        
        # 计算成本结构占比
        total = self.total_monthly_cost
        if total > 0:
            breakdown_dict = self.breakdown.to_dict()
            self.cost_structure = {
                k: round(v / total * 100, 2) 
                for k, v in breakdown_dict.items() 
                if v > 0
            }
    
    def to_report(self) -> str:
        """生成文本报告"""
        lines = [
            f"=== {self.scenario_name} 成本评估报告 ===",
            f"业务类型: {self.business_type}",
            "",
            "【成本汇总】",
            f"月度总成本: ¥{self.total_monthly_cost:,.2f}",
            f"单均成本: ¥{self.total_cost_per_order:,.2f}",
            f"单件成本: ¥{self.total_cost_per_item:,.2f}",
            "",
            "【成本明细】",
        ]
        
        for name, cost in self.breakdown.to_dict().items():
            if cost > 0:
                lines.append(f"  {name}: ¥{cost:,.2f}")
        
        lines.extend([
            "",
            "【成本结构】",
        ])
        
        for name, pct in sorted(self.cost_structure.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {name}: {pct}%")
        
        lines.extend([
            "",
            f"【可行性评级】 {self.feasibility_rating.value}",
        ])
        
        if self.risk_factors:
            lines.extend(["", "【风险提示】"])
            for risk in self.risk_factors:
                lines.append(f"  ⚠️ {risk}")
        
        if self.optimization_suggestions:
            lines.extend(["", "【优化建议】"])
            for suggestion in self.optimization_suggestions:
                lines.append(f"  💡 {suggestion}")
        
        return "\n".join(lines)
