"""
成本计算引擎测试

验证9大环节成本计算的准确性
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.models import CostParameters, InventoryConfig, TransportationConfig, BusinessType
from src.cost_engine import CostCalculator


class TestCostCalculator:
    """成本计算器测试"""
    
    @pytest.fixture
    def calculator(self):
        """创建计算器实例"""
        return CostCalculator()
    
    @pytest.fixture
    def tob_params(self):
        """创建TOB成本参数"""
        return CostParameters(
            monthly_order_count=300,
            monthly_order_lines=1500,
            monthly_items=900,
            inventory_config=InventoryConfig(
                avg_inventory_amount=50000,
                warehouse_area_sqm=50,
                storage_days=5,
            ),
            monthly_packages=300,
            need_cold_packaging=False,
            monthly_distance_km=750,  # 25km * 30天
            monthly_delivery_points=150,
            transportation_config=TransportationConfig(
                use_own_vehicle=True,
                vehicle_type="normal"
            ),
            monthly_loading_hours=150,
            need_upstairs=True,
            total_floors=900,  # 300单 * 3层
            waiting_hours=15,
            monthly_return_items=9,  # 3%退货率
            return_rate=0.01,
            avg_item_cost=50,
        )
    
    @pytest.fixture
    def meal_params(self):
        """创建餐配成本参数"""
        return CostParameters(
            monthly_order_count=1500,
            monthly_order_lines=18000,
            monthly_items=30000,
            inventory_config=InventoryConfig(
                avg_inventory_amount=30000,
                warehouse_area_sqm=30,
                storage_days=3,
            ),
            monthly_packages=1500,
            need_cold_packaging=True,
            monthly_processing_weight=300,  # 10kg * 30天
            monthly_distance_km=450,  # 15km * 30天
            monthly_delivery_points=300,
            transportation_config=TransportationConfig(
                use_own_vehicle=True,
                vehicle_type="cold"
            ),
            monthly_loading_hours=300,
            need_upstairs=False,
            total_floors=0,
            waiting_hours=7.5,
            monthly_return_items=150,  # 5%退货率
            return_rate=0.05,
            avg_item_cost=30,
        )
    
    def test_order_processing_calculation(self, calculator, tob_params):
        """测试订单处理成本计算"""
        cost = calculator._calculate_order_processing(tob_params)
        
        # 预期：1500行 * 2.5元/行 + 300单 * 1元/单 = 4050元
        expected = 1500 * 2.5 + 300 * 1.0
        assert cost == pytest.approx(expected, rel=0.01)
        assert cost > 0
    
    def test_inventory_holding_tob(self, calculator, tob_params):
        """测试TOB库存持有成本"""
        cost = calculator._calculate_inventory_holding(tob_params, BusinessType.TOB_ENTERPRISE.value)
        
        # 资金占用：50000 * 0.05 / 365 * 5 = 34.25
        # 风险成本：50000 * 0.005 = 250
        # 仓储租金：50 * 0.8 * 5 = 200
        # 总计约 484.25
        assert cost > 0
        assert cost == pytest.approx(484.25, rel=0.1)
    
    def test_inventory_holding_meal(self, calculator, meal_params):
        """测试餐配库存持有成本（冷链）"""
        cost = calculator._calculate_inventory_holding(meal_params, BusinessType.MEAL_DELIVERY.value)
        
        # 资金占用：30000 * 0.05 / 365 * 3 = 12.33
        # 风险成本：30000 * 0.03 = 900
        # 仓储租金：30 * 1.6 * 3 = 144
        # 总计约 1056.33
        assert cost > 0
        assert cost > calculator._calculate_inventory_holding(meal_params, BusinessType.TOB_ENTERPRISE.value)  # 冷链应该更贵
    
    def test_picking_tob(self, calculator, tob_params):
        """测试TOB拣选成本"""
        cost = calculator._calculate_picking(tob_params, BusinessType.TOB_ENTERPRISE.value)
        
        # 900件 * 0.5元/件 = 450元
        expected = 900 * 0.5
        assert cost == pytest.approx(expected, rel=0.01)
    
    def test_picking_meal(self, calculator, meal_params):
        """测试餐配拣选成本（冷链）"""
        cost = calculator._calculate_picking(meal_params, BusinessType.MEAL_DELIVERY.value)
        
        # 30000件 * 0.7元/件 = 21000元
        expected = 30000 * 0.7
        assert cost == pytest.approx(expected, rel=0.01)
        assert cost > calculator._calculate_picking(meal_params, BusinessType.TOB_ENTERPRISE.value)
    
    def test_packaging_tob(self, calculator, tob_params):
        """测试TOB包装成本"""
        cost = calculator._calculate_packaging(tob_params, BusinessType.TOB_ENTERPRISE.value)
        
        # 300包 * 2元/包 = 600元
        expected = 300 * 2.0
        assert cost == pytest.approx(expected, rel=0.01)
    
    def test_packaging_meal(self, calculator, meal_params):
        """测试餐配包装成本（冷链）"""
        cost = calculator._calculate_packaging(meal_params, BusinessType.MEAL_DELIVERY.value)
        
        # 1500包 * 5元/包 = 7500元
        expected = 1500 * 5.0
        assert cost == pytest.approx(expected, rel=0.01)
    
    def test_processing_meal(self, calculator, meal_params):
        """测试餐配加工成本"""
        cost = calculator._calculate_processing(meal_params, BusinessType.MEAL_DELIVERY.value)
        
        # 300公斤 * 0.8元/公斤 = 240元
        expected = 300 * 0.8
        assert cost == pytest.approx(expected, rel=0.01)
    
    def test_processing_tob(self, calculator, tob_params):
        """测试TOB加工成本（应为0）"""
        cost = calculator._calculate_processing(tob_params, BusinessType.TOB_ENTERPRISE.value)
        assert cost == 0.0
    
    def test_transportation_tob(self, calculator, tob_params):
        """测试TOB运输成本"""
        cost = calculator._calculate_transportation(tob_params, BusinessType.TOB_ENTERPRISE.value)
        
        # 变动：750公里 * 3.5元/公里 = 2625
        # 固定：120元/天 * 30天 = 3600
        # 总计 6225
        expected = 750 * 3.5 + 120 * 30
        assert cost == pytest.approx(expected, rel=0.01)
    
    def test_transportation_meal(self, calculator, meal_params):
        """测试餐配运输成本（冷链）"""
        cost = calculator._calculate_transportation(meal_params, BusinessType.MEAL_DELIVERY.value)
        
        # 变动：450公里 * 4.8元/公里 = 2160
        # 固定：200元/天 * 30天 = 6000
        # 总计 8160
        expected = 450 * 4.8 + 200 * 30
        assert cost == pytest.approx(expected, rel=0.01)
        # 冷链运输成本应高于常温
        tob_cost = calculator._calculate_transportation(meal_params, BusinessType.TOB_ENTERPRISE.value)
        assert cost >= tob_cost
    
    def test_delivery_with_upstairs(self, calculator, tob_params):
        """测试含上楼的交付成本"""
        cost = calculator._calculate_delivery(tob_params, BusinessType.TOB_ENTERPRISE.value)
        
        # 卸货：300单 * 0.25小时 * 30元/小时 = 2250
        # 上楼：900层 * 10元/层 = 9000
        # 等待：15小时 * 35元/小时 = 525
        # 总计约 11775
        assert cost > 0
        assert cost > 2000  # 应该比纯卸货贵很多
    
    def test_delivery_without_upstairs(self, calculator, meal_params):
        """测试不含上楼的交付成本"""
        cost = calculator._calculate_delivery(meal_params, BusinessType.MEAL_DELIVERY.value)
        
        # 卸货：1500单 * 0.25小时 * 30元/小时 = 11250
        # 等待：7.5小时 * 35元/小时 = 262.5
        # 总计约 11512.5
        assert cost > 0
    
    def test_reverse_logistics(self, calculator, tob_params):
        """测试逆向物流成本"""
        cost = calculator._calculate_reverse_logistics(tob_params, BusinessType.TOB_ENTERPRISE.value)
        
        # 退货运输：1趟 * 50元 = 50
        # 检验：9件 * 2元 = 18
        # 报废：9件 * 50元 * 0.01 = 4.5
        # 总计约 72.5
        assert cost > 0
    
    def test_full_calculation_tob(self, calculator, tob_params):
        """测试TOB完整计算"""
        result = calculator.calculate(
            tob_params, 
            BusinessType.TOB_ENTERPRISE.value,
            "TOB测试场景"
        )
        
        assert result.scenario_name == "TOB测试场景"
        assert result.business_type == BusinessType.TOB_ENTERPRISE.value
        assert result.total_monthly_cost > 0
        assert result.total_cost_per_order > 0
        assert result.total_cost_per_item > 0
        assert len(result.cost_structure) > 0
        assert result.feasibility_rating is not None
        print(f"\nTOB月度总成本: ¥{result.total_monthly_cost:,.2f}")
        print(f"TOB单均成本: ¥{result.total_cost_per_order:,.2f}")
    
    def test_full_calculation_meal(self, calculator, meal_params):
        """测试餐配完整计算"""
        result = calculator.calculate(
            meal_params,
            BusinessType.MEAL_DELIVERY.value,
            "餐配测试场景"
        )
        
        assert result.scenario_name == "餐配测试场景"
        assert result.business_type == BusinessType.MEAL_DELIVERY.value
        assert result.total_monthly_cost > 0
        assert len(result.cost_structure) > 0
        print(f"\n餐配月度总成本: ¥{result.total_monthly_cost:,.2f}")
        print(f"餐配单均成本: ¥{result.total_cost_per_order:,.2f}")
    
    def test_cost_accuracy(self, calculator):
        """测试成本计算准确性 - 验证关键计算逻辑"""
        # 创建一个简单的测试场景，手动验证计算结果
        params = CostParameters(
            monthly_order_count=100,
            monthly_order_lines=500,
            monthly_items=300,
            inventory_config=InventoryConfig(
                avg_inventory_amount=10000,
                warehouse_area_sqm=10,
                storage_days=7,
            ),
            monthly_packages=100,
            need_cold_packaging=False,
            monthly_distance_km=300,
            monthly_delivery_points=50,
            transportation_config=TransportationConfig(
                use_own_vehicle=True,
                vehicle_type="normal"
            ),
            monthly_loading_hours=50,
            need_upstairs=False,
            total_floors=0,
            waiting_hours=0,
            monthly_return_items=0,
            return_rate=0,
            avg_item_cost=50,
        )
        
        result = calculator.calculate(params, BusinessType.TOB_ENTERPRISE.value, "准确性测试")
        
        # 手动计算验证
        # 订单处理：500行 * 2.5 + 100单 * 1 = 1350
        expected_order_processing = 500 * 2.5 + 100 * 1.0
        assert result.breakdown.order_processing == pytest.approx(expected_order_processing, rel=0.01)
        
        # 拣选：300件 * 0.5 = 150
        expected_picking = 300 * 0.5
        assert result.breakdown.picking == pytest.approx(expected_picking, rel=0.01)
        
        # 包装：100包 * 2 = 200
        expected_packaging = 100 * 2.0
        assert result.breakdown.packaging == pytest.approx(expected_packaging, rel=0.01)
        
        # 运输：300公里 * 3.5 + 120 * 30 = 1050 + 3600 = 4650
        expected_transportation = 300 * 3.5 + 120 * 30
        assert result.breakdown.transportation == pytest.approx(expected_transportation, rel=0.01)
        
        print(f"\n准确性测试通过！")
        print(f"订单处理: ¥{result.breakdown.order_processing:.2f} (预期: ¥{expected_order_processing:.2f})")
        print(f"拣选: ¥{result.breakdown.picking:.2f} (预期: ¥{expected_picking:.2f})")
        print(f"包装: ¥{result.breakdown.packaging:.2f} (预期: ¥{expected_packaging:.2f})")
        print(f"运输: ¥{result.breakdown.transportation:.2f} (预期: ¥{expected_transportation:.2f})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
