"""
成本环节配置模型

定义哪些成本环节参与计算，支持选择性计算和自定义环节
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class CostLinkType(str, Enum):
    """成本环节类型"""
    ORDER_PROCESSING = "order_processing"           # 1. 订单处理
    INVENTORY_HOLDING = "inventory_holding"         # 2. 库存持有
    PICKING = "picking"                             # 3. 拣选作业
    PACKAGING = "packaging"                         # 4. 包装
    PROCESSING = "processing"                       # 4. 加工
    LOADING = "loading"                             # 5. 集货装车
    TRANSPORTATION = "transportation"               # 6. 运输配送
    DELIVERY = "delivery"                           # 7. 末端交付
    REVERSE_LOGISTICS = "reverse_logistics"         # 8. 逆向处理
    OVERHEAD = "overhead"                           # 9. 管理及间接费用
    CUSTOM = "custom"                               # 自定义环节


class CostLinkInfo(BaseModel):
    """成本环节信息"""
    link_type: CostLinkType = Field(..., description="环节类型")
    name: str = Field(..., description="环节名称")
    name_en: str = Field(..., description="环节英文标识")
    description: str = Field(default="", description="环节描述")
    is_active: bool = Field(default=True, description="是否参与计算")
    is_custom: bool = Field(default=False, description="是否为自定义环节")
    
    # 数据可用性状态
    data_status: str = Field(default="unknown", description="数据状态: unknown/available/missing/not_applicable")
    data_source: Optional[str] = Field(default=None, description="数据来源说明")
    
    # 自定义环节特有属性
    custom_formula: Optional[str] = Field(default=None, description="自定义计算公式")
    custom_rate: Optional[float] = Field(default=None, description="自定义费率")
    custom_unit: Optional[str] = Field(default=None, description="计量单位")
    
    # 用户确认状态
    user_confirmed: bool = Field(default=False, description="用户是否已确认")
    user_notes: Optional[str] = Field(default=None, description="用户备注")


class CostLinkConfig(BaseModel):
    """
    成本环节配置
    
    管理所有成本环节的配置状态，支持选择性计算
    """
    
    # 9大基础环节
    order_processing: CostLinkInfo = Field(
        default_factory=lambda: CostLinkInfo(
            link_type=CostLinkType.ORDER_PROCESSING,
            name="订单处理",
            name_en="order_processing",
            description="订单接收、系统处理、单据打印等环节成本"
        )
    )
    
    inventory_holding: CostLinkInfo = Field(
        default_factory=lambda: CostLinkInfo(
            link_type=CostLinkType.INVENTORY_HOLDING,
            name="库存持有",
            name_en="inventory_holding",
            description="库存资金占用、仓储租金、库存风险成本"
        )
    )
    
    picking: CostLinkInfo = Field(
        default_factory=lambda: CostLinkInfo(
            link_type=CostLinkType.PICKING,
            name="拣选作业",
            name_en="picking",
            description="商品拣选、复核、集货等作业成本"
        )
    )
    
    packaging: CostLinkInfo = Field(
        default_factory=lambda: CostLinkInfo(
            link_type=CostLinkType.PACKAGING,
            name="包装",
            name_en="packaging",
            description="包装材料、包装作业成本"
        )
    )
    
    processing: CostLinkInfo = Field(
        default_factory=lambda: CostLinkInfo(
            link_type=CostLinkType.PROCESSING,
            name="加工",
            name_en="processing",
            description="商品加工、分拣、组装等成本（仅餐配）"
        )
    )
    
    loading: CostLinkInfo = Field(
        default_factory=lambda: CostLinkInfo(
            link_type=CostLinkType.LOADING,
            name="集货装车",
            name_en="loading",
            description="货物集货、装车作业成本"
        )
    )
    
    transportation: CostLinkInfo = Field(
        default_factory=lambda: CostLinkInfo(
            link_type=CostLinkType.TRANSPORTATION,
            name="运输配送",
            name_en="transportation",
            description="干线运输、配送运输成本"
        )
    )
    
    delivery: CostLinkInfo = Field(
        default_factory=lambda: CostLinkInfo(
            link_type=CostLinkType.DELIVERY,
            name="末端交付",
            name_en="delivery",
            description="卸货、上楼、等待等末端交付成本"
        )
    )
    
    reverse_logistics: CostLinkInfo = Field(
        default_factory=lambda: CostLinkInfo(
            link_type=CostLinkType.REVERSE_LOGISTICS,
            name="逆向处理",
            name_en="reverse_logistics",
            description="退货处理、检验、报废等成本"
        )
    )
    
    overhead: CostLinkInfo = Field(
        default_factory=lambda: CostLinkInfo(
            link_type=CostLinkType.OVERHEAD,
            name="管理及间接费用",
            name_en="overhead",
            description="管理人员薪酬、IT系统、水电等间接费用"
        )
    )
    
    # 自定义环节列表
    custom_links: List[CostLinkInfo] = Field(default_factory=list, description="自定义环节列表")
    
    # 配置元数据
    config_version: str = Field(default="1.0", description="配置版本")
    created_at: Optional[str] = Field(default=None, description="创建时间")
    updated_at: Optional[str] = Field(default=None, description="更新时间")
    
    def get_all_links(self) -> List[CostLinkInfo]:
        """获取所有环节（基础+自定义）"""
        base_links = [
            self.order_processing,
            self.inventory_holding,
            self.picking,
            self.packaging,
            self.processing,
            self.loading,
            self.transportation,
            self.delivery,
            self.reverse_logistics,
            self.overhead,
        ]
        return base_links + self.custom_links
    
    def get_active_links(self) -> List[CostLinkInfo]:
        """获取启用的环节"""
        return [link for link in self.get_all_links() if link.is_active]
    
    def get_links_needing_confirmation(self) -> List[CostLinkInfo]:
        """获取需要用户确认的环节（数据状态为unknown）"""
        return [
            link for link in self.get_all_links() 
            if link.data_status == "unknown" and link.is_active
        ]
    
    def get_links_with_data(self) -> List[CostLinkInfo]:
        """获取有数据的环节"""
        return [
            link for link in self.get_all_links() 
            if link.data_status == "available"
        ]
    
    def get_links_without_data(self) -> List[CostLinkInfo]:
        """获取无数据的环节"""
        return [
            link for link in self.get_all_links() 
            if link.data_status in ["missing", "unknown"]
        ]
    
    def get_link_by_name(self, name: str) -> Optional[CostLinkInfo]:
        """通过名称获取环节"""
        for link in self.get_all_links():
            if link.name == name or link.name_en == name:
                return link
        return None
    
    def set_link_status(self, link_name: str, is_active: bool, data_status: Optional[str] = None):
        """设置环节状态"""
        link = self.get_link_by_name(link_name)
        if link:
            link.is_active = is_active
            if data_status:
                link.data_status = data_status
            return True
        return False
    
    def confirm_link(self, link_name: str, confirmed: bool = True, notes: Optional[str] = None):
        """用户确认环节"""
        link = self.get_link_by_name(link_name)
        if link:
            link.user_confirmed = confirmed
            if notes:
                link.user_notes = notes
            return True
        return False
    
    def add_custom_link(self, name: str, description: str, 
                        formula: Optional[str] = None,
                        rate: Optional[float] = None,
                        unit: Optional[str] = None) -> CostLinkInfo:
        """添加自定义环节"""
        custom_link = CostLinkInfo(
            link_type=CostLinkType.CUSTOM,
            name=name,
            name_en=f"custom_{len(self.custom_links)}",
            description=description,
            is_active=True,
            is_custom=True,
            custom_formula=formula,
            custom_rate=rate,
            custom_unit=unit,
            data_status="available" if rate else "unknown"
        )
        self.custom_links.append(custom_link)
        return custom_link
    
    def remove_custom_link(self, name: str) -> bool:
        """移除自定义环节"""
        for i, link in enumerate(self.custom_links):
            if link.name == name:
                self.custom_links.pop(i)
                return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "基础环节": {
                link.name: {
                    "是否启用": link.is_active,
                    "数据状态": link.data_status,
                    "用户确认": link.user_confirmed,
                    "描述": link.description
                }
                for link in self.get_all_links() if not link.is_custom
            },
            "自定义环节": [
                {
                    "名称": link.name,
                    "是否启用": link.is_active,
                    "数据状态": link.data_status,
                    "费率": link.custom_rate,
                    "单位": link.custom_unit
                }
                for link in self.custom_links
            ],
            "统计": {
                "总环节数": len(self.get_all_links()),
                "启用环节数": len(self.get_active_links()),
                "需确认环节数": len(self.get_links_needing_confirmation()),
                "有数据环节数": len(self.get_links_with_data()),
                "自定义环节数": len(self.custom_links)
            }
        }
    
    def get_confirmation_summary(self) -> str:
        """获取确认摘要（用于展示给用户）"""
        lines = ["\n【成本环节确认】"]
        lines.append("-" * 50)
        
        # 有数据的环节
        links_with_data = self.get_links_with_data()
        if links_with_data:
            lines.append("\n✅ 已识别到有数据的环节：")
            for link in links_with_data:
                lines.append(f"   • {link.name}: {link.description}")
        
        # 无数据的环节
        links_without_data = [
            link for link in self.get_active_links() 
            if link.data_status in ["missing", "unknown"]
        ]
        if links_without_data:
            lines.append("\n❓ 数据状态不明的环节：")
            for link in links_without_data:
                lines.append(f"   • {link.name}: {link.description}")
        
        # 未启用的环节
        inactive_links = [
            link for link in self.get_all_links() 
            if not link.is_active and not link.is_custom
        ]
        if inactive_links:
            lines.append("\n❌ 未启用的环节：")
            for link in inactive_links:
                lines.append(f"   • {link.name}")
        
        # 自定义环节
        if self.custom_links:
            lines.append("\n➕ 自定义环节：")
            for link in self.custom_links:
                status = "✅" if link.is_active else "❌"
                lines.append(f"   {status} {link.name}: {link.description}")
        
        lines.append("-" * 50)
        return "\n".join(lines)
    
    @classmethod
    def create_for_business_type(cls, business_type: str) -> "CostLinkConfig":
        """
        根据业务类型创建默认配置
        
        Args:
            business_type: 业务类型 (tob_enterprise/meal_delivery)
        
        Returns:
            成本环节配置
        """
        config = cls()
        
        if business_type == "meal_delivery":
            # 餐配业务默认启用所有环节
            pass  # 所有环节默认启用
        else:
            # TOB企业购：某些环节可能不适用
            # 例如：加工环节通常不适用
            config.processing.is_active = False
            config.processing.data_status = "not_applicable"
            config.processing.description = "TOB企业购通常不需要加工环节"
        
        return config


class CostLinkConfirmation(BaseModel):
    """
    环节确认结果
    
    记录用户对环节的确认选择
    """
    
    # 确认启用（原本未启用或数据状态不明）
    confirmed_active: List[str] = Field(default_factory=list, description="确认启用的环节")
    
    # 确认禁用（原本启用但用户确认不需要）
    confirmed_inactive: List[str] = Field(default_factory=list, description="确认禁用的环节")
    
    # 需要补充数据的环节
    need_data_input: List[str] = Field(default_factory=list, description="需要补充数据的环节")
    
    # 新增的自定义环节
    added_custom_links: List[Dict[str, Any]] = Field(default_factory=list, description="新增的自定义环节")
    
    # 用户备注
    user_notes: Optional[str] = Field(default=None, description="用户备注")
    
    # 确认时间
    confirmed_at: Optional[str] = Field(default=None, description="确认时间")
    
    def is_fully_confirmed(self, config: CostLinkConfig) -> bool:
        """检查是否所有环节都已确认"""
        for link in config.get_active_links():
            if link.data_status == "unknown" and link.name not in self.confirmed_active + self.confirmed_inactive:
                return False
        return True
