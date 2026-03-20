"""
单均成本计算模型

以"单"为基本计算单元，支持：
- 临时性/一次性订单评估
- 不依赖"日订单数"等循环假设
- 更灵活的成本计算
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class OrderType(str, Enum):
    """订单类型"""
    SINGLE = "single"           # 一次性/临时订单
    DAILY = "daily"           # 每日循环订单
    WEEKLY = "weekly"         # 每周循环订单
    MONTHLY = "monthly"      # 每月循环订单
    UNCERTAIN = "uncertain"  # 不确定


class PerOrderParameters(BaseModel):
    """
    单均成本计算参数
    
    以单个订单为基本计算单元
    """
    
    # 订单基本信息
    order_id: Optional[str] = Field(default=None, description="订单标识")
    order_type: OrderType = Field(default=OrderType.SINGLE, description="订单类型")
    
    # 单均货物信息
    items_per_order: int = Field(default=1, ge=1, description="每单件数")
    weight_per_item_kg: float = Field(default=1.0, gt=0, description="单件重量(kg)")
    total_weight_kg: float = Field(default=1.0, gt=0, description="单均总重量(kg)")
    
    # 配送信息
    distance_km: float = Field(default=10.0, gt=0, description="配送距离(km)")
    need_upstairs: bool = Field(default=False, description="是否需要上楼")
    floor: int = Field(default=1, ge=1, description="楼层")
    has_elevator: bool = Field(default=True, description="是否有电梯")
    
    # 特殊需求
    need_cold_chain: bool = Field(default=False, description="是否需要冷链")
    need_special_handling: bool = Field(default=False, description="是否需要特殊处理")
    
    # 业务类型
    business_type: str = Field(default="tob_enterprise", description="业务类型")
    
    # 价格信息（用于利润计算）
    purchase_price: Optional[float] = Field(default=None, ge=0, description="采购单价")
    selling_price: Optional[float] = Field(default=None, ge=0, description="销售单价")
    
    # 扩展数据（由LLM提取）
    custom_data: Dict[str, Any] = Field(default_factory=dict, description="自定义数据")
    
    @classmethod
    def from_text(cls, text: str = "") -> "PerOrderParameters":
        """
        从文本创建单均参数（由LLM提取）
        
        Args:
            text: 用户描述文本
        
        Returns:
            单均参数实例
        """
        import re
        
        params = cls()
        
        # 提取件数
        items_patterns = [
            r'每单\s*(\d+)\s*[件个箱]',
            r'(\d+)\s*[件个箱]\s*/\s*单',
            r'每单(\d+)件',
        ]
        for pattern in items_patterns:
            match = re.search(pattern, text)
            if match:
                params.items_per_order = int(match.group(1))
                break
        
        # 提取重量
        weight_patterns = [
            r'(\d+\.?\d*)\s*公斤',
            r'(\d+\.?\d*)\s*kg',
            r'每[件箱]重\s*(\d+\.?\d*)',
        ]
        for pattern in weight_patterns:
            match = re.search(pattern, text.lower())
            if match:
                params.weight_per_item_kg = float(match.group(1))
                break
        
        # 提取距离
        distance_patterns = [
            r'(\d+\.?\d*)\s*公里',
            r'(\d+\.?\d*)\s*km',
            r'距离\s*(\d+\.?\d*)',
        ]
        for pattern in distance_patterns:
            match = re.search(pattern, text.lower())
            if match:
                params.distance_km = float(match.group(1))
                break
        
        # 提取楼层
        floor_patterns = [
            r'上?(\d+)\s*楼',
            r'(\d+)\s*层',
        ]
        for pattern in floor_patterns:
            match = re.search(pattern, text)
            if match:
                params.floor = int(match.group(1))
                params.need_upstairs = True
                break
        
        # 提取价格
        price_patterns = [
            r'采购[单价价]\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*元\s*[采进]价',
        ]
        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                params.purchase_price = float(match.group(1))
                break
        
        selling_patterns = [
            r'售价\s*(\d+\.?\d*)',
            r'卖\s*(\d+\.?\d*)',
            r'销售[单价价]\s*(\d+\.?\d*)',
        ]
        for pattern in selling_patterns:
            match = re.search(pattern, text)
            if match:
                params.selling_price = float(match.group(1))
                break
        
        # 判断上楼需求
        if any(kw in text for kw in ['上楼', '爬楼', '无电梯']):
            params.need_upstairs = True
            params.has_elevator = False
        
        # 判断冷链需求
        if any(kw in text.lower() for kw in ['冷链', '冷藏', '冷冻', '保鲜']):
            params.need_cold_chain = True
        
        # 判断业务类型
        if any(kw in text for kw in ['餐', '食材', '食品', '生鲜']):
            params.business_type = "meal_delivery"
        else:
            params.business_type = "tob_enterprise"
        
        # 判断订单类型
        if any(kw in text for kw in ['每天', '日均', '每日']):
            params.order_type = OrderType.DAILY
        elif any(kw in text for kw in ['每周', '周均']):
            params.order_type = OrderType.WEEKLY
        elif any(kw in text for kw in ['每月', '月均']):
            params.order_type = OrderType.MONTHLY
        elif any(kw in text for kw in ['一次', '临时', '这单', '这批']):
            params.order_type = OrderType.SINGLE
        else:
            params.order_type = OrderType.UNCERTAIN
        
        # 计算总重量
        params.total_weight_kg = params.items_per_order * params.weight_per_item_kg
        
        return params
    
    def to_calculation_dict(self) -> Dict[str, Any]:
        """转换为计算所需的字典"""
        return {
            "items_per_order": self.items_per_order,
            "weight_per_item_kg": self.weight_per_item_kg,
            "total_weight_kg": self.total_weight_kg,
            "distance_km": self.distance_km,
            "need_upstairs": self.need_upstairs,
            "floor": self.floor,
            "has_elevator": self.has_elevator,
            "need_cold_chain": self.need_cold_chain,
            "need_special_handling": self.need_special_handling,
            "business_type": self.business_type,
        }
    
    def get_summary(self) -> str:
        """获取摘要描述"""
        lines = [
            f"**订单类型**: {self.order_type.value}",
            f"**每单件数**: {self.items_per_order}件",
            f"**单件重量**: {self.weight_per_item_kg}kg",
            f"**总重量**: {self.total_weight_kg}kg",
            f"**配送距离**: {self.distance_km}km",
        ]
        
        if self.need_upstairs:
            lines.append(f"**上楼需求**: 需要上{self.floor}楼 (电梯: {'有' if self.has_elevator else '无'})")
        
        if self.need_cold_chain:
            lines.append("**冷链需求**: 需要")
        
        if self.purchase_price and self.selling_price:
            lines.extend([
                f"**采购价**: ¥{self.purchase_price}",
                f"**售价**: ¥{self.selling_price}",
            ])
        
        return "\n".join(lines)
