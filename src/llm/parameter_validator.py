"""
参数校验模块

校验和补全业务参数
"""

from typing import Dict, Any, List, Tuple, Optional
from ..models import BusinessScenario, BusinessType, DeliveryRequirement


class ParameterValidator:
    """
    参数校验器
    
    验证提取的参数是否合法，并提供默认值
    """
    
    # 参数校验规则
    VALIDATION_RULES = {
        "daily_order_count": {"min": 1, "max": 100000, "type": int},
        "avg_items_per_order": {"min": 1, "max": 10000, "type": int},
        "avg_weight_kg": {"min": 0.1, "max": 10000, "type": float},
        "delivery_distance_km": {"min": 0.1, "max": 1000, "type": float},
        "floor": {"min": 1, "max": 100, "type": int},
        "expected_return_rate": {"min": 0, "max": 1, "type": float},
    }
    
    # 参数中文名称映射
    PARAM_NAMES = {
        "scenario_name": "场景名称/客户名称",
        "daily_order_count": "日订单数",
        "avg_items_per_order": "平均每单件数",
        "avg_weight_kg": "平均每单重量(kg)",
        "delivery_distance_km": "配送距离(km)",
        "need_upstairs": "是否需要上楼",
        "floor": "配送楼层",
        "has_elevator": "是否有电梯",
        "need_cold_chain": "是否需要冷链",
        "need_processing": "是否需要加工",
        "expected_return_rate": "预期退货率",
    }
    
    @classmethod
    def validate(cls, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        校验参数
        
        Args:
            params: 待校验的参数
        
        Returns:
            (是否通过, 错误信息列表)
        """
        errors = []
        
        for param, rules in cls.VALIDATION_RULES.items():
            value = params.get(param)
            
            if value is None:
                continue
            
            # 类型检查
            if not isinstance(value, rules["type"]):
                try:
                    value = rules["type"](value)
                    params[param] = value
                except (ValueError, TypeError):
                    errors.append(f"{cls.PARAM_NAMES.get(param, param)} 类型错误")
                    continue
            
            # 范围检查
            if value < rules["min"]:
                errors.append(f"{cls.PARAM_NAMES.get(param, param)} 不能小于 {rules['min']}")
            elif value > rules["max"]:
                errors.append(f"{cls.PARAM_NAMES.get(param, param)} 不能大于 {rules['max']}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def apply_defaults(cls, params: Dict[str, Any], business_type: str = None) -> Dict[str, Any]:
        """
        应用默认值
        
        Args:
            params: 原始参数
            business_type: 业务类型
        
        Returns:
            应用默认值后的参数
        """
        result = params.copy()
        
        # 通用默认值
        defaults = {
            "scenario_name": "未命名场景",
            "avg_order_lines": 5,
            "delivery_points": 1,
            "floor": 1,
            "has_elevator": True,
            "inventory_amount": 10000,
            "warehouse_area_sqm": 10,
            "storage_days": 7,
            "avg_item_cost": 50,
        }
        
        # 业务类型特定默认值
        if business_type == "meal_delivery":
            defaults.update({
                "need_cold_chain": True,
                "expected_return_rate": 0.05,
            })
        else:
            defaults.update({
                "need_cold_chain": False,
                "expected_return_rate": 0.01,
            })
        
        # 应用默认值
        for key, value in defaults.items():
            if result.get(key) is None:
                result[key] = value
        
        return result
    
    @classmethod
    def create_scenario(cls, params: Dict[str, Any], business_type: str) -> BusinessScenario:
        """
        从参数创建业务场景
        
        Args:
            params: 参数字典
            business_type: 业务类型
        
        Returns:
            BusinessScenario对象
        """
        # 应用默认值
        params = cls.apply_defaults(params, business_type)
        
        # 创建交付要求
        need_upstairs = params.get("need_upstairs", False)
        if need_upstairs is None:
            need_upstairs = False
            
        has_elevator = params.get("has_elevator", True)
        if has_elevator is None:
            has_elevator = True
            
        delivery_req = DeliveryRequirement(
            need_upstairs=need_upstairs,
            floor=params.get("floor", 1),
            has_elevator=has_elevator,
            waiting_time_hours=params.get("waiting_time_hours", 0)
        )
        
        # 确定业务类型枚举
        if business_type == "meal_delivery":
            bt = BusinessType.MEAL_DELIVERY
        else:
            bt = BusinessType.TOB_ENTERPRISE
        
        # 创建场景
        scenario = BusinessScenario(
            business_type=bt,
            scenario_name=params.get("scenario_name", "未命名场景"),
            daily_order_count=params.get("daily_order_count", 10),
            avg_order_lines=params.get("avg_order_lines", 5),
            avg_items_per_order=params.get("avg_items_per_order", 5),
            avg_weight_kg=params.get("avg_weight_kg", 5.0),
            delivery_distance_km=params.get("delivery_distance_km", 10.0),
            delivery_points=params.get("delivery_points", 1),
            delivery_requirement=delivery_req,
            need_cold_chain=params.get("need_cold_chain", False),
            need_processing=params.get("need_processing", False),
            processing_weight_kg=params.get("processing_weight_kg", 0),
            expected_return_rate=params.get("expected_return_rate", 0.01),
            inventory_amount=params.get("inventory_amount", 10000),
            warehouse_area_sqm=params.get("warehouse_area_sqm", 10),
            storage_days=params.get("storage_days", 7),
            remark=params.get("remark")
        )
        
        return scenario
    
    @classmethod
    def get_param_description(cls, param_name: str) -> str:
        """
        获取参数描述
        
        Args:
            param_name: 参数名
        
        Returns:
            参数描述
        """
        return cls.PARAM_NAMES.get(param_name, param_name)
    
    @classmethod
    def get_missing_required_params(cls, params: Dict[str, Any]) -> List[str]:
        """
        获取缺失的必需参数
        
        Args:
            params: 当前参数
        
        Returns:
            缺失参数列表
        """
        required = ["daily_order_count", "avg_items_per_order", "avg_weight_kg", "delivery_distance_km"]
        missing = []
        
        for param in required:
            if params.get(param) is None:
                missing.append(param)
        
        return missing


if __name__ == "__main__":
    # 测试参数校验
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    # 测试数据
    test_params = {
        "scenario_name": "测试客户",
        "daily_order_count": 100,
        "avg_items_per_order": 5,
        "avg_weight_kg": 10.5,
        "delivery_distance_km": 20,
        "need_upstairs": True,
        "floor": 3,
    }
    
    print("参数校验测试：")
    print(f"输入参数: {test_params}")
    
    # 校验
    is_valid, errors = ParameterValidator.validate(test_params)
    print(f"校验结果: {'通过' if is_valid else '失败'}")
    if errors:
        print(f"错误: {errors}")
    
    # 应用默认值
    params_with_defaults = ParameterValidator.apply_defaults(test_params, "tob_enterprise")
    print(f"\n应用默认值后:")
    for key, value in params_with_defaults.items():
        print(f"  {key}: {value}")
    
    # 创建场景
    scenario = ParameterValidator.create_scenario(params_with_defaults, "tob_enterprise")
    print(f"\n创建的场景: {scenario}")
    print(f"月度业务量: {scenario.get_monthly_volume()}")
