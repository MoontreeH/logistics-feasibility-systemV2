"""
选择性成本计算器

根据配置的成本环节，选择性计算各环节成本
"""

from typing import Dict, List, Optional, Any
from .calculator import CostCalculator
from ..models.cost_parameters import CostParameters
from ..models.cost_result import CostResult, CostBreakdown, FeasibilityRating
from ..models.cost_link_config import CostLinkConfig, CostLinkType
from ..models.business_scenario import BusinessType


class SelectiveCostCalculator(CostCalculator):
    """
    选择性成本计算器
    
    继承自基础计算器，支持根据环节配置选择性计算
    """
    
    def calculate(
        self, 
        params: CostParameters, 
        business_type: str, 
        scenario_name: str = "未命名场景",
        link_config: Optional[CostLinkConfig] = None
    ) -> CostResult:
        """
        计算总成本（支持选择性计算）
        
        Args:
            params: 成本参数
            business_type: 业务类型
            scenario_name: 场景名称
            link_config: 成本环节配置（如果为None则计算所有环节）
        
        Returns:
            成本计算结果
        """
        # 使用传入的配置或参数中的配置
        config = link_config or params.link_config
        
        if config is None:
            # 没有配置时，使用基础计算（计算所有环节）
            return super().calculate(params, business_type, scenario_name)
        
        breakdown = CostBreakdown()
        calculated_links = []  # 记录实际计算的环节
        skipped_links = []  # 记录跳过的环节
        
        # 1. 订单处理成本
        if self._should_calculate(config, "order_processing"):
            breakdown.order_processing = self._calculate_order_processing(params)
            calculated_links.append("订单处理")
        else:
            skipped_links.append("订单处理")
        
        # 2. 库存持有成本
        if self._should_calculate(config, "inventory_holding"):
            breakdown.inventory_holding = self._calculate_inventory_holding(params, business_type)
            calculated_links.append("库存持有")
        else:
            skipped_links.append("库存持有")
        
        # 3. 拣选作业成本
        if self._should_calculate(config, "picking"):
            breakdown.picking = self._calculate_picking(params, business_type)
            calculated_links.append("拣选作业")
        else:
            skipped_links.append("拣选作业")
        
        # 4. 加工包装成本
        if self._should_calculate(config, "packaging"):
            breakdown.packaging = self._calculate_packaging(params, business_type)
            calculated_links.append("包装")
        else:
            skipped_links.append("包装")
            
        if self._should_calculate(config, "processing"):
            breakdown.processing = self._calculate_processing(params, business_type)
            calculated_links.append("加工")
        else:
            skipped_links.append("加工")
        
        # 5. 集货装车成本
        if self._should_calculate(config, "loading"):
            breakdown.loading = self._calculate_loading(params)
            calculated_links.append("集货装车")
        else:
            skipped_links.append("集货装车")
        
        # 6. 运输配送成本
        if self._should_calculate(config, "transportation"):
            breakdown.transportation = self._calculate_transportation(params, business_type)
            calculated_links.append("运输配送")
        else:
            skipped_links.append("运输配送")
        
        # 7. 末端交付成本
        if self._should_calculate(config, "delivery"):
            breakdown.delivery = self._calculate_delivery(params, business_type)
            calculated_links.append("末端交付")
        else:
            skipped_links.append("末端交付")
        
        # 8. 逆向处理成本
        if self._should_calculate(config, "reverse_logistics"):
            breakdown.reverse_logistics = self._calculate_reverse_logistics(params, business_type)
            calculated_links.append("逆向处理")
        else:
            skipped_links.append("逆向处理")
        
        # 9. 管理及间接费用
        if self._should_calculate(config, "overhead"):
            direct_cost = (
                breakdown.order_processing + breakdown.inventory_holding +
                breakdown.picking + breakdown.packaging + breakdown.processing +
                breakdown.loading + breakdown.transportation + breakdown.delivery +
                breakdown.reverse_logistics
            )
            breakdown.overhead = self._calculate_overhead(direct_cost, params)
            calculated_links.append("管理及间接费用")
        else:
            skipped_links.append("管理及间接费用")
        
        # 计算自定义环节成本
        custom_costs = self._calculate_custom_links(config, params)
        
        # 创建结果对象
        result = CostResult(
            scenario_name=scenario_name,
            business_type=business_type,
            breakdown=breakdown,
        )
        
        # 计算汇总数据
        result.calculate_summary(params.monthly_order_count, params.monthly_items)
        
        # 添加自定义环节成本到总成本
        total_custom_cost = sum(custom_costs.values())
        result.total_monthly_cost += total_custom_cost
        if params.monthly_order_count > 0:
            result.total_cost_per_order = result.total_monthly_cost / params.monthly_order_count
        if params.monthly_items > 0:
            result.total_cost_per_item = result.total_monthly_cost / params.monthly_items
        
        # 评估可行性
        result.feasibility_rating = self._evaluate_feasibility(result.total_cost_per_order, business_type)
        
        # 生成风险提示
        result.risk_factors = self._generate_risk_factors(params, business_type, config)
        
        # 生成优化建议
        result.optimization_suggestions = self._generate_suggestions(result, params, config)
        
        # 保存计算详情
        result.calculation_details = {
            "params": params.dict(),
            "rates_version": "1.0",
            "calculated_links": calculated_links,
            "skipped_links": skipped_links,
            "custom_costs": custom_costs,
            "link_config": config.to_dict() if config else None,
        }
        
        return result
    
    def _should_calculate(self, config: CostLinkConfig, link_name: str) -> bool:
        """
        判断是否应该计算该环节
        
        Args:
            config: 成本环节配置
            link_name: 环节名称（英文）
        
        Returns:
            是否应该计算
        """
        link = config.get_link_by_name(link_name)
        if link:
            return link.is_active
        return True  # 默认计算
    
    def _calculate_custom_links(self, config: CostLinkConfig, params: CostParameters) -> Dict[str, float]:
        """
        计算自定义环节成本
        
        Args:
            config: 成本环节配置
            params: 成本参数
        
        Returns:
            自定义环节成本字典
        """
        custom_costs = {}
        
        for link in config.custom_links:
            if not link.is_active:
                continue
            
            # 根据自定义公式计算成本
            cost = self._calculate_custom_link(link, params)
            if cost > 0:
                custom_costs[link.name] = cost
        
        return custom_costs
    
    def _calculate_custom_link(self, link, params: CostParameters) -> float:
        """
        计算单个自定义环节成本
        
        Args:
            link: 自定义环节信息
            params: 成本参数
        
        Returns:
            成本金额
        """
        if link.custom_rate is None:
            return 0.0
        
        # 根据单位确定计算基数
        unit = link.custom_unit or ""
        
        if "单" in unit or "order" in unit.lower():
            return params.monthly_order_count * link.custom_rate
        elif "件" in unit or "item" in unit.lower():
            return params.monthly_items * link.custom_rate
        elif "公里" in unit or "km" in unit.lower():
            return params.monthly_distance_km * link.custom_rate
        elif "小时" in unit or "hour" in unit.lower():
            # 假设有月工时参数
            return getattr(params, 'monthly_hours', 0) * link.custom_rate
        else:
            # 默认按订单数计算
            return params.monthly_order_count * link.custom_rate
    
    def _generate_risk_factors(
        self, 
        params: CostParameters, 
        business_type: str,
        config: Optional[CostLinkConfig] = None
    ) -> List[str]:
        """
        生成风险提示（考虑环节配置）
        
        Args:
            params: 成本参数
            business_type: 业务类型
            config: 成本环节配置
        
        Returns:
            风险列表
        """
        risks = []
        
        # 只针对启用的环节生成风险
        if config:
            # 退货率风险（仅当逆向处理启用时）
            if (self._should_calculate(config, "reverse_logistics") and 
                params.return_rate > 0.05):
                risks.append(f"退货率较高（{params.return_rate:.1%}），建议关注商品质量")
            
            # 冷链风险（仅当相关环节启用时）
            if (params.need_cold_packaging and 
                business_type == BusinessType.MEAL_DELIVERY.value and
                self._should_calculate(config, "transportation")):
                risks.append("冷链运输存在温度控制风险，建议全程监控")
            
            # 上楼风险（仅当末端交付启用时）
            if (self._should_calculate(config, "delivery") and
                params.need_upstairs and params.no_elevator_count > 0):
                risks.append("无电梯上楼作业效率低，人工成本较高")
            
            # 距离风险（仅当运输配送启用时）
            if self._should_calculate(config, "transportation"):
                avg_distance = params.monthly_distance_km / 30 if params.monthly_order_count > 0 else 0
                if avg_distance > 50:
                    risks.append("配送距离较长，运输成本占比高")
        else:
            # 没有配置时使用基础逻辑
            risks = super()._generate_risk_factors(params, business_type)
        
        return risks
    
    def _generate_suggestions(
        self, 
        result: CostResult, 
        params: CostParameters,
        config: Optional[CostLinkConfig] = None
    ) -> List[str]:
        """
        生成优化建议（考虑环节配置）
        
        Args:
            result: 成本结果
            params: 成本参数
            config: 成本环节配置
        
        Returns:
            建议列表
        """
        suggestions = []
        
        if config:
            # 基于成本结构的建议
            if (self._should_calculate(config, "transportation") and
                result.cost_structure.get('运输配送', 0) > 30):
                suggestions.append("运输成本占比较高，建议优化配送路线或增加装载率")
            
            if (self._should_calculate(config, "inventory_holding") and
                result.cost_structure.get('库存持有', 0) > 15):
                suggestions.append("库存成本较高，建议优化库存周转率")
            
            # 基于业务特征的建议
            if params.monthly_order_count > 0 and params.monthly_items / params.monthly_order_count < 5:
                suggestions.append("单均件数较少，建议推广批量订单以摊薄固定成本")
            
            if self._should_calculate(config, "delivery") and params.need_upstairs:
                suggestions.append("上楼配送成本高，建议与客户协商楼下交货或收取上楼费")
            
            # 针对未启用环节的建议
            inactive_links = [l.name for l in config.get_all_links() if not l.is_active and not l.is_custom]
            if "逆向处理" in inactive_links and params.return_rate > 0.03:
                suggestions.append("当前未计算逆向处理成本，但实际退货率较高，建议考虑退货处理成本")
        else:
            # 没有配置时使用基础逻辑
            suggestions = super()._generate_suggestions(result, params)
        
        return suggestions


def calculate_with_link_config(
    params: CostParameters,
    business_type: str,
    scenario_name: str,
    link_config: CostLinkConfig
) -> CostResult:
    """
    使用环节配置计算成本的便捷函数
    
    Args:
        params: 成本参数
        business_type: 业务类型
        scenario_name: 场景名称
        link_config: 成本环节配置
    
    Returns:
        成本计算结果
    """
    calculator = SelectiveCostCalculator()
    return calculator.calculate(params, business_type, scenario_name, link_config)
