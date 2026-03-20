"""
成本计算引擎

实现9大环节的成本计算
"""

from typing import Dict, List
from .base_calculator import BaseCostCalculator
from ..models.cost_parameters import CostParameters
from ..models.cost_result import CostResult, CostBreakdown, FeasibilityRating
from ..models.business_scenario import BusinessType


class CostCalculator(BaseCostCalculator):
    """
    物流成本计算器
    
    实现9大环节的成本计算逻辑
    """
    
    def calculate(self, params: CostParameters, business_type: str, scenario_name: str = "未命名场景") -> CostResult:
        """
        计算总成本
        
        Args:
            params: 成本参数
            business_type: 业务类型
            scenario_name: 场景名称
        
        Returns:
            成本计算结果
        """
        breakdown = CostBreakdown()
        
        # 1. 订单处理成本
        breakdown.order_processing = self._calculate_order_processing(params)
        
        # 2. 库存持有成本
        breakdown.inventory_holding = self._calculate_inventory_holding(params, business_type)
        
        # 3. 拣选作业成本
        breakdown.picking = self._calculate_picking(params, business_type)
        
        # 4. 加工包装成本
        breakdown.packaging = self._calculate_packaging(params, business_type)
        breakdown.processing = self._calculate_processing(params, business_type)
        
        # 5. 集货装车成本
        breakdown.loading = self._calculate_loading(params)
        
        # 6. 运输配送成本
        breakdown.transportation = self._calculate_transportation(params, business_type)
        
        # 7. 末端交付成本
        breakdown.delivery = self._calculate_delivery(params, business_type)
        
        # 8. 逆向处理成本
        breakdown.reverse_logistics = self._calculate_reverse_logistics(params, business_type)
        
        # 9. 管理及间接费用
        direct_cost = (
            breakdown.order_processing + breakdown.inventory_holding +
            breakdown.picking + breakdown.packaging + breakdown.processing +
            breakdown.loading + breakdown.transportation + breakdown.delivery +
            breakdown.reverse_logistics
        )
        breakdown.overhead = self._calculate_overhead(direct_cost, params)
        
        # 创建结果对象
        result = CostResult(
            scenario_name=scenario_name,
            business_type=business_type,
            breakdown=breakdown,
        )
        
        # 计算汇总数据
        result.calculate_summary(params.monthly_order_count, params.monthly_items)
        
        # 评估可行性
        result.feasibility_rating = self._evaluate_feasibility(result.total_cost_per_order, business_type)
        
        # 生成风险提示
        result.risk_factors = self._generate_risk_factors(params, business_type)
        
        # 生成优化建议
        result.optimization_suggestions = self._generate_suggestions(result, params)
        
        # 保存计算详情
        result.calculation_details = {
            "params": params.dict(),
            "rates_version": "1.0",
        }
        
        return result
    
    # ========== 9大环节成本计算 ==========
    
    def _calculate_order_processing(self, params: CostParameters) -> float:
        """1. 订单处理成本"""
        # 按行计费
        per_line_rate = self.get_rate('order_processing', 'per_line', 2.5)
        line_cost = params.monthly_order_lines * per_line_rate
        
        # 系统摊销
        system_rate = self.get_rate('order_processing', 'system_amortization', 1.0)
        system_cost = params.monthly_order_count * system_rate
        
        return line_cost + system_cost
    
    def _calculate_inventory_holding(self, params: CostParameters, business_type: str) -> float:
        """2. 库存持有成本"""
        inv = params.inventory_config
        
        # 资金占用成本
        capital_rate = self.get_rate('inventory_holding', 'capital_cost', 0.05)
        daily_capital_cost = inv.avg_inventory_amount * capital_rate / 365
        capital_cost = daily_capital_cost * inv.storage_days
        
        # 库存风险成本（损耗、过期）
        risk_rate = self.get_rate_with_business_type(
            'inventory_holding', 'risk_cost', business_type, 0.005
        )
        risk_cost = inv.avg_inventory_amount * risk_rate
        
        # 仓储租金
        if business_type == BusinessType.MEAL_DELIVERY.value:
            warehouse_rate = self.get_rate('inventory_holding', 'warehouse_cold', 1.6)
        else:
            warehouse_rate = self.get_rate('inventory_holding', 'warehouse_normal', 0.8)
        warehouse_cost = inv.warehouse_area_sqm * warehouse_rate * inv.storage_days
        
        return capital_cost + risk_cost + warehouse_cost
    
    def _calculate_picking(self, params: CostParameters, business_type: str) -> float:
        """3. 拣选作业成本"""
        if business_type == BusinessType.MEAL_DELIVERY.value:
            rate = self.get_rate('picking', 'cold', 0.7)
        else:
            rate = self.get_rate('picking', 'normal', 0.5)
        
        return params.monthly_items * rate
    
    def _calculate_packaging(self, params: CostParameters, business_type: str) -> float:
        """4. 包装成本"""
        if params.need_cold_packaging or business_type == BusinessType.MEAL_DELIVERY.value:
            rate = self.get_rate('packaging', 'cold_material', 5.0)
        else:
            rate = self.get_rate('packaging', 'normal_material', 2.0)
        
        return params.monthly_packages * rate
    
    def _calculate_processing(self, params: CostParameters, business_type: str) -> float:
        """4. 加工成本（仅餐配）"""
        if business_type != BusinessType.MEAL_DELIVERY.value or params.monthly_processing_weight <= 0:
            return 0.0
        
        rate = self.get_rate('packaging', 'processing', 0.8)
        return params.monthly_processing_weight * rate
    
    def _calculate_loading(self, params: CostParameters) -> float:
        """5. 集货装车成本"""
        # 人工成本
        labor_rate = self.get_rate('loading', 'labor', 25.0)
        labor_cost = params.monthly_loading_hours * labor_rate
        
        # 设备成本
        equipment_rate = self.get_rate('loading', 'equipment', 5.0)
        equipment_cost = params.monthly_loading_hours * equipment_rate
        
        return labor_cost + equipment_cost
    
    def _calculate_transportation(self, params: CostParameters, business_type: str) -> float:
        """6. 运输配送成本"""
        is_cold = params.transportation_config.vehicle_type == 'cold' or business_type == BusinessType.MEAL_DELIVERY.value
        
        if params.transportation_config.use_own_vehicle:
            if is_cold:
                variable_rate = self.get_rate('transportation', 'cold_vehicle_variable', 4.8)
                fixed_rate = self.get_rate('transportation', 'cold_vehicle_fixed', 200.0)
            else:
                variable_rate = self.get_rate('transportation', 'normal_vehicle_variable', 3.5)
                fixed_rate = self.get_rate('transportation', 'normal_vehicle_fixed', 120.0)
            
            # 变动成本（按里程）
            variable_cost = params.monthly_distance_km * variable_rate
            # 固定成本（按天，假设每天配送）
            fixed_cost = fixed_rate * 30
            
            return variable_cost + fixed_cost
        else:
            # 外包运输
            rate = self.get_rate('transportation', 'outsourcing', 4.0)
            return params.monthly_distance_km * rate
    
    def _calculate_delivery(self, params: CostParameters, business_type: str) -> float:
        """7. 末端交付成本"""
        cost = 0.0
        
        # 卸货成本
        unloading_rate = self.get_rate('delivery', 'unloading', 30.0)
        # 假设每单卸货0.25小时
        unloading_hours = params.monthly_order_count * 0.25
        cost += unloading_hours * unloading_rate
        
        # 上楼费用（仅TOB）
        if business_type == BusinessType.TOB_ENTERPRISE.value and params.need_upstairs:
            upstairs_rate = self.get_rate('delivery', 'upstairs', 10.0)
            cost += params.total_floors * upstairs_rate
            
            # 无电梯附加费
            if params.no_elevator_count > 0:
                no_elevator_rate = self.get_rate('delivery', 'no_elevator', 50.0)
                cost += params.no_elevator_count * no_elevator_rate
        
        # 等待费用
        if params.waiting_hours > 0:
            waiting_rate = self.get_rate('delivery', 'waiting', 35.0)
            cost += params.waiting_hours * waiting_rate
        
        return cost
    
    def _calculate_reverse_logistics(self, params: CostParameters, business_type: str) -> float:
        """8. 逆向处理成本"""
        if params.monthly_return_items == 0:
            return 0.0
        
        cost = 0.0
        
        # 退货运输（假设平均每10件退货需要1趟）
        return_trips = max(1, params.monthly_return_items // 10)
        transport_rate = self.get_rate('reverse_logistics', 'return_transport', 50.0)
        cost += return_trips * transport_rate
        
        # 检验处理
        inspection_rate = self.get_rate('reverse_logistics', 'inspection', 2.0)
        cost += params.monthly_return_items * inspection_rate
        
        # 报废损失
        scrap_rate = self.get_rate_with_business_type(
            'reverse_logistics', 'scrap_loss', business_type, 0.01
        )
        scrap_cost = params.monthly_return_items * params.avg_item_cost * scrap_rate
        cost += scrap_cost
        
        return cost
    
    def _calculate_overhead(self, direct_cost: float, params: CostParameters) -> float:
        """9. 管理及间接费用"""
        # 管理人员薪酬（按直接人工比例）
        management_rate = self.get_rate('overhead', 'management', 0.15)
        management_cost = direct_cost * management_rate
        
        # IT系统摊销
        it_rate = self.get_rate('overhead', 'it_system', 0.5)
        it_cost = params.monthly_order_count * it_rate
        
        # 仓库水电费
        if params.need_cold_packaging:
            utility_rate = self.get_rate_with_business_type('overhead', 'warehouse_utilities', 'meal_delivery', 0.3)
        else:
            utility_rate = self.get_rate_with_business_type('overhead', 'warehouse_utilities', 'tob_enterprise', 0.1)
        utility_cost = params.inventory_config.warehouse_area_sqm * utility_rate * 30
        
        return management_cost + it_cost + utility_cost
    
    # ========== 可行性评估 ==========
    
    def _evaluate_feasibility(self, cost_per_order: float, business_type: str) -> FeasibilityRating:
        """评估可行性"""
        # 根据单均成本评估（实际应用中应考虑收入）
        # 这里简化处理，仅作为示例
        try:
            high_threshold = self.rates['feasibility_rating']['high']['min_margin']
            medium_threshold = self.rates['feasibility_rating']['medium']['min_margin']
        except KeyError:
            high_threshold = 0.15
            medium_threshold = 0.08
        
        # 假设合理的单均成本阈值（需要根据实际业务调整）
        if business_type == BusinessType.TOB_ENTERPRISE.value:
            reasonable_cost = 50  # TOB企业购合理成本
        else:
            reasonable_cost = 80  # 餐配业务合理成本
        
        ratio = cost_per_order / reasonable_cost if reasonable_cost > 0 else 1
        
        if ratio < 0.85:
            return FeasibilityRating.HIGH
        elif ratio < 1.15:
            return FeasibilityRating.MEDIUM
        else:
            return FeasibilityRating.LOW
    
    def _generate_risk_factors(self, params: CostParameters, business_type: str) -> List[str]:
        """生成风险提示"""
        risks = []
        
        # 退货率风险
        if params.return_rate > 0.05:
            risks.append(f"退货率较高（{params.return_rate:.1%}），建议关注商品质量")
        
        # 冷链风险
        if params.need_cold_packaging and business_type == BusinessType.MEAL_DELIVERY.value:
            risks.append("冷链运输存在温度控制风险，建议全程监控")
        
        # 上楼风险
        if params.need_upstairs and params.no_elevator_count > 0:
            risks.append("无电梯上楼作业效率低，人工成本较高")
        
        # 距离风险
        avg_distance = params.monthly_distance_km / 30 if params.monthly_order_count > 0 else 0
        if avg_distance > 50:
            risks.append("配送距离较长，运输成本占比高")
        
        return risks
    
    def _generate_suggestions(self, result: CostResult, params: CostParameters) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        # 基于成本结构的建议
        if result.cost_structure.get('运输配送', 0) > 30:
            suggestions.append("运输成本占比较高，建议优化配送路线或增加装载率")
        
        if result.cost_structure.get('库存持有', 0) > 15:
            suggestions.append("库存成本较高，建议优化库存周转率")
        
        # 基于业务特征的建议
        if params.monthly_order_count > 0 and params.monthly_items / params.monthly_order_count < 5:
            suggestions.append("单均件数较少，建议推广批量订单以摊薄固定成本")
        
        if params.need_upstairs:
            suggestions.append("上楼配送成本高，建议与客户协商楼下交货或收取上楼费")
        
        return suggestions
