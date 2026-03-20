"""
LLM原生对话引擎 V2

真正以LLM为核心的对话系统架构：
- LLM理解用户意图和需求
- LLM编排和调度任务
- LLM提取和处理数据
- 支持文件上传和多模态交互
- 生成个性化建议
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class TaskType(str, Enum):
    """任务类型枚举"""
    COST_ASSESSMENT = "cost_assessment"           # 成本评估
    PROFIT_ANALYSIS = "profit_analysis"          # 利润分析
    KNOWLEDGE_QUERY = "knowledge_query"           # 知识查询
    DATA_IMPORT = "data_import"                   # 数据导入
    COMPARISON = "comparison"                    # 对比分析
    OPTIMIZATION = "optimization"                # 优化建议
    GENERAL_CHAT = "general_chat"               # 通用对话
    CLARIFICATION = "clarification"              # 需求澄清
    UNKNOWN = "unknown"                         # 未知


class DataSource(str, Enum):
    """数据来源"""
    USER_TEXT = "user_text"      # 用户文本输入
    USER_FILE = "user_file"     # 用户上传文件
    SYSTEM_CONTEXT = "system"    # 系统上下文
    KNOWLEDGE_BASE = "knowledge" # 知识库


# 个性化建议生成提示词
PERSONALIZED_ADVICE_PROMPT = """你是一个专业的物流成本顾问。基于以下成本分析结果，生成个性化的优化建议。

成本数据：
{-cost_data}

订单特征：
{order_features}

请生成3-5条具体、可操作的优化建议。每条建议应包括：
1. 具体问题
2. 量化分析（能节省多少成本或提高多少效率）
3. 实施难度（容易/中等/困难）
4. 预期效果

要求：
- 建议要具体，不要泛泛而谈
- 结合订单的具体特征（距离、重量、上楼需求等）
- 考虑业务实际情况，不是理论最优
- 语言简洁，专业但易懂

输出格式：
```json
{{
    "suggestions": [
        {{
            "issue": "具体问题描述",
            "action": "建议采取的行动",
            "savings": "预估节省金额或提高效率",
            "difficulty": "容易/中等/困难",
            "priority": "高/中/低"
        }}
    ]
}}
```"""


class ConversationContext:
    """对话上下文"""
    
    def __init__(self):
        """初始化上下文"""
        self.current_task: TaskType = TaskType.UNKNOWN
        self.collected_data: Dict[str, Any] = {}
        self.missing_fields: List[str] = []
        self.conversation_turns: int = 0
        self.last_intent: str = ""
        self.last_response: str = ""
        self.order_type: str = "single"  # single/daily/uncertain
        self.business_context: str = ""  # 业务背景描述
        
        # 记忆的偏好设置
        self.user_preferences: Dict[str, Any] = {}


class LLMMissionEngineV2:
    """
    LLM任务引擎 V2
    
    核心职责：
    1. 理解用户意图
    2. 编排任务流程
    3. 提取和验证数据
    4. 管理对话上下文
    5. 生成个性化建议
    """
    
    SYSTEM_PROMPT = """你是一个专业的物流业务助手，负责帮助用户评估物流成本和分析订单可行性。

**你的能力：**
1. 理解用户的业务描述，提取关键信息
2. 识别是临时订单还是循环订单
3. 基于单均计算逻辑评估物流成本（系统有默认费率配置）
4. 分析订单可行性（结合采购价、售价计算毛利）

**重要原则：**
- 以"单"为基本计算单元，支持临时性、一次性订单
- 不要假设用户每天都有订单，订单可能是临时的
- 数据提取要灵活，不强求用户按固定格式输入
- 遇到模糊信息时，可以使用合理的默认值
- 不要询问用户关于费率、成本单价等系统参数！这些由系统自动处理
- 用户只需要提供：货物数量、重量、距离、是否上楼、是否冷链、采购价、售价

