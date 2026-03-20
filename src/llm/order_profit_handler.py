"""
订单利润评估处理器

处理订单可行性评估的交互逻辑，包括：
- 识别用户意图（是否要进行订单可行性评估）
- 收集采购成本和销售价格信息
- 触发综合评估
"""

import re
from typing import Dict, Any, Optional, List
from ..models.order_profit_assessment import (
    OrderProfitAssessment, 
    OrderProfitAssessmentInput,
    ProductCostInfo,
    SalesRevenueInfo
)


class OrderProfitIntentDetector:
    """订单利润评估意图检测器"""
    
    # 触发关键词
    PROFIT_KEYWORDS = [
        "能不能做", "能做吗", "值得做", "划算", "利润", "毛利", "盈亏",
        "报价", "售价", "卖价", "采购价", "进货价", "成本价",
        "赚多少", "收益", "回报", "性价比", "可行性"
    ]
    
    # 价格相关关键词
    PRICE_KEYWORDS = {
        "purchase": ["采购", "进货", "买入", "成本价", "进价", "批发价", "拿货价"],
        "selling": ["售价", "卖价", "报价", "销售价", "零售价", "出价"],
    }
    
    @classmethod
    def detect_profit_intent(cls, user_input: str) -> Dict[str, Any]:
        """
        检测用户是否有订单利润评估意图
        
        Args:
            user_input: 用户输入
        
        Returns:
            检测结果
        """
        user_input_lower = user_input.lower()
        
        # 检查是否包含利润相关关键词
        has_profit_keyword = any(kw in user_input_lower for kw in cls.PROFIT_KEYWORDS)
        
        # 检查是否包含价格信息
        has_purchase_price = any(kw in user_input_lower for kw in cls.PRICE_KEYWORDS["purchase"])
        has_selling_price = any(kw in user_input_lower for kw in cls.PRICE_KEYWORDS["selling"])
        
        # 尝试提取价格数字
        prices = cls._extract_prices(user_input)
        
        return {
            "has_profit_intent": has_profit_keyword or has_purchase_price or has_selling_price,
            "has_purchase_price": has_purchase_price,
            "has_selling_price": has_selling_price,
            "extracted_prices": prices,
            "confidence": "high" if (has_profit_keyword and (has_purchase_price or has_selling_price)) else "medium"
        }
    
    @classmethod
    def _extract_prices(cls, text: str) -> List[float]:
        """从文本中提取价格数字"""
        # 匹配价格模式：数字+元/块/元/￥/$等
        patterns = [
            r'(\d+\.?\d*)\s*[元块￥$]',  # 数字+货币单位
            r'[单价价格售价采购价进货价]*[:：]\s*(\d+\.?\d*)',  # 标签+数字
        ]
        
        prices = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    price = float(match)
                    if price > 0 and price < 100000:  # 合理范围
                        prices.append(price)
                except:
                    pass
        
        return prices


