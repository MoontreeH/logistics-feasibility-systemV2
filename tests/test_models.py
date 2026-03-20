"""
数据模型测试
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.models import (
    BusinessScenario, 
    BusinessType, 
    DeliveryRequirement,
    CostParameters,
    CostResult,
    CostBreakdown,
    FeasibilityRating
)


class TestBusinessScenario:
    """业务场景模型测试"""
    
    def test_create_tob_scenario(self):
        """测试创建TOB场景"""
        scenario = BusinessScenario(
            business_type=BusinessType.TOB_ENTERPRISE,
            scenario_name="测试客户",
            daily_order_count=10,
            avg_items_per_order=5,
            avg_weight_kg=10.0,
            delivery_distance_km=20.0,
        )
        
        assert scenario.business_type == BusinessType.TOB_ENTERPRISE
        assert scenario.scenario_name == "测试客户"
        assert scenario.daily_order_count == 10
        assert scenario.expected_return_rate == 0.01  # 默认值
        assert not scenario.need_cold_chain  # TOB默认不需要冷链
    
    def test_create_meal_scenario(self):
        """测试创建餐配场景"""
        scenario = BusinessScenario(
            business_type=BusinessType.MEAL_DELIVERY,
            scenario_name="测试餐厅",
            daily_order_count=20,
            avg_items_per_order=10,
            avg_weight_kg=15.0,
            delivery_distance_km=15.0,
        )
        
        assert scenario.business_type == BusinessType.MEAL_DELIVERY
        assert scenario.expected_return_rate == 0.05  # 餐配默认5%
        assert scenario.need_cold_chain  # 餐配默认需要冷链
    
    def test_monthly_volume_calculation(self):
        """测试月度业务量计算"""
        scenario = BusinessScenario(
            business_type=BusinessType.TOB_ENTERPRISE,
            scenario_name="测试",
            daily_order_count=10,
            avg_order_lines=5,
            avg_items_per_order=3,
            avg_weight_kg=10.0,
            delivery_distance_km=20.0,
        )
        
        volume = scenario.get_monthly_volume()
        assert volume["monthly_orders"] == 300  # 10 * 30
        assert volume["monthly_items"] == 900  # 10 * 30 * 3
        assert volume["monthly_lines"] == 1500  # 10 * 30 * 5
    
    def test_delivery_requirement(self):
        """测试交付要求"""
        req = DeliveryRequirement(
            need_upstairs=True,
            floor=5,
            has_elevator=False,
            waiting_time_hours=1.0
        )
        
        assert req.need_upstairs is True
        assert req.floor == 5
        assert req.has_elevator is False
        assert req.waiting_time_hours == 1.0


class TestCostParameters:
    """成本参数模型测试"""
    
    def test_from_scenario(self):
        """测试从场景创建参数"""
        scenario = BusinessScenario(
            business_type=BusinessType.TOB_ENTERPRISE,
            scenario_name="测试",
            daily_order_count=10,
            avg_order_lines=5,
            avg_items_per_order=3,
            avg_weight_kg=10.0,
            delivery_distance_km=20.0,
            delivery_requirement=DeliveryRequirement(
                need_upstairs=True,
                floor=3,
                has_elevator=True
            ),
            expected_return_rate=0.02,
        )
        
        params = CostParameters.from_scenario(scenario)
        
        assert params.monthly_order_count == 300
        assert params.monthly_items == 900
        assert params.monthly_distance_km == 600  # 20 * 30
        assert params.need_upstairs is True
        assert params.return_rate == 0.02


class TestCostResult:
    """成本结果模型测试"""
    
    def test_cost_breakdown_total(self):
        """测试成本明细汇总"""
        breakdown = CostBreakdown(
            order_processing=100.0,
            inventory_holding=200.0,
            picking=150.0,
            packaging=100.0,
            transportation=300.0,
            delivery=50.0,
            overhead=100.0
        )
        
        total = breakdown.get_total()
        assert total == 1000.0
    
    def test_calculate_summary(self):
        """测试汇总计算"""
        result = CostResult(
            scenario_name="测试",
            business_type="tob_enterprise",
            breakdown=CostBreakdown(
                order_processing=100.0,
                picking=200.0,
                transportation=300.0,
            )
        )
        
        result.calculate_summary(monthly_order_count=100, monthly_item_count=300)
        
        assert result.total_monthly_cost == 600.0
        assert result.total_cost_per_order == 6.0
        assert result.total_cost_per_item == 2.0
        assert "订单处理" in result.cost_structure
        assert "运输配送" in result.cost_structure
    
    def test_report_generation(self):
        """测试报告生成"""
        result = CostResult(
            scenario_name="测试场景",
            business_type="tob_enterprise",
            breakdown=CostBreakdown(order_processing=100.0),
            feasibility_rating=FeasibilityRating.HIGH,
            risk_factors=["测试风险"],
            optimization_suggestions=["测试建议"]
        )
        result.calculate_summary(10, 30)
        
        report = result.to_report()
        
        assert "测试场景" in report
        assert "tob_enterprise" in report
        assert "月度总成本" in report
        assert "高可行性" in report or "high" in report
        assert "测试风险" in report
        assert "测试建议" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
