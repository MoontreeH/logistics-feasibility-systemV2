"""
订单利润评估模型

实现订单可行性综合评估，包括：
- 商品采购成本
- 物流成本
- 销售收入
- 毛利计算
- 可行性判断
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, validator


class ProfitLevel(str, Enum):
    """利润水平评级"""
    EXCELLENT = "excellent"      # 优秀 (>30%)
    GOOD = "good"                # 良好 (20-30%)
    ACCEPTABLE = "acceptable"    # 可接受 (10-20%)
    MARGINAL = "marginal"        # 边际 (5-10%)
    POOR = "poor"                # 较差 (<5%)
    LOSS = "loss"                # 亏损 (<0%)


class OrderFeasibility(str, Enum):
    """订单可行性评级"""
    HIGHLY_RECOMMENDED = "highly_recommended"  # 强烈推荐
    RECOMMENDED = "recommended"                # 推荐
    ACCEPTABLE = "acceptable"                  # 可接受
    CAUTION = "caution"                        # 谨慎
    NOT_RECOMMENDED = "not_recommended"        # 不推荐


class ProductCostInfo(BaseModel):
    """商品成本信息"""
    
    # 采购相关
    purchase_price_per_unit: float = Field(..., ge=0, description="商品采购单价（元）")
    purchase_quantity_per_order: int = Field(default=1, ge=1, description="每单采购数量")
    
    # 供应商相关
    supplier_discount_rate: float = Field(default=0, ge=0, le=1, description="供应商折扣率")
    bulk_discount_threshold: Optional[int] = Field(default=None, description="批量折扣门槛数量")
    bulk_discount_rate: float = Field(default=0, ge=0, le=1, description="批量折扣率")
    
    # 其他成本
    packaging_material_cost: float = Field(default=0, ge=0, description="包装材料成本（元/单）")
    quality_inspection_cost: float = Field(default=0, ge=0, description="质检成本（元/单）")
    
    @property
    def total_purchase_cost_per_order(self) -> float:
        """计算每单总采购成本"""
        base_cost = self.purchase_price_per_unit * self.purchase_quantity_per_order
        
        # 应用供应商折扣
        discount_rate = self.supplier_discount_rate
        if self.bulk_discount_threshold and self.purchase_quantity_per_order >= self.bulk_discount_threshold:
            discount_rate = max(discount_rate, self.bulk_discount_rate)
        
        discounted_cost = base_cost * (1 - discount_rate)
        
        # 加上其他成本
        total = discounted_cost + self.packaging_material_cost + self.quality_inspection_cost
        
        return total


class SalesRevenueInfo(BaseModel):
    """销售收入信息"""
    
    # 定价相关
    selling_price_per_unit: float = Field(..., ge=0, description="商品销售单价（元）")
    sales_quantity_per_order: int = Field(default=1, ge=1, description="每单销售数量")
    
    # 折扣和优惠
    customer_discount_rate: float = Field(default=0, ge=0, le=1, description="客户折扣率")
    promotion_cost_per_order: float = Field(default=0, ge=0, description="促销成本（元/单）")
    
    # 平台费用（如果是平台销售）
    platform_fee_rate: float = Field(default=0, ge=0, le=1, description="平台费率")
    payment_fee_rate: float = Field(default=0.006, ge=0, le=1, description="支付手续费率")
    
    @property
    def gross_revenue_per_order(self) -> float:
        """计算每单毛收入"""
        return self.selling_price_per_unit * self.sales_quantity_per_order
    
    @property
    def net_revenue_per_order(self) -> float:
        """计算每单净收入（扣除折扣和费用）"""
        gross = self.gross_revenue_per_order
        
        # 扣除折扣
        after_discount = gross * (1 - self.customer_discount_rate)
        
        # 扣除平台费用和支付手续费
        after_fees = after_discount * (1 - self.platform_fee_rate - self.payment_fee_rate)
        
        # 扣除促销成本
        net = after_fees - self.promotion_cost_per_order
        
        return max(0, net)


class OrderProfitAssessment(BaseModel):
    """
    订单利润评估
    
    综合评估订单的可行性，包括采购成本、物流成本、销售收入和毛利
    """
    
    # 基本信息
    order_id: Optional[str] = Field(default=None, description="订单标识")
    scenario_name: str = Field(default="未命名订单", description="场景名称")
    
    # 成本信息
    product_cost: Optional[ProductCostInfo] = Field(default=None, description="商品成本信息")
    logistics_cost_per_order: float = Field(default=0, ge=0, description="单均物流成本")
    
    # 收入信息
    sales_revenue: Optional[SalesRevenueInfo] = Field(default=None, description="销售收入信息")
    
    # 计算结果
    total_cost_per_order: float = Field(default=0, description="单均总成本")
    revenue_per_order: float = Field(default=0, description="单均收入")
    gross_profit_per_order: float = Field(default=0, description="单均毛利")
    gross_profit_margin: float = Field(default=0, description="毛利率")
    
    # 评估结果
    profit_level: ProfitLevel = Field(default=ProfitLevel.POOR, description="利润水平")
    feasibility: OrderFeasibility = Field(default=OrderFeasibility.NOT_RECOMMENDED, description="可行性评级")
    
    # 分析建议
    break_even_price: Optional[float] = Field(default=None, description="盈亏平衡售价")
    min_viable_quantity: Optional[int] = Field(default=None, description="最小可行数量")
    suggestions: List[str] = Field(default_factory=list, description="优化建议")
    risk_warnings: List[str] = Field(default_factory=list, description="风险警告")
    
    def calculate(self):
        """执行计算"""
        # 计算总成本
        product_cost = 0
        if self.product_cost:
            product_cost = self.product_cost.total_purchase_cost_per_order
        
        self.total_cost_per_order = product_cost + self.logistics_cost_per_order
        
        # 计算收入
        if self.sales_revenue:
            self.revenue_per_order = self.sales_revenue.net_revenue_per_order
        
        # 计算毛利
        self.gross_profit_per_order = self.revenue_per_order - self.total_cost_per_order
        
        # 计算毛利率
        if self.revenue_per_order > 0:
            self.gross_profit_margin = self.gross_profit_per_order / self.revenue_per_order
        
        # 评估利润水平
        self._evaluate_profit_level()
        
        # 评估可行性
        self._evaluate_feasibility()
        
        # 计算盈亏平衡点
        self._calculate_break_even()
        
        # 生成建议
        self._generate_suggestions()
    
    def _evaluate_profit_level(self):
        """评估利润水平"""
        margin = self.gross_profit_margin
        
        if margin < 0:
            self.profit_level = ProfitLevel.LOSS
        elif margin < 0.05:
            self.profit_level = ProfitLevel.POOR
        elif margin < 0.10:
            self.profit_level = ProfitLevel.MARGINAL
        elif margin < 0.20:
            self.profit_level = ProfitLevel.ACCEPTABLE
        elif margin < 0.30:
            self.profit_level = ProfitLevel.GOOD
        else:
            self.profit_level = ProfitLevel.EXCELLENT
    
    def _evaluate_feasibility(self):
        """评估订单可行性"""
        margin = self.gross_profit_margin
        profit = self.gross_profit_per_order
        
        if margin < 0:
            self.feasibility = OrderFeasibility.NOT_RECOMMENDED
        elif margin < 0.05 or profit < 5:
            self.feasibility = OrderFeasibility.CAUTION
        elif margin < 0.10:
            self.feasibility = OrderFeasibility.ACCEPTABLE
        elif margin < 0.20:
            self.feasibility = OrderFeasibility.RECOMMENDED
        else:
            self.feasibility = OrderFeasibility.HIGHLY_RECOMMENDED
    
    def _calculate_break_even(self):
        """计算盈亏平衡点"""
        if self.product_cost and self.sales_revenue:
            # 计算盈亏平衡售价
            if self.sales_revenue.sales_quantity_per_order > 0:
                cost_per_unit = self.total_cost_per_order / self.sales_revenue.sales_quantity_per_order
                # 考虑费用率
                fee_rate = self.sales_revenue.platform_fee_rate + self.sales_revenue.payment_fee_rate
                self.break_even_price = cost_per_unit / (1 - fee_rate) if fee_rate < 1 else cost_per_unit * 2
        
        # 计算最小可行数量（简化计算）
        if self.gross_profit_per_order > 0:
            # 假设固定成本为1000元
            fixed_cost = 1000
            self.min_viable_quantity = int(fixed_cost / self.gross_profit_per_order) + 1
    
    def _generate_suggestions(self):
        """生成优化建议"""
        suggestions = []
        warnings = []
        
        # 基于利润率的建议
        if self.gross_profit_margin < 0:
            warnings.append("当前定价下订单将亏损，请提高售价或降低成本")
        elif self.gross_profit_margin < 0.05:
            warnings.append("利润率过低，抗风险能力弱")
        
        # 基于成本结构的建议
        if self.logistics_cost_per_order > 0 and self.total_cost_per_order > 0:
            logistics_ratio = self.logistics_cost_per_order / self.total_cost_per_order
            if logistics_ratio > 0.3:
                suggestions.append(f"物流成本占比({logistics_ratio:.1%})较高，建议优化配送方案")
        
        # 基于定价的建议
        if self.break_even_price and self.sales_revenue:
            current_price = self.sales_revenue.selling_price_per_unit
            if current_price < self.break_even_price * 1.1:
                suggestions.append(f"当前售价接近盈亏平衡点，建议提高至¥{self.break_even_price * 1.2:.2f}以上")
        
        # 基于批量的建议
        if self.product_cost and self.product_cost.bulk_discount_threshold:
            current_qty = self.product_cost.purchase_quantity_per_order
            threshold = self.product_cost.bulk_discount_threshold
            if current_qty < threshold:
                suggestions.append(f"采购数量达到{threshold}可享受批量折扣，建议增加采购量")
        
        self.suggestions = suggestions
        self.risk_warnings = warnings
    
    def to_report(self) -> str:
        """生成评估报告"""
        lines = [
            f"\n{'='*60}",
            f"  {self.scenario_name} - 订单可行性评估报告",
            f"{'='*60}",
            f"",
            f"【成本分析】",
            f"  商品采购成本: ¥{self.product_cost.total_purchase_cost_per_order if self.product_cost else 0:.2f}/单",
            f"  物流成本: ¥{self.logistics_cost_per_order:.2f}/单",
            f"  总成本: ¥{self.total_cost_per_order:.2f}/单",
            f"",
            f"【收入分析】",
            f"  销售收入: ¥{self.revenue_per_order:.2f}/单",
            f"",
            f"【利润分析】",
            f"  毛利: ¥{self.gross_profit_per_order:.2f}/单",
            f"  毛利率: {self.gross_profit_margin:.1%}",
            f"  利润水平: {self._get_profit_level_text()}",
            f"",
            f"【可行性评级】 {self._get_feasibility_text()}",
        ]
        
        if self.break_even_price:
            lines.extend([
                f"",
                f"【盈亏平衡分析】",
                f"  盈亏平衡售价: ¥{self.break_even_price:.2f}",
            ])
        
        if self.risk_warnings:
            lines.extend([
                f"",
                f"【⚠️ 风险警告】",
            ])
            for warning in self.risk_warnings:
                lines.append(f"  • {warning}")
        
        if self.suggestions:
            lines.extend([
                f"",
                f"【💡 优化建议】",
            ])
            for suggestion in self.suggestions:
                lines.append(f"  • {suggestion}")
        
        lines.append(f"{'='*60}")
        
        return "\n".join(lines)
    
    def _get_profit_level_text(self) -> str:
        """获取利润水平文本"""
        level_texts = {
            ProfitLevel.EXCELLENT: "优秀 (>30%)",
            ProfitLevel.GOOD: "良好 (20-30%)",
            ProfitLevel.ACCEPTABLE: "可接受 (10-20%)",
            ProfitLevel.MARGINAL: "边际 (5-10%)",
            ProfitLevel.POOR: "较差 (<5%)",
            ProfitLevel.LOSS: "亏损 (<0%)",
        }
        return level_texts.get(self.profit_level, "未知")
    
    def _get_feasibility_text(self) -> str:
        """获取可行性文本"""
        feasibility_texts = {
            OrderFeasibility.HIGHLY_RECOMMENDED: "⭐⭐⭐ 强烈推荐",
            OrderFeasibility.RECOMMENDED: "⭐⭐ 推荐",
            OrderFeasibility.ACCEPTABLE: "⭐ 可接受",
            OrderFeasibility.CAUTION: "⚠️ 谨慎",
            OrderFeasibility.NOT_RECOMMENDED: "❌ 不推荐",
        }
        return feasibility_texts.get(self.feasibility, "未知")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "scenario_name": self.scenario_name,
            "costs": {
                "product_cost": self.product_cost.total_purchase_cost_per_order if self.product_cost else 0,
                "logistics_cost": self.logistics_cost_per_order,
                "total_cost": self.total_cost_per_order,
            },
            "revenue": {
                "net_revenue": self.revenue_per_order,
            },
            "profit": {
                "gross_profit": self.gross_profit_per_order,
                "gross_margin": round(self.gross_profit_margin * 100, 2),
                "profit_level": self.profit_level.value,
            },
            "feasibility": self.feasibility.value,
            "break_even": {
                "break_even_price": self.break_even_price,
                "min_viable_quantity": self.min_viable_quantity,
            },
            "suggestions": self.suggestions,
            "warnings": self.risk_warnings,
        }


class OrderProfitAssessmentInput(BaseModel):
    """
    订单利润评估输入
    
    用于收集用户输入的评估参数
    """
    
    # 商品信息
    product_name: Optional[str] = Field(default=None, description="商品名称")
    purchase_price: Optional[float] = Field(default=None, ge=0, description="采购单价")
    selling_price: Optional[float] = Field(default=None, ge=0, description="销售单价")
    quantity_per_order: int = Field(default=1, ge=1, description="每单数量")
    
    # 其他成本
    additional_cost_per_order: float = Field(default=0, ge=0, description="其他成本/单")
    
    # 折扣信息
    has_bulk_discount: bool = Field(default=False, description="是否有批量折扣")
    bulk_discount_threshold: Optional[int] = Field(default=None, description="批量折扣门槛")
    bulk_discount_rate: float = Field(default=0, ge=0, le=1, description="批量折扣率")
    
    def create_assessment(self, logistics_cost: float) -> OrderProfitAssessment:
        """
        创建订单利润评估对象
        
        Args:
            logistics_cost: 物流成本/单
        
        Returns:
            订单利润评估对象
        """
        # 创建商品成本信息
        product_cost = None
        if self.purchase_price:
            product_cost = ProductCostInfo(
                purchase_price_per_unit=self.purchase_price,
                purchase_quantity_per_order=self.quantity_per_order,
                bulk_discount_threshold=self.bulk_discount_threshold if self.has_bulk_discount else None,
                bulk_discount_rate=self.bulk_discount_rate if self.has_bulk_discount else 0,
            )
        
        # 创建销售收入信息
        sales_revenue = None
        if self.selling_price:
            sales_revenue = SalesRevenueInfo(
                selling_price_per_unit=self.selling_price,
                sales_quantity_per_order=self.quantity_per_order,
            )
        
        # 创建评估对象
        assessment = OrderProfitAssessment(
            scenario_name=self.product_name or "订单评估",
            product_cost=product_cost,
            logistics_cost_per_order=logistics_cost + self.additional_cost_per_order,
            sales_revenue=sales_revenue,
        )
        
        # 执行计算
        assessment.calculate()
        
        return assessment