class OrderProfitInputCollector:
    """订单利润评估输入收集器"""
    
    def __init__(self):
        """初始化收集器"""
        self.input_data = OrderProfitAssessmentInput()
        self.collected_fields = set()
        self.missing_fields = ["purchase_price", "selling_price"]
    
    def extract_from_text(self, user_input: str) -> Dict[str, Any]:
        """
        从用户输入中提取信息
        
        Args:
            user_input: 用户输入
        
        Returns:
            提取结果
        """
        user_input_lower = user_input.lower()
        extracted = {}
        
        # 提取商品名称
        if not self.input_data.product_name:
            # 尝试提取"XX的采购价"或"XX售价"中的XX
            name_patterns = [
                r'([\u4e00-\u9fa5]+)[的之]?\s*(?:采购|进货|买入|售价|卖价|报价)',
                r'评估([\u4e00-\u9fa5]+)',
            ]
            for pattern in name_patterns:
                match = re.search(pattern, user_input)
                if match:
                    self.input_data.product_name = match.group(1)
                    extracted["product_name"] = self.input_data.product_name
                    break
        
        # 提取采购价
        if self.input_data.purchase_price is None:
            purchase_patterns = [
                r'(?:采购|进货|买入|成本|进|批发|拿货)[价价格]*[:：]?\s*(\d+\.?\d*)',
                r'(\d+\.?\d*)\s*[元块￥$]?\s*(?:采购|进货|买入)',
            ]
            for pattern in purchase_patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    try:
                        self.input_data.purchase_price = float(match.group(1))
                        extracted["purchase_price"] = self.input_data.purchase_price
                        if "purchase_price" in self.missing_fields:
                            self.missing_fields.remove("purchase_price")
                        break
                    except:
                        pass
        
        # 提取销售价
        if self.input_data.selling_price is None:
            selling_patterns = [
                r'(?:销售|卖|零售|报|出)[价价格]*[:：]?\s*(\d+\.?\d*)',
                r'(?:售价|卖价|报价)[是]?[:：]?\s*(\d+\.?\d*)',
                r'(\d+\.?\d*)\s*[元块￥$]?\s*(?:销售|卖|零售|报)',
                r'卖(\d+\.?\d*)[元块￥$]?',
            ]
            for pattern in selling_patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    try:
                        self.input_data.selling_price = float(match.group(1))
                        extracted["selling_price"] = self.input_data.selling_price
                        if "selling_price" in self.missing_fields:
                            self.missing_fields.remove("selling_price")
                        break
                    except:
                        pass
        
        # 提取数量 - 只提取明确标注为每单数量的数字
        # 避免匹配价格数字（通常较大）
        if self.input_data.quantity_per_order == 1:
            quantity_patterns = [
                r'每单[:：]?\s*(\d+)\s*[件个套]*',
                r'每订单[:：]?\s*(\d+)\s*[件个套]*',
                r'数量[:：]?\s*(\d+)\s*[件个套]*',
            ]
            for pattern in quantity_patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    try:
                        qty = int(match.group(1))
                        if 1 <= qty <= 1000:
                            self.input_data.quantity_per_order = qty
                            extracted["quantity_per_order"] = qty
                            break
                    except:
                        pass
        
        return {
            "extracted": extracted,
            "missing_fields": self.missing_fields,
            "is_complete": len(self.missing_fields) == 0
        }
    
    def get_next_question(self) -> str:
        """获取下一个需要询问的问题"""
        if "purchase_price" in self.missing_fields:
            return "请提供商品的采购单价（元）："
        elif "selling_price" in self.missing_fields:
            return "请提供商品的销售单价（元）："
        else:
            return "信息已收集完整，是否需要进行订单可行性评估？"
    
    def create_assessment(self, logistics_cost: float) -> OrderProfitAssessment:
        """
        创建订单利润评估
        
        Args:
            logistics_cost: 物流成本/单
        
        Returns:
            订单利润评估对象
        """
        return self.input_data.create_assessment(logistics_cost)


