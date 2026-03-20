"""
CLI辅助工具

提供命令行交互的辅助函数
"""

from typing import Optional
from ..models.business_scenario import BusinessScenario, BusinessType, DeliveryRequirement


class CLIHelper:
    """命令行交互辅助类"""
    
    @staticmethod
    def prompt_business_type() -> BusinessType:
        """提示选择业务类型"""
        print("\n请选择业务类型:")
        print("1. TOB企业购")
        print("2. 餐配业务")
        
        while True:
            choice = input("请输入选项 (1/2): ").strip()
            if choice == "1":
                return BusinessType.TOB_ENTERPRISE
            elif choice == "2":
                return BusinessType.MEAL_DELIVERY
            else:
                print("无效选项，请重新输入")
    
    @staticmethod
    def prompt_string(prompt: str, default: Optional[str] = None) -> str:
        """提示输入字符串"""
        if default:
            prompt_text = f"{prompt} [{default}]: "
        else:
            prompt_text = f"{prompt}: "
        
        value = input(prompt_text).strip()
        return value if value else default
    
    @staticmethod
    def prompt_int(prompt: str, default: int = 0, min_value: int = 0) -> int:
        """提示输入整数"""
        while True:
            try:
                prompt_text = f"{prompt} [{default}]: " if default else f"{prompt}: "
                value = input(prompt_text).strip()
                if not value:
                    return default
                value = int(value)
                if value < min_value:
                    print(f"输入值不能小于 {min_value}")
                    continue
                return value
            except ValueError:
                print("请输入有效的整数")
    
    @staticmethod
    def prompt_float(prompt: str, default: float = 0.0, min_value: float = 0.0) -> float:
        """提示输入浮点数"""
        while True:
            try:
                prompt_text = f"{prompt} [{default}]: " if default else f"{prompt}: "
                value = input(prompt_text).strip()
                if not value:
                    return default
                value = float(value)
                if value < min_value:
                    print(f"输入值不能小于 {min_value}")
                    continue
                return value
            except ValueError:
                print("请输入有效的数字")
    
    @staticmethod
    def prompt_bool(prompt: str, default: bool = False) -> bool:
        """提示输入布尔值"""
        default_text = "Y/n" if default else "y/N"
        while True:
            value = input(f"{prompt} [{default_text}]: ").strip().lower()
            if not value:
                return default
            if value in ['y', 'yes', '是']:
                return True
            elif value in ['n', 'no', '否']:
                return False
            else:
                print("请输入 y 或 n")
    
    @classmethod
    def prompt_delivery_requirement(cls) -> DeliveryRequirement:
        """提示输入交付要求"""
        print("\n--- 交付要求 ---")
        
        need_upstairs = cls.prompt_bool("是否需要上楼配送", False)
        
        floor = 1
        has_elevator = True
        
        if need_upstairs:
            floor = cls.prompt_int("配送楼层", 1, 1)
            has_elevator = cls.prompt_bool("是否有电梯", True)
        
        waiting_time = cls.prompt_float("预计等待时间（小时）", 0.0, 0.0)
        
        return DeliveryRequirement(
            need_upstairs=need_upstairs,
            floor=floor,
            has_elevator=has_elevator,
            waiting_time_hours=waiting_time
        )
    
    @classmethod
    def prompt_scenario(cls) -> BusinessScenario:
        """交互式输入业务场景"""
        print("\n" + "="*50)
        print("  物流业务智能可行性评估系统")
        print("="*50)
        
        # 业务类型
        business_type = cls.prompt_business_type()
        
        # 基本信息
        print("\n--- 基本信息 ---")
        scenario_name = cls.prompt_string("场景名称/客户名称", "新客户")
        
        # 订单特征
        print("\n--- 订单特征 ---")
        daily_order_count = cls.prompt_int("日订单数", 10, 1)
        avg_order_lines = cls.prompt_int("平均每单行数", 5, 1)
        avg_items_per_order = cls.prompt_int("平均每单件数", 3, 1)
        avg_weight_kg = cls.prompt_float("平均每单重量（公斤）", 5.0, 0.1)
        
        # 配送特征
        print("\n--- 配送特征 ---")
        delivery_distance_km = cls.prompt_float("配送距离（公里）", 20.0, 0.1)
        delivery_points = cls.prompt_int("配送点数", 1, 1)
        
        # 交付要求
        delivery_requirement = cls.prompt_delivery_requirement()
        
        # 冷链要求（餐配默认需要）
        need_cold_chain = business_type == BusinessType.MEAL_DELIVERY
        if not need_cold_chain:
            need_cold_chain = cls.prompt_bool("是否需要冷链", False)
        
        cold_chain_type = None
        if need_cold_chain:
            cold_chain_type = "refrigerated"  # 默认冷藏
        
        # 加工要求（仅餐配）
        need_processing = False
        processing_weight_kg = 0.0
        if business_type == BusinessType.MEAL_DELIVERY:
            need_processing = cls.prompt_bool("是否需要加工", False)
            if need_processing:
                processing_weight_kg = cls.prompt_float("每单加工重量（公斤）", 2.0, 0.1)
        
        # 退货率
        print("\n--- 退货/损耗 ---")
        default_return_rate = 0.05 if business_type == BusinessType.MEAL_DELIVERY else 0.01
        expected_return_rate = cls.prompt_float(
            f"预期退货率（如0.05表示5%）", 
            default_return_rate, 
            0.0
        )
        
        # 库存特征
        print("\n--- 库存特征 ---")
        inventory_amount = cls.prompt_float("平均库存金额（元）", 10000.0, 0.0)
        warehouse_area_sqm = cls.prompt_float("占用仓库面积（平米）", 10.0, 0.1)
        storage_days = cls.prompt_float("平均存储天数", 7.0, 0.1)
        
        # 备注
        remark = cls.prompt_string("备注（可选）")
        
        return BusinessScenario(
            business_type=business_type,
            scenario_name=scenario_name,
            daily_order_count=daily_order_count,
            avg_order_lines=avg_order_lines,
            avg_items_per_order=avg_items_per_order,
            avg_weight_kg=avg_weight_kg,
            delivery_distance_km=delivery_distance_km,
            delivery_points=delivery_points,
            delivery_requirement=delivery_requirement,
            need_cold_chain=need_cold_chain,
            cold_chain_type=cold_chain_type,
            need_processing=need_processing,
            processing_weight_kg=processing_weight_kg,
            expected_return_rate=expected_return_rate,
            inventory_amount=inventory_amount,
            warehouse_area_sqm=warehouse_area_sqm,
            storage_days=storage_days,
            remark=remark if remark else None
        )