**提取字段规范：**
- items_per_order 或 quantity: 每单件数/数量
- weight_per_item_kg: 单件重量(kg)
- distance_km: 配送距离(km)
- floor: 楼层（需要上楼时）
- need_upstairs: 是否需要上楼
- has_elevator: 是否有电梯
- need_cold_chain: 是否需要冷链
- purchase_price: 采购单价
- selling_price: 销售单价
- order_type: single/daily/weekly/monthly/uncertain

**输出格式：**
始终返回JSON格式，包含：
- intent: 识别到的意图（cost_assessment/profit_analysis/general_chat）
- extracted_data: 从用户输入提取的数据（使用上述字段名）
- missing_fields: 还需要的数据（如果有，且是用户应该知道的）
- next_action: 下一步（ask/calculate/explain/advise）
- response_message: 回复用户的自然语言文本
- personalized_advice: 个性化建议（如有）

**注意：**
当用户提供了足够计算的数据（数量、重量、距离）时，应立即计算，不要询问费率！
"""

    def __init__(self, llm_client=None):
        """初始化LLM任务引擎"""
        self.llm_client = llm_client
        self.context = ConversationContext()

    def process(self, user_input: str, file_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理用户输入（核心方法）

        真正LLM-native架构：
        1. 所有输入都由LLM理解
        2. 即使没有LLM，也不使用关键词fallback
        3. 上下文驱动，记忆用户意图和进度
        """
        self.context.conversation_turns += 1

        context_info = self._build_context_info()
        user_message = self._build_user_message(user_input, file_data)

        response = self._call_llm(context_info, user_message)
        parsed = self._parse_llm_response(response)

        self._update_context(parsed, user_input)

        if parsed.get("next_action") == "explain" and parsed.get("cost_result"):
            parsed["personalized_advice"] = self._generate_advice(
                parsed.get("cost_result", {}),
                self.context.collected_data
            )

        final_response = self._build_response(parsed)

        return final_response

    def _build_context_info(self) -> str:
        """构建上下文信息"""
        ctx = self.context

        parts = []

        parts.append(f"对话轮次: {ctx.conversation_turns}")

        if ctx.collected_data:
            data_summary = []
            for key, value in ctx.collected_data.items():
                if value is not None:
                    data_summary.append(f"{key}={value}")
            if data_summary:
                parts.append(f"已收集数据: {', '.join(data_summary)}")

        if ctx.missing_fields:
            parts.append(f"待确认数据: {', '.join(ctx.missing_fields)}")

        if ctx.order_type != "uncertain":
            parts.append(f"订单类型: {ctx.order_type}")

        if ctx.last_intent:
            parts.append(f"上轮意图: {ctx.last_intent}")

        return "\n".join(parts) if parts else "（首次对话）"

    def _build_user_message(self, user_input: str, file_data: Dict = None) -> str:
        """构建用户消息"""
        parts = ["用户输入：\n" + user_input]

        if file_data:
            parts.append(f"\n上传文件: {file_data.get('filename', 'unknown')}")
            if file_data.get('preview'):
                parts.append(f"文件预览: {file_data.get('preview', '')[:500]}")

        return "\n".join(parts)

    def _call_llm(self, context_info: str, user_message: str) -> str:
        """调用LLM"""
        if self.llm_client is None:
            return self._graceful_degradation_response(context_info, user_message)

        try:
            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"上下文：\n{context_info}\n\n{user_message}"}
            ]
            response = self.llm_client.chat_completion(
                messages=messages,
                temperature=0.3
            )
            if isinstance(response, dict):
                content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                return content
            return str(response)
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                user_message = "抱歉，AI服务响应超时。这可能是因为网络原因或服务器繁忙。请稍后重试，或换一种方式描述您的需求。"
            elif "429" in error_msg:
                user_message = "抱歉，AI服务请求过于频繁。请稍后重试。"
            elif "invalid" in error_msg.lower() or "401" in error_msg:
                user_message = "抱歉，API密钥无效或已过期。请检查配置。"
            else:
                user_message = f"抱歉遇到了问题：{error_msg}，请换一种方式描述您的需求。"

            return json.dumps({
                "intent": "error",
                "response_message": user_message,
                "next_action": "retry"
            })

    def _graceful_degradation_response(self, context_info: str, user_input: str) -> str:
        """
        无LLM时的优雅降级响应

        不使用关键词匹配，而是：
        1. 分析当前上下文状态
        2. 根据已有数据决定下一步
        3. 引导用户提供必要信息
        """
        ctx = self.context

        has_items = ctx.collected_data.get("items_per_order")
        has_distance = ctx.collected_data.get("distance_km")
        has_price = ctx.collected_data.get("purchase_price") and ctx.collected_data.get("selling_price")

        if ctx.conversation_turns == 1:
            return json.dumps({
                "intent": "greeting",
                "response_message": "您好！我是物流业务智能助手。请描述您的业务场景，比如要运送什么货物，多少重量，送到哪里等。",
                "next_action": "listen",
                "extracted_data": {},
                "missing_fields": []
            })

        if has_items and has_distance and has_price:
            return json.dumps({
                "intent": "ready_to_calculate",
                "response_message": "已收集足够数据，准备计算...",
                "next_action": "calculate",
                "extracted_data": ctx.collected_data,
                "missing_fields": []
            })

        if has_items and has_distance:
            return json.dumps({
                "intent": "cost_assessment",
                "response_message": f"已了解您的配送需求：{has_items}件货物，{has_distance}公里。如果需要利润分析，请告诉我采购价和售价。",
                "next_action": "listen",
                "extracted_data": ctx.collected_data,
                "missing_fields": []
            })

        if ctx.last_response and ctx.last_intent:
            return json.dumps({
                "intent": ctx.last_intent,
                "response_message": "请继续描述您的需求，比如货物的数量、重量、距离等信息。",
                "next_action": "ask",
                "extracted_data": ctx.collected_data,
                "missing_fields": ["items_per_order", "distance_km"]
            })

        return json.dumps({
            "intent": "general",
            "response_message": "请告诉我您的配送需求，比如要运送什么，多少件，多重，送到哪里等。",
            "next_action": "listen",
            "extracted_data": {},
            "missing_fields": []
        })

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            json_str = self._extract_json(response)
            return json.loads(json_str)
        except:
            return {
                "intent": "error",
                "response_message": "抱歉无法理解，请换一种方式描述您的需求。",
                "next_action": "retry"
            }

    def _extract_json(self, text: str) -> str:
        """提取JSON"""
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return text[start:end+1]
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                return text[start:end]
        return text
    
    def _update_context(self, parsed: Dict[str, Any], user_input: str):
        """更新上下文"""
        ctx = self.context

        intent = parsed.get("intent", "unknown")
        if intent != "unknown":
            ctx.last_intent = ctx.current_task
            ctx.current_task = TaskType(intent) if intent in [e.value for e in TaskType] else TaskType.UNKNOWN

        extracted = parsed.get("extracted_data", {})
        if extracted:
            mapped_data = self._map_fields(extracted)

            critical_fields = ["items_per_order", "distance_km", "weight_per_item_kg"]
            has_new_critical = any(k in mapped_data for k in critical_fields)
            if has_new_critical:
                ctx.collected_data = {}

            for key, value in mapped_data.items():
                if value is not None:
                    ctx.collected_data[key] = value

        ctx.missing_fields = parsed.get("missing_fields", [])

        order_type = extracted.get("order_type", "")
        if order_type:
            if order_type in ["single", "一次性", "临时"]:
                ctx.order_type = "single"
            elif order_type in ["recurring", "daily", "每天", "日均"]:
                ctx.order_type = "daily"
            else:
                ctx.order_type = order_type

        if "business_type" in extracted:
            ctx.business_context = extracted.get("business_type", "")

        ctx.last_response = parsed.get("response_message", "")

    def _map_fields(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """映射LLM提取的字段名到计算器期望的字段名"""
        field_mapping = {
            "quantity": "items_per_order",
            "daily_quantity": "items_per_order",
            "weight_per_unit_kg": "weight_per_item_kg",
            "floor_without_elevator": "floor",
        }

        result = {}
        for key, value in extracted.items():
            if key in field_mapping:
                result[field_mapping[key]] = value
                if key == "floor_without_elevator":
                    result["has_elevator"] = False
                    result["need_upstairs"] = True
            else:
                result[key] = value

        if "special_requirements" in extracted:
            special = str(extracted["special_requirements"]).lower()
            if "冷链" in special or "冷藏" in special or "冷冻" in special:
                result["need_cold_chain"] = True

        return result
    
    def _generate_advice(self, cost_data: Dict, order_features: Dict) -> List[Dict]:
        """生成个性化建议"""
        if self.llm_client is None:
            return []

        try:
            prompt = PERSONALIZED_ADVICE_PROMPT.format(
                cost_data=json.dumps(cost_data, ensure_ascii=False),
                order_features=json.dumps(order_features, ensure_ascii=False)
            )

            messages = [
                {"role": "system", "content": "你是一个专业的物流成本优化顾问。"},
                {"role": "user", "content": prompt}
            ]
            response = self.llm_client.chat_completion(
                messages=messages,
                temperature=0.5
            )

            if isinstance(response, dict):
                content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                result = json.loads(self._extract_json(content))
            else:
                result = json.loads(self._extract_json(str(response)))
            return result.get("suggestions", [])
        except:
            return []
    
    def _build_response(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """构建最终响应"""
        return {
            "success": parsed.get("intent") != "error",
            "intent": parsed.get("intent", "unknown"),
            "message": parsed.get("response_message", ""),
            "next_action": parsed.get("next_action", "listen"),
            "extracted_data": parsed.get("extracted_data", {}),
            "missing_fields": parsed.get("missing_fields", []),
            "personalized_advice": parsed.get("personalized_advice", []),
            "context": {
                "conversation_turns": self.context.conversation_turns,
                "collected_data": self.context.collected_data,
                "order_type": self.context.order_type,
            }
        }
    
    def get_context_summary(self) -> str:
        """获取上下文摘要"""
        ctx = self.context
        return f"""对话轮次: {ctx.conversation_turns}
当前任务: {ctx.current_task.value}
订单类型: {ctx.order_type}
已收集数据: {ctx.collected_data}
缺失数据: {ctx.missing_fields}"""
    
    def reset(self):
        """重置上下文"""
        self.context = ConversationContext()


# 别名，保持向后兼容
LLMMissionEngine = LLMMissionEngineV2


if __name__ == "__main__":
    print("="*60)
    print("LLM原生对话引擎 V2 测试")
    print("="*60)
    
    engine = LLMMissionEngineV2()
    
    # 测试1: 临时订单
    print("\n【测试1】临时订单评估")
    result = engine.process("我有100箱苹果要送，每箱10公斤，送到20公里外，采购价50，卖80，能做吗？")
    print(f"意图: {result['intent']}")
    print(f"回复: {result['message']}")
    print(f"提取数据: {result['extracted_data']}")
    print(f"缺失: {result['missing_fields']}")
    
    # 测试2: 循环订单
    print("\n【测试2】每日循环订单")
    result2 = engine.process("我们每天要给超市送200箱货，每箱5公斤，距离15公里")
    print(f"意图: {result2['intent']}")
    print(f"回复: {result2['message']}")
    
    # 测试3: 模糊需求
    print("\n【测试3】模糊需求")
    result3 = engine.process("我有个配送的活儿，帮我算算成本")
    print(f"意图: {result3['intent']}")
    print(f"回复: {result3['message']}")
