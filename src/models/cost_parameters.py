"""
成本参数模型

定义成本计算所需的参数配置
"""

from typing import Optional
from pydantic import BaseModel, Field
from .cost_link_config import CostLinkConfig


class InventoryConfig(BaseModel):
    """库存配置参数"""
    avg_inventory_amount: float = Field(default=10000, ge=0, description="平均库存金额（元）")
    warehouse_area_sqm: float = Field(default=10, gt=0, description="占用仓库面积（平米）")
    storage_days: float = Field(default=7, gt=0, description="平均存储天数")
    capital_cost_rate: float = Field(default=0.05, ge=0, description="资金成本率（年化）")


class TransportationConfig(BaseModel):
    """运输配置参数"""
    use_own_vehicle: bool = Field(default=True, description="是否使用自有车辆")
    vehicle_type: str = Field(default="normal", description="车辆类型：normal/cold")
    round_trip: bool = Field(default=False, description="是否往返")
    

class CostParameters(BaseModel):
    """
    成本计算参数
    
    包含所有成本计算所需的参数，可以从业务场景自动转换，也可以手动设置
    """
    
    # 成本环节配置（新增）
    link_config: Optional[CostLinkConfig] = Field(default=None, description="成本环节配置")
    
    # 业务量参数
    monthly_order_count: int = Field(..., ge=1, description="月订单数")
    monthly_order_lines: int = Field(..., ge=1, description="月订单行数")
    monthly_items: int = Field(..., ge=1, description="月拣货件数")
    
    # 库存参数
    inventory_config: InventoryConfig = Field(default_factory=InventoryConfig)
    
    # 包装参数
    monthly_packages: int = Field(..., ge=1, description="月包装个数")
    need_cold_packaging: bool = Field(default=False, description="是否需要冷链包装")
    
    # 加工参数（餐配）
    monthly_processing_weight: float = Field(default=0, ge=0, description="月加工重量（公斤）")
    
    # 运输参数
    monthly_distance_km: float = Field(..., gt=0, description="月行驶里程（公里）")
    monthly_delivery_points: int = Field(..., ge=1, description="月配送点数")
    transportation_config: TransportationConfig = Field(default_factory=TransportationConfig)
    
    # 装车参数
    monthly_loading_hours: float = Field(default=10, gt=0, description="月装车工时")
    
    # 末端交付参数
    need_upstairs: bool = Field(default=False, description="是否需要上楼")
    total_floors: int = Field(default=0, ge=0, description="总楼层数（所有订单累计）")
    no_elevator_count: int = Field(default=0, ge=0, description="无电梯次数")
    waiting_hours: float = Field(default=0, ge=0, description="等待时间（小时）")
    
    # 退货参数
    monthly_return_items: int = Field(default=0, ge=0, description="月退货件数")
    return_rate: float = Field(default=0.01, ge=0, le=1, description="退货率")
    scrap_rate: float = Field(default=0.5, ge=0, le=1, description="报废率")
    
    # 商品成本（用于计算报废损失）
    avg_item_cost: float = Field(default=50, gt=0, description="平均商品成本（元/件）")
    
    @classmethod
    def from_scenario(cls, scenario) -> "CostParameters":
        """从业务场景创建成本参数"""
        monthly = scenario.get_monthly_volume()
        
        # 计算月行驶里程（假设每天配送，每趟距离*30）
        monthly_distance = scenario.delivery_distance_km * 30
        if scenario.delivery_requirement and scenario.delivery_requirement.need_upstairs:
            total_floors = scenario.delivery_requirement.floor * monthly["monthly_orders"]
        else:
            total_floors = 0
            
        # 计算退货数量
        monthly_return_items = int(monthly["monthly_items"] * scenario.expected_return_rate)
        
        return cls(
            monthly_order_count=monthly["monthly_orders"],
            monthly_order_lines=monthly["monthly_lines"],
            monthly_items=monthly["monthly_items"],
            inventory_config=InventoryConfig(
                avg_inventory_amount=scenario.inventory_amount,
                warehouse_area_sqm=scenario.warehouse_area_sqm,
                storage_days=scenario.storage_days,
            ),
            monthly_packages=monthly["monthly_orders"],  # 假设每单一个包裹
            need_cold_packaging=scenario.is_cold_chain(),
            monthly_processing_weight=scenario.processing_weight_kg * 30,
            monthly_distance_km=monthly_distance,
            monthly_delivery_points=scenario.delivery_points * 30,
            transportation_config=TransportationConfig(
                vehicle_type="cold" if scenario.is_cold_chain() else "normal"
            ),
            monthly_loading_hours=monthly["monthly_orders"] * 0.5,  # 假设每单0.5小时
            need_upstairs=scenario.delivery_requirement.need_upstairs if scenario.delivery_requirement else False,
            total_floors=total_floors,
            no_elevator_count=0,  # 需要根据实际情况设置
            waiting_hours=scenario.delivery_requirement.waiting_time_hours * 30 if scenario.delivery_requirement else 0,
            monthly_return_items=monthly_return_items,
            return_rate=scenario.expected_return_rate,
            scrap_rate=0.05 if scenario.business_type.value == "meal_delivery" else 0.01,
        )
