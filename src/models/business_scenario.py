"""
业务场景模型

定义TOB企业购和餐配业务的业务场景数据结构
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, validator


class BusinessType(str, Enum):
    """业务类型枚举"""
    TOB_ENTERPRISE = "tob_enterprise"
    MEAL_DELIVERY = "meal_delivery"


class DeliveryRequirement(BaseModel):
    """交付要求"""
    need_upstairs: bool = Field(default=False, description="是否需要上楼")
    floor: int = Field(default=1, ge=1, description="楼层")
    has_elevator: bool = Field(default=True, description="是否有电梯")
    delivery_time_window: Optional[str] = Field(default=None, description="配送时间窗口要求")
    waiting_time_hours: float = Field(default=0, ge=0, description="预计等待时间（小时）")


class BusinessScenario(BaseModel):
    """
    业务场景定义
    
    描述一个物流业务的基本信息，包括业务类型、订单特征、配送要求等
    """
    
    # 基本信息
    business_type: BusinessType = Field(..., description="业务类型")
    scenario_name: str = Field(..., description="场景名称/客户名称")
    
    # 订单特征
    daily_order_count: int = Field(..., ge=1, description="日订单数")
    avg_order_lines: int = Field(default=5, ge=1, description="平均每单行数")
    avg_items_per_order: int = Field(..., ge=1, description="平均每单件数")
    avg_weight_kg: float = Field(..., gt=0, description="平均每单重量（公斤）")
    
    # 配送特征
    delivery_distance_km: float = Field(..., gt=0, description="配送距离（公里）")
    delivery_points: int = Field(default=1, ge=1, description="配送点数")
    
    # 特殊要求
    delivery_requirement: DeliveryRequirement = Field(
        default_factory=DeliveryRequirement, 
        description="交付要求"
    )
    
    # 冷链要求（仅餐配业务）
    need_cold_chain: bool = Field(default=False, description="是否需要冷链")
    cold_chain_type: Optional[str] = Field(default=None, description="冷链类型：refrigerated/frozen")
    
    # 加工要求（仅餐配业务）
    need_processing: bool = Field(default=False, description="是否需要加工")
    processing_weight_kg: float = Field(default=0, ge=0, description="加工重量（公斤）")
    
    # 退货/损耗特征
    expected_return_rate: Optional[float] = Field(default=None, ge=0, le=1, description="预期退货率")
    
    # 库存特征
    inventory_amount: float = Field(default=10000, ge=0, description="平均库存金额（元）")
    warehouse_area_sqm: float = Field(default=10, gt=0, description="占用仓库面积（平米）")
    storage_days: float = Field(default=7, gt=0, description="平均存储天数")
    
    # 其他
    remark: Optional[str] = Field(default=None, description="备注")
    
    @validator('expected_return_rate', always=True)
    def set_default_return_rate(cls, v, values):
        """设置默认退货率"""
        if v is None:
            business_type = values.get('business_type')
            if business_type == BusinessType.MEAL_DELIVERY:
                return 0.05  # 餐配默认5%
            else:
                return 0.01  # TOB默认1%
        return v
    
    @validator('need_cold_chain', always=True)
    def validate_cold_chain(cls, v, values):
        """餐配业务默认需要冷链"""
        business_type = values.get('business_type')
        if business_type == BusinessType.MEAL_DELIVERY and not v:
            return True
        return v
    
    def get_monthly_volume(self) -> dict:
        """计算月度业务量"""
        return {
            "monthly_orders": self.daily_order_count * 30,
            "monthly_items": self.daily_order_count * 30 * self.avg_items_per_order,
            "monthly_lines": self.daily_order_count * 30 * self.avg_order_lines,
        }
    
    def is_cold_chain(self) -> bool:
        """判断是否需要冷链"""
        return self.need_cold_chain or self.business_type == BusinessType.MEAL_DELIVERY
    
    def __str__(self) -> str:
        return f"{self.scenario_name} ({self.business_type.value})"
