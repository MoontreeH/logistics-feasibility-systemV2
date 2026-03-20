"""
数据模型模块

定义业务场景、成本参数和成本结果的数据结构
"""

from .business_scenario import BusinessScenario, BusinessType, DeliveryRequirement
from .cost_parameters import CostParameters, InventoryConfig, TransportationConfig
from .cost_result import CostResult, CostBreakdown, FeasibilityRating
from .cost_link_config import (
    CostLinkConfig,
    CostLinkInfo,
    CostLinkType,
    CostLinkConfirmation
)
from .order_profit_assessment import (
    OrderProfitAssessment,
    OrderProfitAssessmentInput,
    ProductCostInfo,
    SalesRevenueInfo,
    ProfitLevel,
    OrderFeasibility
)

__all__ = [
    "BusinessScenario",
    "BusinessType",
    "DeliveryRequirement",
    "CostParameters",
    "InventoryConfig",
    "TransportationConfig",
    "CostResult",
    "CostBreakdown",
    "FeasibilityRating",
    "CostLinkConfig",
    "CostLinkInfo",
    "CostLinkType",
    "CostLinkConfirmation",
    "OrderProfitAssessment",
    "OrderProfitAssessmentInput",
    "ProductCostInfo",
    "SalesRevenueInfo",
    "ProfitLevel",
    "OrderFeasibility",
]
