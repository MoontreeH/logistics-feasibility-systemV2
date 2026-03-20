"""
单均成本计算器

以单个订单为基本计算单元，不依赖循环假设
支持临时订单、一次性订单的精确评估
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..models.order_unit import PerOrderParameters, OrderType


class PerOrderCostCalculator:
    """
    单均成本计算器
    
    核心特点：
    - 以"单"为基本计算单元
    - 不需要日订单数、月订单数等循环假设
    - 适用于临时性、一次性订单评估
    - 每个环节的成本都可以单独计算
    """
    
    def __init__(self, rates_config: str = None):
        """
        初始化计算器
        
        Args:
            rates_config: 费率配置文件路径
        """
        if rates_config is None:
            rates_config = Path(__file__).parent.parent.parent / "config" / "rates.yaml"
        
        self.rates = self._load_rates(rates_config)
    
    def _load_rates(self, config_path: Path) -> Dict:
        """加载费率配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except:
            # 返回默认费率
            return self._get_default_rates()
    
    def _get_default_rates(self) -> Dict:
        """获取默认费率"""
        return {
            "order_processing": {"base_fee": 0.5, "per_line_fee": 0.1},
            "inventory_holding": {"daily_rate_per_sqm": 1.5, "capital_cost_rate": 0.0005},
            "picking": {"per_item_fee": 0.3, "per_order_base": 1.0},
            "packaging": {"normal": {"material": 0.5, "labor": 0.3}, "cold": {"material": 2.0, "labor": 0.5}},
            "processing": {"per_kg": 0.5},
            "loading": {"per_order": 1.5, "per_100kg": 0.5},
            "transportation": {"per_km_per_kg": 0.0008, "base_fee": 2.0, "cold_multiplier": 1.5},
            "delivery": {"base": 2.0, "upstairs_per_floor": 0.5, "waiting_per_hour": 10.0},
            "reverse_logistics": {"inspection": 2.0, "repacking": 3.0, "scrap_rate": 0.3},
            "overhead": {"percentage": 0.15},
        }
    
    def calculate(self, params: PerOrderParameters) -> Dict[str, Any]:
        """
        计算单均成本
        
        Args:
            params: 单均参数
        
        Returns:
            成本计算结果
        """
        costs = {}
        cost_breakdown = []
        
        # 1. 订单处理成本
        order_processing = self._calc_order_processing(params)
        costs['order_processing'] = order_processing
        cost_breakdown.append({"环节": "订单处理", "成本": order_processing})
        
        # 2. 拣选作业成本
        picking = self._calc_picking(params)
        costs['picking'] = picking
        cost_breakdown.append({"环节": "拣选作业", "成本": picking})
        
        # 3. 包装成本
        packaging = self._calc_packaging(params)
        costs['packaging'] = packaging
        cost_breakdown.append({"环节": "包装", "成本": packaging})
        
        # 4. 集货装车成本
        loading = self._calc_loading(params)
        costs['loading'] = loading
        cost_breakdown.append({"环节": "集货装车", "成本": loading})
        
        # 5. 运输配送成本
        transportation = self._calc_transportation(params)
        costs['transportation'] = transportation
        cost_breakdown.append({"环节": "运输配送", "成本": transportation})
        
        # 6. 末端交付成本
        delivery = self._calc_delivery(params)
        costs['delivery'] = delivery
        cost_breakdown.append({"环节": "末端交付", "成本": delivery})
        
        # 7. 库存持有（如果有）
        inventory = self._calc_inventory(params)
        if inventory > 0:
            costs['inventory'] = inventory
            cost_breakdown.append({"环节": "库存持有", "成本": inventory})
        
        # 8. 特殊处理（冷链等）
        if params.need_cold_chain:
            cold_cost = self._calc_cold_chain(params)
            costs['cold_chain'] = cold_cost
            cost_breakdown.append({"环节": "冷链处理", "成本": cold_cost})
        
        # 计算总成本
        total_cost = sum(costs.values())
        
        # 计算间接费用（管理分摊）
        overhead_rate = self.rates.get("overhead", {}).get("percentage", 0.15)
        overhead = total_cost * overhead_rate
        costs['overhead'] = overhead
        cost_breakdown.append({"环节": "管理分摊", "成本": overhead})
        
        total_cost += overhead
        
        # 计算成本结构
        cost_structure = {}
        for key, cost in costs.items():
            if total_cost > 0:
                cost_structure[key] = round(cost / total_cost * 100, 1)
        
        return {
            "success": True,
            "params": params,
            "costs": costs,
            "cost_breakdown": cost_breakdown,
            "total_cost": round(total_cost, 2),
            "cost_per_item": round(total_cost / params.items_per_order, 2) if params.items_per_order > 0 else total_cost,
            "cost_structure": cost_structure,
            "order_type": params.order_type.value,
        }
    
    def _calc_order_processing(self, params: PerOrderParameters) -> float:
        """计算订单处理成本"""
        rates = self.rates.get("order_processing", {})
        base = rates.get("base_fee", 0.5)
        per_line = rates.get("per_line_fee", 0.1)
        
        # 按件数计算（订单行数简化为件数）
        cost = base + per_line * params.items_per_order
        return round(cost, 2)
    
    def _calc_picking(self, params: PerOrderParameters) -> float:
        """计算拣选作业成本"""
        rates = self.rates.get("picking", {})
        per_item = rates.get("per_item_fee", 0.3)
        base = rates.get("per_order_base", 1.0)
        
        cost = base + per_item * params.items_per_order
        return round(cost, 2)
    
    def _calc_packaging(self, params: PerOrderParameters) -> float:
        """计算包装成本"""
        rates = self.rates.get("packaging", {})
        
        if params.need_cold_chain:
            pkg_rates = rates.get("cold", {})
        else:
            pkg_rates = rates.get("normal", {})
        
        material = pkg_rates.get("material", 0.5)
        labor = pkg_rates.get("labor", 0.3)
        
        # 包装材料成本按件数计算
        cost = (material + labor) * params.items_per_order
        return round(cost, 2)
    
    def _calc_loading(self, params: PerOrderParameters) -> float:
        """计算集货装车成本"""
        rates = self.rates.get("loading", {})
        per_order = rates.get("per_order", 1.5)
        per_100kg = rates.get("per_100kg", 0.5)
        
        # 装车成本按重量计算
        weight_factor = params.total_weight_kg / 100
        cost = per_order + per_100kg * weight_factor
        return round(cost, 2)
    
    def _calc_transportation(self, params: PerOrderParameters) -> float:
        """计算运输配送成本"""
        rates = self.rates.get("transportation", {})
        per_km_per_kg = rates.get("per_km_per_kg", 0.0008)
        base = rates.get("base_fee", 2.0)
        
        # 运输成本 = 基础费 + 里程费 * 距离 * 重量
        distance_cost = params.distance_km * params.total_weight_kg * per_km_per_kg
        
        # 冷链加成
        multiplier = 1.0
        if params.need_cold_chain:
            multiplier = rates.get("cold_multiplier", 1.5)
        
        cost = (base + distance_cost) * multiplier
        return round(cost, 2)
    
    def _calc_delivery(self, params: PerOrderParameters) -> float:
        """计算末端交付成本"""
        rates = self.rates.get("delivery", {})
        base = rates.get("base", 2.0)
        upstairs_per_floor = rates.get("upstairs_per_floor", 0.5)
        waiting_per_hour = rates.get("waiting_per_hour", 10.0)
        
        cost = base
        
        # 上楼成本
        if params.need_upstairs and not params.has_elevator:
            floor_cost = upstairs_per_floor * params.floor
            cost += floor_cost
        
        return round(cost, 2)
    
    def _calc_inventory(self, params: PerOrderParameters) -> float:
        """计算库存持有成本（简化版）"""
        rates = self.rates.get("inventory_holding", {})
        
        # 库存持有成本主要与重量和存储时间相关
        # 这里简化处理，按件数计算
        if params.items_per_order > 10:
            daily_rate = rates.get("daily_rate_per_sqm", 1.5)
            # 假设每10件占用1平米
            area = params.items_per_order / 10
            # 假设平均存储1天
            cost = area * daily_rate
            return round(cost, 2)
        
        return 0.0
    
    def _calc_cold_chain(self, params: PerOrderParameters) -> float:
        """计算冷链处理成本"""
        rates = self.rates.get("processing", {})
        per_kg = rates.get("per_kg", 0.5)
        
        cost = per_kg * params.total_weight_kg
        return round(cost, 2)
    
    def calculate_profit(self, cost_result: Dict, params: PerOrderParameters) -> Dict:
        """
        计算利润分析
        
        Args:
            cost_result: 成本计算结果
            params: 单均参数
        
        Returns:
            利润分析结果
        """
        if params.purchase_price is None or params.selling_price is None:
            return None
        
        purchase_total = params.purchase_price * params.items_per_order
        selling_total = params.selling_price * params.items_per_order
        
        logistics_cost = cost_result["total_cost"]
        product_cost = purchase_total
        total_cost = product_cost + logistics_cost
        
        revenue = selling_total
        profit = revenue - total_cost
        profit_margin = profit / revenue if revenue > 0 else 0
        
        # 可行性判断
        if profit_margin < 0:
            feasibility = "not_recommended"
            feasibility_label = "❌ 不推荐"
        elif profit_margin < 0.1:
            feasibility = "caution"
            feasibility_label = "⚠️ 谨慎"
        elif profit_margin < 0.2:
            feasibility = "acceptable"
            feasibility_label = "✅ 可接受"
        else:
            feasibility = "recommended"
            feasibility_label = "✅✅ 强烈推荐"
        
        return {
            "product_cost": product_cost,
            "logistics_cost": logistics_cost,
            "total_cost": total_cost,
            "revenue": revenue,
            "profit": profit,
            "profit_margin": profit_margin,
            "feasibility": feasibility,
            "feasibility_label": feasibility_label,
            "break_even_price": round(cost_result["total_cost"] / params.items_per_order, 2) if params.items_per_order > 0 else 0,
        }
    
    def format_result(self, cost_result: Dict, profit_result: Dict = None) -> str:
        """
        格式化结果输出
        
        Args:
            cost_result: 成本计算结果
            profit_result: 利润计算结果（可选）
        
        Returns:
            格式化的报告文本
        """
        params = cost_result["params"]
        
        lines = [
            "\n" + "="*60,
            "📊 单均成本评估报告",
            "="*60,
            "",
            "【订单信息】",
            f"  订单类型: {cost_result['order_type']}",
            f"  每单件数: {params.items_per_order}件",
            f"  单件重量: {params.weight_per_item_kg}kg",
            f"  总重量: {params.total_weight_kg}kg",
            f"  配送距离: {params.distance_km}km",
        ]
        
        if params.need_upstairs:
            lines.append(f"  上楼需求: {params.floor}楼 (电梯: {'有' if params.has_elevator else '无'})")
        
        if params.need_cold_chain:
            lines.append("  冷链需求: 需要")
        
        lines.extend([
            "",
            "【单均成本明细】",
        ])
        
        for item in cost_result["cost_breakdown"]:
            lines.append(f"  {item['环节']}: ¥{item['成本']:.2f}")
        
        lines.extend([
            "",
            "【成本汇总】",
            f"  单均总成本: ¥{cost_result['total_cost']:.2f}",
            f"  单件成本: ¥{cost_result['cost_per_item']:.2f}",
            "",
            "【成本结构】",
        ])
        
        for category, pct in cost_result["cost_structure"].items():
            lines.append(f"  • {category}: {pct:.1f}%")
        
        if profit_result:
            lines.extend([
                "",
                "【利润分析】",
                f"  商品成本: ¥{profit_result['product_cost']:.2f}",
                f"  物流成本: ¥{profit_result['logistics_cost']:.2f}",
                f"  总成本: ¥{profit_result['total_cost']:.2f}",
                f"  销售收入: ¥{profit_result['revenue']:.2f}",
                f"  毛利: ¥{profit_result['profit']:.2f}",
                f"  毛利率: {profit_result['profit_margin']:.1%}",
                f"  可行性: {profit_result['feasibility_label']}",
                f"  盈亏平衡售价: ¥{profit_result['break_even_price']:.2f}/件",
            ])
        
        lines.append("="*60)
        
        return "\n".join(lines)