class OrderProfitHandler:
    """
    订单利润评估处理器
    
    管理订单利润评估的完整流程
    """
    
    # 处理状态
    STATE_IDLE = "idle"
    STATE_COLLECTING = "collecting"
    STATE_READY = "ready"
    STATE_COMPLETED = "completed"
    
    def __init__(self, llm_client=None):
        """
        初始化处理器
        
        Args:
            llm_client: LLM客户端
        """
        self.llm_client = llm_client
        self.state = self.STATE_IDLE
        self.collector = None
        self.current_assessment = None
        self.logistics_cost = 0
    
    def start_assessment(self, logistics_cost: float, user_input: str = "") -> Dict[str, Any]:
        """
        开始订单利润评估
        
        Args:
            logistics_cost: 已计算的物流成本/单
            user_input: 用户输入（可能包含价格信息）
        
        Returns:
            响应结果
        """
        self.logistics_cost = logistics_cost
        self.collector = OrderProfitInputCollector()
        self.state = self.STATE_COLLECTING
        
        # 尝试从输入中提取信息
        if user_input:
            result = self.collector.extract_from_text(user_input)
            if result["is_complete"]:
                self.state = self.STATE_READY
                return self._perform_assessment()
            else:
                return {
                    "status": "collecting",
                    "message": self._generate_collection_message(result),
                    "missing_fields": result["missing_fields"],
                    "extracted": result["extracted"]
                }
        
        # 没有输入，开始询问
        return {
            "status": "collecting",
            "message": f"已计算出物流成本为 ¥{logistics_cost:.2f}/单。\n\n为了评估订单可行性，我还需要了解以下信息：\n\n1. 商品的采购单价是多少？\n2. 商品的销售单价是多少？\n\n您可以直接回复，例如：\"采购价50元，售价80元\"",
            "missing_fields": ["purchase_price", "selling_price"]
        }
    
    def process_input(self, user_input: str) -> Dict[str, Any]:
        """
        处理用户输入
        
        Args:
            user_input: 用户输入
        
        Returns:
            处理结果
        """
        if self.state == self.STATE_COLLECTING:
            result = self.collector.extract_from_text(user_input)
            
            if result["is_complete"]:
                self.state = self.STATE_READY
                return self._perform_assessment()
            else:
                return {
                    "status": "collecting",
                    "message": self.collector.get_next_question(),
                    "missing_fields": result["missing_fields"],
                    "extracted": result["extracted"]
                }
        
        elif self.state == self.STATE_COMPLETED:
            # 已经评估完成，检查是否有新的意图
            intent = OrderProfitIntentDetector.detect_profit_intent(user_input)
            if intent["has_profit_intent"]:
                # 重新开始评估
                self.reset()
                return self.start_assessment(self.logistics_cost, user_input)
            else:
                return {
                    "status": "completed",
                    "message": "订单可行性评估已完成。如需重新评估，请提供新的价格信息。",
                    "assessment": self.current_assessment.to_dict() if self.current_assessment else None
                }
        
        return {
            "status": "error",
            "message": "未知状态"
        }
    
    def _perform_assessment(self) -> Dict[str, Any]:
        """执行评估"""
        self.current_assessment = self.collector.create_assessment(self.logistics_cost)
        self.state = self.STATE_COMPLETED
        
        return {
            "status": "completed",
            "message": self.current_assessment.to_report(),
            "assessment": self.current_assessment.to_dict(),
            "feasibility": self.current_assessment.feasibility.value,
            "profit_margin": self.current_assessment.gross_profit_margin
        }
    
    def _generate_collection_message(self, result: Dict[str, Any]) -> str:
        """生成收集信息的消息"""
        lines = ["已提取到以下信息："]
        
        extracted = result.get("extracted", {})
        if "product_name" in extracted:
            lines.append(f"  • 商品名称: {extracted['product_name']}")
        if "purchase_price" in extracted:
            lines.append(f"  • 采购单价: ¥{extracted['purchase_price']:.2f}")
        if "selling_price" in extracted:
            lines.append(f"  • 销售单价: ¥{extracted['selling_price']:.2f}")
        if "quantity_per_order" in extracted:
            lines.append(f"  • 每单数量: {extracted['quantity_per_order']}件")
        
        lines.append(f"\n物流成本: ¥{self.logistics_cost:.2f}/单")
        
        if result["missing_fields"]:
            lines.append(f"\n还需要以下信息：")
            for field in result["missing_fields"]:
                if field == "purchase_price":
                    lines.append("  • 采购单价")
                elif field == "selling_price":
                    lines.append("  • 销售单价")
        
        return "\n".join(lines)
    
    def reset(self):
        """重置状态"""
        self.state = self.STATE_IDLE
        self.collector = None
        self.current_assessment = None
    
    def is_active(self) -> bool:
        """检查是否处于活跃状态"""
        return self.state != self.STATE_IDLE
    
    def get_state(self) -> str:
        """获取当前状态"""
        return self.state


def should_trigger_profit_assessment(user_input: str, has_logistics_result: bool = False) -> bool:
    """
    判断是否应触发订单利润评估
    
    Args:
        user_input: 用户输入
        has_logistics_result: 是否已有物流成本计算结果
    
    Returns:
        是否应该触发
    """
    # 如果没有物流成本结果，不能触发利润评估
    if not has_logistics_result:
        return False
    
    # 检测意图
    intent = OrderProfitIntentDetector.detect_profit_intent(user_input)
    return intent["has_profit_intent"]


if __name__ == "__main__":
    # 测试
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    print("="*60)
    print("订单利润评估处理器测试")
    print("="*60)
    
    # 测试意图检测
    test_inputs = [
        "这单能不能做？",
        "采购价50元，卖80元",
        "利润怎么样？",
        "这个报价划算吗？",
        "普通业务咨询"
    ]
    
    print("\n【意图检测测试】")
    for text in test_inputs:
        intent = OrderProfitIntentDetector.detect_profit_intent(text)
        print(f"输入: {text}")
        print(f"  意图: {'是' if intent['has_profit_intent'] else '否'} (置信度: {intent['confidence']})")
        print(f"  提取价格: {intent['extracted_prices']}")
        print()
    
    # 测试输入收集
    print("\n【输入收集测试】")
    collector = OrderProfitInputCollector()
    
    test_text = "办公用品采购价50元，售价80元，每单5件"
    result = collector.extract_from_text(test_text)
    print(f"输入: {test_text}")
    print(f"提取结果: {result}")
    
    # 测试完整流程
    print("\n【完整流程测试】")
    handler = OrderProfitHandler()
    
    # 开始评估
    response = handler.start_assessment(logistics_cost=33.79)
    print(f"系统: {response['message']}")
    
    # 用户回复
    user_reply = "采购价50元，售价80元"
    response = handler.process_input(user_reply)
    print(f"\n用户: {user_reply}")
    print(f"系统: {response['message'][:200]}...")
