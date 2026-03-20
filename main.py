"""
物流业务智能可行性评估系统 - 主入口

第一阶段：基础成本计算引擎
"""

import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.models import BusinessScenario, CostParameters
from src.cost_engine import CostCalculator
from src.utils import CLIHelper


def main():
    """主函数"""
    print("欢迎使用物流业务智能可行性评估系统！")
    print("版本: 0.1.0 (MVP阶段)")
    
    while True:
        print("\n" + "="*50)
        print("主菜单")
        print("="*50)
        print("1. 新建业务场景评估")
        print("2. 使用示例数据测试")
        print("3. 退出")
        
        choice = input("\n请选择操作 (1/2/3): ").strip()
        
        if choice == "1":
            run_assessment()
        elif choice == "2":
            run_demo()
        elif choice == "3":
            print("\n感谢使用，再见！")
            break
        else:
            print("无效选项，请重新选择")


def run_assessment():
    """运行评估流程"""
    try:
        # 1. 输入业务场景
        scenario = CLIHelper.prompt_scenario()
        
        print("\n" + "="*50)
        print("正在计算成本，请稍候...")
        print("="*50)
        
        # 2. 转换为成本参数
        params = CostParameters.from_scenario(scenario)
        
        # 3. 计算成本
        calculator = CostCalculator()
        result = calculator.calculate(
            params=params,
            business_type=scenario.business_type.value,
            scenario_name=scenario.scenario_name
        )
        
        # 4. 输出报告
        print("\n" + result.to_report())
        
        # 5. 保存选项
        save_option = input("\n是否保存报告到文件? (y/N): ").strip().lower()
        if save_option in ['y', 'yes', '是']:
            filename = f"report_{scenario.scenario_name.replace(' ', '_')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(result.to_report())
            print(f"报告已保存到: {filename}")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


def run_demo():
    """运行示例数据"""
    print("\n" + "="*50)
    print("示例数据测试")
    print("="*50)
    
    print("\n请选择示例场景:")
    print("1. TOB企业购 - 办公用品配送")
    print("2. 餐配业务 - 餐厅食材配送")
    
    choice = input("\n请选择 (1/2): ").strip()
    
    if choice == "1":
        scenario = create_tob_demo_scenario()
    elif choice == "2":
        scenario = create_meal_demo_scenario()
    else:
        print("无效选项")
        return
    
    print(f"\n示例场景: {scenario.scenario_name}")
    print(f"业务类型: {scenario.business_type.value}")
    print(f"日订单数: {scenario.daily_order_count}")
    print(f"配送距离: {scenario.delivery_distance_km}公里")
    
    print("\n正在计算成本...")
    
    # 计算成本
    params = CostParameters.from_scenario(scenario)
    calculator = CostCalculator()
    result = calculator.calculate(
        params=params,
        business_type=scenario.business_type.value,
        scenario_name=scenario.scenario_name
    )
    
    # 输出报告
    print("\n" + result.to_report())


def create_tob_demo_scenario() -> BusinessScenario:
    """创建TOB示例场景"""
    from src.models import BusinessType, DeliveryRequirement
    
    return BusinessScenario(
        business_type=BusinessType.TOB_ENTERPRISE,
        scenario_name="某科技公司办公用品配送",
        daily_order_count=20,
        avg_order_lines=8,
        avg_items_per_order=15,
        avg_weight_kg=25.0,
        delivery_distance_km=25.0,
        delivery_points=5,
        delivery_requirement=DeliveryRequirement(
            need_upstairs=True,
            floor=3,
            has_elevator=True,
            waiting_time_hours=0.5
        ),
        need_cold_chain=False,
        expected_return_rate=0.01,
        inventory_amount=50000,
        warehouse_area_sqm=50,
        storage_days=5,
        remark="TOB企业购示例"
    )


def create_meal_demo_scenario() -> BusinessScenario:
    """创建餐配示例场景"""
    from src.models import BusinessType, DeliveryRequirement
    
    return BusinessScenario(
        business_type=BusinessType.MEAL_DELIVERY,
        scenario_name="某连锁餐厅食材配送",
        daily_order_count=50,
        avg_order_lines=12,
        avg_items_per_order=20,
        avg_weight_kg=30.0,
        delivery_distance_km=15.0,
        delivery_points=10,
        delivery_requirement=DeliveryRequirement(
            need_upstairs=False,
            floor=1,
            has_elevator=True,
            waiting_time_hours=0.25
        ),
        need_cold_chain=True,
        cold_chain_type="refrigerated",
        need_processing=True,
        processing_weight_kg=10.0,
        expected_return_rate=0.05,
        inventory_amount=30000,
        warehouse_area_sqm=30,
        storage_days=3,
        remark="餐配业务示例"
    )


if __name__ == "__main__":
    main()