if __name__ == "__main__":
    # 测试
    print("="*60)
    print("单均成本计算器测试")
    print("="*60)
    
    calculator = PerOrderCostCalculator()
    
    # 测试1: 临时性订单
    print("\n【测试1】临时性订单")
    params1 = PerOrderParameters(
        order_type=OrderType.SINGLE,
        items_per_order=5,
        weight_per_item_kg=10,
        distance_km=20,
        need_upstairs=True,
        floor=3,
        has_elevator=False,
        purchase_price=50,
        selling_price=80,
    )
    
    result1 = calculator.calculate(params1)
    print(f"单均总成本: ¥{result1['total_cost']:.2f}")
    
    profit1 = calculator.calculate_profit(result1, params1)
    if profit1:
        print(f"毛利: ¥{profit1['profit']:.2f}, 毛利率: {profit1['profit_margin']:.1%}")
        print(f"可行性: {profit1['feasibility_label']}")
    
    print(result1['cost_breakdown'])
    
    # 测试2: 循环订单
    print("\n【测试2】每日循环订单")
    params2 = PerOrderParameters(
        order_type=OrderType.DAILY,
        items_per_order=3,
        weight_per_item_kg=5,
        distance_km=15,
        need_cold_chain=True,
    )
    
    result2 = calculator.calculate(params2)
    print(f"单均总成本: ¥{result2['total_cost']:.2f}")
    print(f"成本结构: {result2['cost_structure']}")
