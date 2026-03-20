"""
智能参数收集器

实现智能的参数收集和确认逻辑：
- 区分参数缺失原因（提取失败/用户未提供）
- 主动询问用户补全参数
- 支持部分计算（计算可计算的部分）
- 计算前确认环节和数据
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ParameterStatus(str, Enum):
    """参数状态"""
    EXTRACTED = "extracted"           # 已从输入中提取
    USER_PROVIDED = "user_provided"   # 用户明确提供
    DEFAULT = "default"               # 使用默认值
    MISSING = "missing"               # 缺失，需要询问
    UNCERTAIN = "uncertain"           # 不确定，需要确认


@dataclass
class ParameterInfo:
    """参数信息"""
    name: str
    value: Any = None
    status: ParameterStatus = ParameterStatus.MISSING
    description: str = ""
    unit: str = ""
    is_required: bool = True
    default_value: Any = None
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    alternatives: List[str] = field(default_factory=list)  # 替代参数名


class SmartParameterCollector:
    """
    智能参数收集器
    
    管理参数的整个生命周期：提取→确认→补全→验证
    """
    
    # 参数定义
    PARAMETER_DEFINITIONS = {
        "scenario_name": ParameterInfo(
            name="scenario_name",
            description="场景名称/客户名称",
            is_required=True,
            default_value="未命名场景",
            alternatives=["客户名称", "项目名称", "业务名称"]
        ),
        "daily_order_count": ParameterInfo(
            name="daily_order_count",
            description="日订单数",
            unit="单/天",
            is_required=True,
            validation_rules={"min": 1, "max": 100000},
            alternatives=["订单量", "每天单量", "日单量"]
        ),
        "avg_items_per_order": ParameterInfo(
            name="avg_items_per_order",
            description="平均每单件数",
            unit="件/单",
            is_required=True,
            validation_rules={"min": 1, "max": 1000},
            default_value=1,
            alternatives=["每单件数", "单均件数", "件数"]
        ),
        "avg_weight_kg": ParameterInfo(
            name="avg_weight_kg",
            description="平均每单重量",
            unit="公斤",
            is_required=True,
            validation_rules={"min": 0.1, "max": 10000},
            default_value=1.0,
            alternatives=["重量", "单重", "每单重量"]
        ),
        "delivery_distance_km": ParameterInfo(
            name="delivery_distance_km",
            description="配送距离",
            unit="公里",
            is_required=True,
            validation_rules={"min": 0.1, "max": 1000},
            alternatives=["距离", "配送距离", "公里数"]
        ),
        "need_upstairs": ParameterInfo(
            name="need_upstairs",
            description="是否需要上楼配送",
            is_required=False,
            default_value=False,
            alternatives=["上楼", "爬楼梯", "高层"]
        ),
        "floor": ParameterInfo(
            name="floor",
            description="楼层",
            unit="层",
            is_required=False,
            default_value=1,
            validation_rules={"min": 1, "max": 100},
            alternatives=["楼层", "几楼"]
        ),
        "has_elevator": ParameterInfo(
            name="has_elevator",
            description="是否有电梯",
            is_required=False,
            default_value=True,
            alternatives=["电梯", "有无电梯"]
        ),
        "need_cold_chain": ParameterInfo(
            name="need_cold_chain",
            description="是否需要冷链",
            is_required=False,
            default_value=False,
            alternatives=["冷链", "冷藏", "冷冻"]
        ),
    }
    
    def __init__(self):
        """初始化收集器"""
        self.parameters: Dict[str, ParameterInfo] = {}
        self.extraction_attempts = 0
        self.max_extraction_attempts = 3
        self.collected_from_user = False
    
    def initialize_parameters(self, business_type: str):
        """根据业务类型初始化参数"""
        self.parameters = {}
        for name, definition in self.PARAMETER_DEFINITIONS.items():
            # 根据业务类型调整默认值
            param = ParameterInfo(
                name=definition.name,
                description=definition.description,
                unit=definition.unit,
                is_required=definition.is_required,
                default_value=definition.default_value,
                validation_rules=definition.validation_rules,
                alternatives=definition.alternatives
            )
            
            # 业务类型特定默认值
            if business_type == "meal_delivery":
                if name == "need_cold_chain":
                    param.default_value = True
                if name == "avg_items_per_order":
                    param.default_value = 3
            
            self.parameters[name] = param
    
    def extract_from_text(self, user_input: str, business_type: str) -> Dict[str, Any]:
        """
        从用户输入中提取参数
        
        Args:
            user_input: 用户输入
            business_type: 业务类型
        
        Returns:
            提取结果
        """
        if not self.parameters:
            self.initialize_parameters(business_type)
        
        self.extraction_attempts += 1
        extracted_count = 0
        
        # 使用规则提取参数
        for param_name, param in self.parameters.items():
            if param.status == ParameterStatus.MISSING:
                value = self._extract_parameter(user_input, param_name)
                if value is not None:
                    if self._validate_parameter(param_name, value):
                        param.value = value
                        param.status = ParameterStatus.EXTRACTED
                        extracted_count += 1
        
        # 分析缺失参数
        missing_params = self._get_missing_params()
        uncertain_params = self._get_uncertain_params()
        
        return {
            "extracted_count": extracted_count,
            "missing_params": missing_params,
            "uncertain_params": uncertain_params,
            "can_calculate_partial": self._can_calculate_partial(),
            "parameters": self._get_parameters_summary()
        }
    
    def _extract_parameter(self, user_input: str, param_name: str) -> Any:
        """提取单个参数"""
        user_input_lower = user_input.lower()
        
        # 数值参数提取
        if param_name == "daily_order_count":
            patterns = [
                r'每天[:：]?\s*(\d+)\s*[单订单]*',
                r'日[:：]?\s*(\d+)\s*[单订单]*',
                r'(\d+)\s*[单订单]*\s*/?\s*天',
            ]
            for pattern in patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    return int(match.group(1))
        
        elif param_name == "avg_items_per_order":
            patterns = [
                r'每单[:：]?\s*(\d+)\s*[件个套]*',
                r'单均[:：]?\s*(\d+)\s*[件个套]*',
            ]
            for pattern in patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    return int(match.group(1))
        
        elif param_name == "avg_weight_kg":
            patterns = [
                r'(\d+\.?\d*)\s*公斤',
                r'(\d+\.?\d*)\s*kg',
                r'重量[:：]?\s*(\d+\.?\d*)',
            ]
            for pattern in patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    return float(match.group(1))
        
        elif param_name == "delivery_distance_km":
            patterns = [
                r'(\d+\.?\d*)\s*公里',
                r'距离[:：]?\s*(\d+\.?\d*)',
                r'(\d+\.?\d*)\s*km',
            ]
            for pattern in patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    return float(match.group(1))
        
        elif param_name == "scenario_name":
            # 提取客户名称
            patterns = [
                r'客户[:：]?\s*([\u4e00-\u9fa5\w]+)',
                r'([\u4e00-\u9fa5\w]+)[公司企业]',
            ]
            for pattern in patterns:
                match = re.search(pattern, user_input)
                if match:
                    return match.group(1)
        
        # 布尔参数提取
        elif param_name == "need_upstairs":
            if any(kw in user_input_lower for kw in ["上楼", "爬楼梯", "无电梯"]):
                return True
            elif any(kw in user_input_lower for kw in ["不上楼", "有电梯", "一楼"]):
                return False
        
        elif param_name == "need_cold_chain":
            if any(kw in user_input_lower for kw in ["冷链", "冷藏", "冷冻", "保鲜"]):
                return True
        
        return None
    
    def _validate_parameter(self, param_name: str, value: Any) -> bool:
        """验证参数值"""
        param = self.parameters.get(param_name)
        if not param or not param.validation_rules:
            return True
        
        rules = param.validation_rules
        
        if "min" in rules and value < rules["min"]:
            return False
        if "max" in rules and value > rules["max"]:
            return False
        
        return True
    
    def process_user_response(self, user_response: str) -> Dict[str, Any]:
        """
        处理用户回复，尝试提取缺失的参数
        
        Args:
            user_response: 用户回复
        
        Returns:
            处理结果
        """
        self.collected_from_user = True
        extracted_count = 0
        
        # 尝试从回复中提取所有缺失的参数
        for param_name, param in self.parameters.items():
            if param.status == ParameterStatus.MISSING:
                value = self._extract_parameter(user_response, param_name)
                if value is not None and self._validate_parameter(param_name, value):
                    param.value = value
                    param.status = ParameterStatus.USER_PROVIDED
                    extracted_count += 1
        
        # 检查是否还有缺失的必需参数
        missing_required = [p for p in self.parameters.values() 
                          if p.status == ParameterStatus.MISSING and p.is_required]
        
        # 检查用户是否说明无法提供
        cannot_provide = self._check_cannot_provide(user_response)
        
        # 如果用户无法提供或超过最大尝试次数，应用默认值
        applied_defaults = []
        if (cannot_provide or self.extraction_attempts >= self.max_extraction_attempts) and missing_required:
            defaults_result = self.apply_defaults()
            applied_defaults = defaults_result["applied_defaults"]
            missing_required = []  # 应用默认值后，没有缺失参数了
        
        return {
            "extracted_count": extracted_count,
            "missing_required": [p.name for p in missing_required],
            "applied_defaults": applied_defaults,
            "can_proceed": len(missing_required) == 0 or cannot_provide,
            "cannot_provide": cannot_provide
        }
    
    def _check_cannot_provide(self, user_response: str) -> bool:
        """检查用户是否表示无法提供信息"""
        indicators = [
            "不知道", "不清楚", "没有", "无法", "不能",
            "暂未确定", "还没定", "不确定"
        ]
        return any(ind in user_response for ind in indicators)
    
    def _determine_next_action(self, missing_required: List[ParameterInfo], 
                               cannot_provide: bool) -> str:
        """确定下一步操作"""
        if not missing_required:
            return "proceed"
        elif cannot_provide:
            return "use_defaults"
        elif self.extraction_attempts >= self.max_extraction_attempts:
            return "use_defaults"
        else:
            return "ask_again"
    
    def apply_defaults(self) -> Dict[str, Any]:
        """为缺失参数应用默认值"""
        applied_defaults = []
        
        for param_name, param in self.parameters.items():
            if param.status == ParameterStatus.MISSING:
                if param.default_value is not None:
                    param.value = param.default_value
                    param.status = ParameterStatus.DEFAULT
                    applied_defaults.append({
                        "name": param_name,
                        "value": param.default_value,
                        "description": param.description
                    })
        
        return {
            "applied_defaults": applied_defaults,
            "can_calculate": self._can_calculate_partial()
        }
    
    def generate_collection_prompt(self) -> str:
        """生成参数收集提示"""
        missing = self._get_missing_params()
        
        if not missing:
            return "所有必需参数已收集完成。"
        
        lines = [
            "\n【参数信息收集】",
            "="*60,
            "",
            "为了进行准确的成本评估，还需要以下信息：",
            ""
        ]
        
        for i, param in enumerate(missing, 1):
            line = f"{i}. {param.description}"
            if param.unit:
                line += f" ({param.unit})"
            if param.alternatives:
                line += f"\n   也可以说：{', '.join(param.alternatives)}"
            lines.append(line)
        
        lines.extend([
            "",
            "您可以：",
            "  • 一次性提供所有信息",
            "  • 分批提供",
            "  • 如果某项信息确实无法提供，请说明原因",
            "="*60
        ])
        
        return "\n".join(lines)
    
    def generate_pre_calculation_summary(self) -> str:
        """生成计算前的参数确认摘要"""
        lines = [
            "\n【计算前确认】",
            "="*60,
            "",
            "将使用以下参数进行成本计算：",
            ""
        ]
        
        # 已提取/用户提供的参数
        confirmed = [p for p in self.parameters.values() 
                    if p.status in [ParameterStatus.EXTRACTED, ParameterStatus.USER_PROVIDED]]
        if confirmed:
            lines.append("✅ 已确认的参数：")
            for param in confirmed:
                value_str = f"{param.value} {param.unit}" if param.unit else str(param.value)
                lines.append(f"   • {param.description}: {value_str}")
            lines.append("")
        
        # 使用默认值的参数
        defaults = [p for p in self.parameters.values() if p.status == ParameterStatus.DEFAULT]
        if defaults:
            lines.append("⚠️ 使用默认值的参数：")
            for param in defaults:
                value_str = f"{param.value} {param.unit}" if param.unit else str(param.value)
                lines.append(f"   • {param.description}: {value_str} (默认值)")
            lines.append("")
        
        # 仍然缺失的参数
        missing = [p for p in self.parameters.values() if p.status == ParameterStatus.MISSING]
        if missing:
            lines.append("❌ 缺失的参数（将无法计算相关环节）：")
            for param in missing:
                lines.append(f"   • {param.description}")
            lines.append("")
        
        lines.extend([
            "请确认以上信息是否正确，或提供修改：",
            "  • 回复'确认'开始计算",
            "  • 回复'修改XX=值'修改特定参数",
            "  • 回复'补充XX=值'添加缺失参数",
            "="*60
        ])
        
        return "\n".join(lines)
    
    def _get_missing_params(self) -> List[ParameterInfo]:
        """获取缺失的参数"""
        return [p for p in self.parameters.values() 
                if p.status == ParameterStatus.MISSING and p.is_required]
    
    def _get_uncertain_params(self) -> List[ParameterInfo]:
        """获取不确定的参数"""
        return [p for p in self.parameters.values() if p.status == ParameterStatus.UNCERTAIN]
    
    def _can_calculate_partial(self) -> bool:
        """检查是否可以进行部分计算"""
        # 只要有日订单数和距离，就可以进行基础计算
        daily_orders = self.parameters.get("daily_order_count")
        distance = self.parameters.get("delivery_distance_km")
        
        has_daily = daily_orders and daily_orders.status != ParameterStatus.MISSING
        has_distance = distance and distance.status != ParameterStatus.MISSING
        
        return has_daily and has_distance
    
    def _get_parameters_summary(self) -> Dict[str, Any]:
        """获取参数摘要"""
        return {
            name: {
                "value": param.value,
                "status": param.status.value,
                "description": param.description
            }
            for name, param in self.parameters.items()
        }
    
    def get_final_parameters(self) -> Dict[str, Any]:
        """获取最终参数值字典"""
        return {
            name: param.value for name, param in self.parameters.items()
            if param.value is not None
        }
    
    def update_parameter(self, name: str, value: Any, source: str = "user") -> bool:
        """更新参数值"""
        if name not in self.parameters:
            return False
        
        param = self.parameters[name]
        if self._validate_parameter(name, value):
            param.value = value
            param.status = ParameterStatus.USER_PROVIDED if source == "user" else ParameterStatus.EXTRACTED
            return True
        return False


if __name__ == "__main__":
    # 测试
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    print("="*60)
    print("智能参数收集器测试")
    print("="*60)
    
    collector = SmartParameterCollector()
    
    # 测试1: 完整输入
    print("\n【测试1】完整输入")
    test_input = "我们想接ABC公司，每天100单办公用品，每单5件，重量10公斤，送到20公里外"
    result = collector.extract_from_text(test_input, "tob_enterprise")
    print(f"输入: {test_input}")
    print(f"提取数量: {result['extracted_count']}")
    print(f"缺失参数: {[p.name for p in result['missing_params']]}")
    
    # 测试2: 不完整输入
    print("\n【测试2】不完整输入")
    collector2 = SmartParameterCollector()
    test_input2 = "每天50单，送到15公里外"
    result2 = collector2.extract_from_text(test_input2, "tob_enterprise")
    print(f"输入: {test_input2}")
    print(f"提取数量: {result2['extracted_count']}")
    print(f"缺失参数: {[p.name for p in result2['missing_params']]}")
    print(f"\n收集提示:")
    print(collector2.generate_collection_prompt())
    
    # 测试3: 用户补全
    print("\n【测试3】用户补全")
    user_reply = "每单3件，重量8公斤"
    result3 = collector2.process_user_response(user_reply)
    print(f"用户回复: {user_reply}")
    print(f"提取数量: {result3['extracted_count']}")
    print(f"仍然缺失: {result3['missing_required']}")
    
    # 测试4: 应用默认值
    print("\n【测试4】应用默认值")
    defaults_result = collector2.apply_defaults()
    print(f"应用默认值: {defaults_result['applied_defaults']}")
    
    # 测试5: 计算前确认
    print("\n【测试5】计算前确认")
    print(collector2.generate_pre_calculation_summary())
